# -*- coding: utf-8 -*-
"""
锁的是业务不变量，不是快照。
数字会随价表变，但下面这些关系不能变——变了就是引擎出错。
"""
import json
import unittest
from pathlib import Path

from bomcheck import Book, calculate, compare
from bomcheck.pricebook import REPO_BOOK

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"


def load(name):
    with open(DATA / name, "r", encoding="utf-8") as f:
        return json.load(f)


def q(name="bom-terminal-std.json", quote=None, book=None):
    return calculate(load(name), book or Book(path=REPO_BOOK), quote=quote)


class Test物料(unittest.TestCase):
    def test_物料费等于逐行含损耗之和(self):
        r = q()
        s = sum(ln["含损耗"] for ln in r["行明细"])
        self.assertAlmostEqual(r["物料费"], s, delta=0.05)

    def test_每行含损耗等于金额乘以一加损耗率(self):
        r = q()
        for ln in r["行明细"]:
            self.assertAlmostEqual(ln["含损耗"], ln["金额"] * (1 + ln["损耗率"]), delta=0.02)

    def test_结构件损耗高于芯片(self):
        """结构件 5%，芯片 2%——这是常识，不能被改反"""
        book = Book(path=REPO_BOOK)
        self.assertGreater(book.loss("结构"), book.loss("芯片"))

    def test_同一价格不同类别含损耗不同(self):
        b = {"名称": "t", "批量": 1000,
             "行": [{"件名": "a", "规格": "PCB4层100x80", "数量": 1}]}
        book = Book(path=REPO_BOOK)
        cheap = calculate(b, book)["物料费"]
        # PCB 是辅料（5%），比默认 3% 高
        self.assertAlmostEqual(cheap, 9.8 * 1.05, delta=0.01)


class Test加工与摊销(unittest.TestCase):
    def test_加工费等于三项之和(self):
        r = q()
        book = Book(path=REPO_BOOK)
        bom = load("bom-terminal-std.json")
        p = bom["加工"]
        want = (p["贴片点数"] * book.proc("贴片元每点")
                + p["手焊点数"] * book.proc("手焊元每点")
                + p["组装分钟"] * book.proc("组装元每分钟"))
        self.assertAlmostEqual(r["加工费"], want, delta=0.02)

    def test_认证摊销随批量下降(self):
        book = Book(path=REPO_BOOK)
        b = load("bom-terminal-std.json")
        small = calculate({**b, "批量": 500}, book)["成本明细"]["认证摊销"]
        big = calculate({**b, "批量": 5000}, book)["成本明细"]["认证摊销"]
        self.assertAlmostEqual(small / big, 10.0, delta=0.01)

    def test_认证摊销等于总额除以批量(self):
        r = q()
        book = Book(path=REPO_BOOK)
        total = float(book.biz("认证一次性总额"))
        self.assertAlmostEqual(r["成本明细"]["认证摊销"], total / r["批量"], delta=0.01)

    def test_不良返修只按物料加加工计提(self):
        r = q()
        want = (r["物料费"] + r["加工费"]) * 0.025
        self.assertAlmostEqual(r["成本明细"]["不良返修"], want, delta=0.02)

    def test_出厂成本等于成本明细之和(self):
        r = q()
        self.assertAlmostEqual(r["出厂成本"], sum(r["成本明细"].values()), delta=0.05)

    def test_九项明细一项不少(self):
        r = q()
        self.assertEqual(len(r["成本明细"]), 8)   # 加工费已合并贴片/手焊/组装
        self.assertEqual(sum(1 for s in r["算式"] if s["金额"] > 0), 10)


class Test报价(unittest.TestCase):
    def test_不传报价时按档位倍数算(self):
        r = q()
        book = Book(path=REPO_BOOK)
        self.assertAlmostEqual(r["报价"], r["出厂成本"] * book.tier_multiple("标准"), delta=1.0)

    def test_毛利率是毛利除报价不是除成本(self):
        """乘 2.6 的毛利率是 61.5%，不是 160%——这条最容易算反"""
        r = q()
        self.assertAlmostEqual(r["毛利率"], (r["报价"] - r["出厂成本"]) / r["报价"], delta=1e-4)
        self.assertLess(r["毛利率"], 1.0)

    def test_项目制倍数高于标准(self):
        book = Book(path=REPO_BOOK)
        self.assertGreater(book.tier_multiple("项目制"), book.tier_multiple("标准"))


