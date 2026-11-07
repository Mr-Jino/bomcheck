# -*- coding: utf-8 -*-
"""
cli —— 命令行入口
=================
    python -m bomcheck.cli check data/bom-terminal-std.json --quote 4000
    python -m bomcheck.cli tiers data/bom-terminal-lite.json data/bom-terminal-std.json
    python -m bomcheck.cli book
    python -m bomcheck.cli schema
"""
import argparse
import json
import sys
import unicodedata
from pathlib import Path

from .engine import calculate, compare
from .pricebook import Book, default_path

SCHEMA_TEXT = """
BOM 字段
--------
名称      整机名，随意
档位      精简 / 标准 / 项目制 —— 决定报价倍数（价表「商务.报价倍数」）
批量      台数，认证费按它摊销
加工.贴片点数 / 手焊点数 / 组装分钟 / 测试分钟   工时口径，没填就用默认值
行[]      每一行是一个件：
    件名   人看的名字
    规格   价表里的键（如 A7670C）
    数量   用量
    单价   不填就从价表查；填了就以你填的为准（会拉低置信度）
    备注   随意

价表字段
--------
价格.<规格>.价      单价，元
价格.<规格>.类别    决定采购损耗率
加工.*              元/点、元/分钟
损耗率.<类别>       采购损耗
商务.*              不良率、摊销率、包装、物流、认证一次性总额、报价倍数、红旗倍数
"""


def _w(s) -> int:
    return sum(2 if unicodedata.east_asian_width(c) in "WF" else 1 for c in str(s))


def _pad(s, width, right=False) -> str:
    gap = " " * max(1, width - _w(s))
    return gap + str(s) if right else str(s) + gap


def _load(path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def cmd_check(args):
    book = Book(path=args.pricebook) if args.pricebook else Book()
    r = calculate(_load(args.bom), book, quote=args.quote)

    if args.json:
        print(json.dumps(r, ensure_ascii=False, indent=2))
        return 0

    print()
    print(f"  {r['名称']}    [{r['档位']}档 · {r['批量']:,.0f} 台]")
    print("  " + "─" * 62)

    print(f"  {'件名':<10}{'规格':<22}{'数量':>4}{'单价':>9}{'含损耗':>10}")
    for ln in r["行明细"]:
        print(f"  {_pad(ln['件名'], 10)}{_pad(ln['规格'], 22)}{ln['数量']:>4.0f}"
              f"{ln['单价']:>9.2f}{ln['含损耗']:>10.2f}")

    print("  " + "─" * 62)
    for s in r["算式"]:
        print(f"  {_pad(s['名称'], 16)}{s['金额']:>12,.2f}   {s['算式']}")

    print("  " + "─" * 62)
    print(f"  {_pad('出厂成本', 16)}{r['出厂成本']:>12,.2f}")
    print(f"  {_pad('报价', 16)}{r['报价']:>12,.2f}   {r['报价来源']}")
    print(f"  {_pad('毛利', 16)}{r['毛利']:>12,.2f}   毛利率 {r['毛利率']*100:.1f}%")
    print(f"  {_pad('倍数', 16)}{r['报价除出厂']:>12,.2f} × 出厂   {r['报价除物料']:.2f} × 物料")

    if r["红旗"]:
        print("  " + "─" * 62)
        for f in r["红旗"]:
            print(f"  [{f['级别']}] {f['说明']}")
    for w in r["告警"]:
        print(f"  注意：{w}")

    print(f"  置信度 {r['confidence_level']}　{r['提示']}")
    print()
    return 0


def cmd_tiers(args):
    book = Book(path=args.pricebook) if args.pricebook else Book()
    results = [calculate(_load(p), book) for p in args.boms]
    c = compare(results)

    print()
    print(f"  {'档位':<8}{'件数':>5}{'物料费':>12}{'出厂成本':>12}{'报价':>12}{'较最低':>12}")
    print("  " + "─" * 64)
    for row in c["档位对比"]:
        print(f"  {_pad(row['档位'], 8)}{row['件数']:>5}{row['物料费']:>12,.2f}"
              f"{row['出厂成本']:>12,.2f}{row['报价']:>12,.2f}{row['较最低档']:>+12,.2f}")
    print("  " + "─" * 64)
    print(f"  最高档 / 最低档 = {c['倍数']:.2f} 倍出厂成本")
    print()
    return 0


def cmd_book(args):
    book = Book(path=args.pricebook) if args.pricebook else Book()
    print(f"\n  价表：{book.path}\n")
    items = book.data.get("价格", {})
    print(f"  {'规格':<22}{'单价':>9}   类别")
    print("  " + "─" * 48)
    for spec, item in items.items():
        print(f"  {_pad(spec, 22)}{float(item['价']):>9.2f}   {item.get('类别','')}")
    print(f"\n  共 {len(items)} 个件。改价直接改这份 JSON，或用 BOMCHECK_PRICEBOOK 指到自己的。\n")
    return 0


def cmd_schema(args):
    print(SCHEMA_TEXT)
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(prog="bomcheck", description="硬件 BOM 核价器")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p1 = sub.add_parser("check", help="核一份 BOM")
    p1.add_argument("bom")
    p1.add_argument("--quote", type=float, default=None, help="外部报价，用来比倍数")
    p1.add_argument("--pricebook", default=None)
    p1.add_argument("--json", action="store_true")
    p1.set_defaults(func=cmd_check)

    p2 = sub.add_parser("tiers", help="多档并排")
    p2.add_argument("boms", nargs="+")
    p2.add_argument("--pricebook", default=None)
    p2.set_defaults(func=cmd_tiers)

    p3 = sub.add_parser("book", help="看价表")
    p3.add_argument("--pricebook", default=None)
    p3.set_defaults(func=cmd_book)

    p4 = sub.add_parser("schema", help="字段说明")
    p4.set_defaults(func=cmd_schema)

    args = ap.parse_args(argv)
    try:
        return args.func(args)
    except (ValueError, FileNotFoundError) as e:
        print(f"\n  {e}\n", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
