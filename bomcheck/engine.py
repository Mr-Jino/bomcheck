# -*- coding: utf-8 -*-
"""
engine —— 硬件核价引擎
======================
一份 BOM 进去，九项成本出来，每项都带算式。

九项：物料 / 加工（贴片 + 手焊 + 组装）/ 测试 / 认证摊销 / 包装 / 物流 /
      不良返修 / 研发管理摊销 —— 前七项加总就是出厂成本。

三个刻意的设计：

1. 不猜价格。BOM 行里没写单价、价表里也查不到，直接报错，不给你一个"大概"。
2. 认证费按批量摊销。1000 台和 100 台，同一张 3C 证书摊出来的数不一样，
   很多人算 BOM 时漏掉这一项，小批量报价就亏在这里。
3. 报价倍数分档。精简 / 标准 / 项目制三个口径，价表里可改。
   倍数不是利润——乘以 2.6 的毛利率是 61.5%，不是 160%。
"""
from .pricebook import Book

# 出现这些词，说明这个方案动了车上的物理执行机构，必须提示
SAFETY_WORDS = ("气阀", "刹车", "气路", "电磁阀")


def _r(x, n=2):
    return round(float(x) + 1e-9, n)


def calculate(bom: dict, book: Book = None, quote: float = None) -> dict:
    """bom: 见 docs/核价模型.md 的字段说明；quote: 外部报价，用来做红旗比对。"""
    bk = book or Book()
    rows = bom.get("行") or []
    if not rows:
        raise ValueError("BOM 里没有「行」——至少放一个件进去。")

    batch = float(bom.get("批量") or 1000)
    tier = bom.get("档位") or "标准"

    # ---------------------------------------------------------------- 物料
    detail, steps, lines = {}, [], []
    missing, hand_filled, cat_fallback = [], 0, 0
    mat = 0.0

    for row in rows:
        spec = row.get("规格") or ""
        name = row.get("件名") or spec
        qty = float(row.get("数量", 1))
        unit = row.get("单价")
        if unit is None:
            unit = bk.price(spec)
        else:
            unit = float(unit)
            hand_filled += 1
        if unit is None:
            missing.append(f"{name}（规格 {spec}）")
            continue

        cat = bk.category(spec, row.get("类别"))
        if cat is None:
            cat, cat_fallback = "辅料", cat_fallback + 1
        loss = bk.loss(cat)
        amount = qty * unit
        with_loss = amount * (1 + loss)
        mat += with_loss

        detail[name] = _r(with_loss)
        lines.append({
            "件名": name, "规格": spec, "数量": qty, "单价": _r(unit),
            "类别": cat, "损耗率": loss,
            "金额": _r(amount), "含损耗": _r(with_loss),
            "备注": row.get("备注", ""),
        })

    if missing:
        raise ValueError(
            "这些件在价表里查不到，BOM 行里也没写单价：\n  - "
            + "\n  - ".join(missing)
            + "\n去价表里加上，或者在该行写 \"单价\": 12.5。"
        )

    # ---------------------------------------------------------------- 加工
    p = bom.get("加工") or {}
    smd_pts = float(p.get("贴片点数", 800))
    hand_pts = float(p.get("手焊点数", 50))
    asm_min = float(p.get("组装分钟", 20))
    test_min = float(p.get("测试分钟", 12))

    smd = smd_pts * bk.proc("贴片元每点", 0.0095)
    hand = hand_pts * bk.proc("手焊元每点", 0.18)
    asm = asm_min * bk.proc("组装元每分钟", 1.15)
    proc = smd + hand + asm

    # ---------------------------------------------------------------- 其它
    test = test_min * bk.proc("测试元每分钟", 1.05)
    cert_total = float(bk.biz("认证一次性总额", 35000.0))
    cert = cert_total / batch
    pack = float(bk.biz("包装元每台", 6.0))
    ship = float(bk.biz("物流元每台", 8.0))
    defect_rate = float(bk.biz("不良率", 0.025))
    defect = (mat + proc) * defect_rate

    base = mat + proc + test + cert + pack + ship + defect
    overhead_rate = float(bk.biz("研发管理摊销率", 0.08))
    overhead = base * overhead_rate

    factory = base + overhead

    # ---------------------------------------------------------------- 明细
    成本明细 = {
        "物料费": _r(mat),
        "加工费": _r(proc),
        "测试费": _r(test),
        "认证摊销": _r(cert),
        "包装费": _r(pack),
        "物流费": _r(ship),
        "不良返修": _r(defect),
        "研发管理摊销": _r(overhead),
    }

    steps = [
        {"名称": "物料费",
         "算式": f"{len(lines)} 个件，含采购损耗 {len(lines)} 项逐行加总（见「行明细」）",
         "金额": _r(mat)},
        {"名称": "加工费-贴片",
         "算式": f"{smd_pts:.0f} 点 × {bk.proc('贴片元每点', 0.0095)} 元/点",
         "金额": _r(smd)},
        {"名称": "加工费-手焊",
         "算式": f"{hand_pts:.0f} 点 × {bk.proc('手焊元每点', 0.18)} 元/点",
         "金额": _r(hand)},
        {"名称": "加工费-组装",
         "算式": f"{asm_min:.0f} 分钟 × {bk.proc('组装元每分钟', 1.15)} 元/分钟",
         "金额": _r(asm)},
        {"名称": "测试费",
         "算式": f"{test_min:.0f} 分钟 × {bk.proc('测试元每分钟', 1.05)} 元/分钟",
         "金额": _r(test)},
        {"名称": "认证摊销",
         "算式": f"一次性 {cert_total:,.0f} 元 ÷ {batch:,.0f} 台",
         "金额": _r(cert)},
        {"名称": "包装费", "算式": "按台固定", "金额": _r(pack)},
        {"名称": "物流费", "算式": "按台固定（到仓）", "金额": _r(ship)},
        {"名称": "不良返修",
         "算式": f"(物料 {mat:,.2f} + 加工 {proc:,.2f}) × 不良率 {defect_rate*100:.1f}%",
         "金额": _r(defect)},
        {"名称": "研发管理摊销",
         "算式": f"前七项 {base:,.2f} × {overhead_rate*100:.0f}%",
         "金额": _r(overhead)},
    ]

    # ---------------------------------------------------------------- 报价
    multiple = bk.tier_multiple(tier)
    ask = float(quote) if quote else factory * multiple
    gross = ask - factory
    gross_rate = gross / ask if ask else 0.0

    # ---------------------------------------------------------------- 红旗
    flags = []
    r_cost = ask / factory if factory else 0
    r_mat = ask / mat if mat else 0
    red_cost = bk.redline("报价除出厂_红") or 3.0
    yel_cost = bk.redline("报价除出厂_黄") or 2.2
    red_mat = bk.redline("报价除物料_红") or 4.0

    if r_cost >= red_cost:
        flags.append({"级别": "红",
                      "说明": f"报价是出厂成本的 {r_cost:.1f} 倍（阈值 {red_cost:.1f}）"})
    elif r_cost >= yel_cost:
        flags.append({"级别": "黄",
                      "说明": f"报价是出厂成本的 {r_cost:.1f} 倍（阈值 {yel_cost:.1f}）"})
    if r_mat >= red_mat:
        flags.append({"级别": "红",
                      "说明": f"报价是物料成本的 {r_mat:.1f} 倍（阈值 {red_mat:.1f}）"})
    if r_cost < 1.6:
        flags.append({"级别": "蓝",
                      "说明": f"报价只有出厂成本的 {r_cost:.1f} 倍，可能不含服务/安装，或者算漏了项"})

    for ln in lines:
        std = bk.price(ln["规格"])
        if std and ln["单价"] > std * 1.5:
            flags.append({"级别": "灰",
                          "说明": f"{ln['件名']} 单价 {ln['单价']:.2f} 高于价表 {std:.2f} 的 1.5 倍，先查渠道"})

    # ---------------------------------------------------------------- 告警
    warnings = []
    hit = [ln["件名"] for ln in lines if any(w in ln["件名"] for w in SAFETY_WORDS)]
    if hit:
        warnings.append("本 BOM 含物理执行件：" + "、".join(hit)
                        + "。动原车气路/刹车属于非冗余改装，安全责任不在本工具评估范围内。")
    if batch < 300:
        warnings.append(f"批量 {batch:.0f} 台偏小，认证摊销 {cert:.2f} 元/台 已经在咬成本了。")

    # ---------------------------------------------------------------- 置信度
    total_rows = len(lines)
    if hand_filled == 0 and cat_fallback == 0:
        confidence = "高"
    elif hand_filled <= total_rows / 2:
        confidence = "中"
    else:
        confidence = "低"

    return {
        "名称": bom.get("名称", ""),
        "档位": tier,
        "批量": batch,
        "物料费": _r(mat),
        "加工费": _r(proc),
        "出厂成本": _r(factory),
        "成本明细": 成本明细,
        "行明细": lines,
        "算式": steps,
        "报价": _r(ask),
        "报价来源": "外部报价" if quote else f"出厂成本 × {multiple}（{tier}档）",
        "毛利": _r(gross),
        "毛利率": round(gross_rate, 4),
        "报价除出厂": round(r_cost, 2),
        "报价除物料": round(r_mat, 2),
        "红旗": flags,
        "告警": warnings,
        "confidence_level": confidence,
        "提示": "价表按 1000 台批量填的参考价，实际以自己渠道询价为准。",
    }


def compare(results) -> dict:
    """三档并排：同口径比物料、比出厂、比报价。"""
    rows = []
    base_cost = results[0]["出厂成本"] if results else 0
    for r in results:
        rows.append({
            "档位": r["档位"],
            "物料费": r["物料费"],
            "出厂成本": r["出厂成本"],
            "报价": r["报价"],
            "较最低档": _r(r["出厂成本"] - base_cost),
            "价差占比": round((r["出厂成本"] - base_cost) / base_cost * 100, 1) if base_cost else 0,
            "件数": len(r["行明细"]),
        })
    rows.sort(key=lambda x: x["出厂成本"])
    return {"档位对比": rows,
            "最低": rows[0]["档位"] if rows else "",
            "最高": rows[-1]["档位"] if rows else "",
            "倍数": round(rows[-1]["出厂成本"] / rows[0]["出厂成本"], 2) if rows and rows[0]["出厂成本"] else 0}