class Test红旗(unittest.TestCase):
    def test_报四千打红(self):
        r = q(quote=4000)
        lv = [f["级别"] for f in r["红旗"]]
        self.assertIn("红", lv)

    def test_按出厂成本报价不报红(self):
        r = q()
        r2 = q(quote=r["出厂成本"] * 1.1)
        self.assertNotIn("红", [f["级别"] for f in r2["红旗"]])

    def test_报价低于成本是蓝不是红(self):
        r = q(quote=100)
        self.assertIn("蓝", [f["级别"] for f in r["红旗"]])
        self.assertNotIn("红", [f["级别"] for f in r["红旗"]])

    def test_倍数口径对得上(self):
        r = q(quote=4000)
        self.assertAlmostEqual(r["报价除出厂"], 4000 / r["出厂成本"], delta=0.01)


class Test安全告警(unittest.TestCase):
    def test_含气阀的档位会告警(self):
        self.assertTrue(any("气阀" in w for w in q()["告警"]))

    def test_冗余档不装气阀也不告警(self):
        r = q("bom-terminal-rugged.json")
        self.assertEqual(r["告警"], [])

    def test_气阀那行确实占了钱(self):
        std = q()
        r = q("bom-terminal-rugged.json")
        air = next(ln for ln in std["行明细"] if ln["件名"] == "气阀")
        self.assertAlmostEqual(air["含损耗"], 80.34, delta=0.05)
        self.assertTrue(all(ln["件名"] != "气阀" for ln in r["行明细"]))


class Test三档(unittest.TestCase):
    def test_三档成本递增(self):
        book = Book(path=REPO_BOOK)
        c = compare([calculate(load(n), book) for n in
                     ("bom-terminal-lite.json", "bom-terminal-std.json", "bom-terminal-rugged.json")])
        costs = [row["出厂成本"] for row in c["档位对比"]]
        self.assertEqual(costs, sorted(costs))

    def test_精简档出厂成本不到标准档一半(self):
        book = Book(path=REPO_BOOK)
        lite = calculate(load("bom-terminal-lite.json"), book)
        std = calculate(load("bom-terminal-std.json"), book)
        self.assertLess(lite["出厂成本"], std["出厂成本"] * 0.5)

    def test_标准档出厂成本远低于市售整机的四分之一(self):
        std = q()
        self.assertLess(std["出厂成本"], 4000 / 4)


class Test容错(unittest.TestCase):
    def test_价表缺件会报错而不是瞎猜(self):
        bad = {"名称": "x", "批量": 1000,
               "行": [{"件名": "神秘件", "规格": "不存在的规格", "数量": 1}]}
        with self.assertRaises(ValueError) as ctx:
            calculate(bad, Book(path=REPO_BOOK))
        self.assertIn("查不到", str(ctx.exception))

    def test_行内写单价可以覆盖价表(self):
        b = {"名称": "x", "批量": 1000,
             "行": [{"件名": "a", "规格": "A7670C", "数量": 1, "单价": 100.0}]}
        r = calculate(b, Book(path=REPO_BOOK))
        self.assertAlmostEqual(r["行明细"][0]["单价"], 100.0)

    def test_手填单价会拉低置信度(self):
        b = {"名称": "x", "批量": 1000,
             "行": [{"件名": "a", "规格": "A7670C", "数量": 1, "单价": 100.0}]}
        r = calculate(b, Book(path=REPO_BOOK))
        self.assertEqual(r["confidence_level"], "低")

    def test_空BOM直接报错(self):
        with self.assertRaises(ValueError):
            calculate({"名称": "x", "行": []}, Book(path=REPO_BOOK))


class Test价表本身(unittest.TestCase):
    def test_价表能加载且价格为正(self):
        book = Book(path=REPO_BOOK)
        items = book.data["价格"]
        self.assertGreater(len(items), 20)
        for spec, it in items.items():
            self.assertGreater(float(it["价"]), 0, spec)

    def test_每个件都有类别且类别在损耗表里(self):
        book = Book(path=REPO_BOOK)
        table = book.data["损耗率"]
        for spec, it in book.data["价格"].items():
            self.assertIn("类别", it, spec)
            self.assertIn(it["类别"], table, f"{spec} 的类别 {it['类别']} 不在损耗率表里")


if __name__ == "__main__":
    unittest.main(verbosity=2)
