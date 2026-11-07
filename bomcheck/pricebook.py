# -*- coding: utf-8 -*-
"""
pricebook —— 价表加载
=====================
价表是一份明文 JSON，不是加密的，也不需要联网。

查找顺序：
    1. 环境变量 BOMCHECK_PRICEBOOK 指定的路径
    2. 当前目录下的 pricebook.json
    3. ~/.bomcheck/pricebook.json

价表里没有的件，可以在 BOM 行里直接写 "单价"，两者都缺就直接报错——
宁可让程序停下来，也不要用一个猜出来的价格去算成本。
"""
import json
import os
from pathlib import Path

PKG_DIR = Path(__file__).resolve().parent
REPO_BOOK = PKG_DIR.parent / "pricebook.json"


def default_path() -> Path:
    env = os.environ.get("BOMCHECK_PRICEBOOK")
    if env:
        return Path(env).expanduser()
    here = Path.cwd() / "pricebook.json"
    if here.exists():
        return here
    home = Path.home() / ".bomcheck" / "pricebook.json"
    if home.exists():
        return home
    return REPO_BOOK


_cache = {}


def load(path=None) -> dict:
    p = Path(path).expanduser() if path else default_path()
    key = str(p.resolve()) if p.exists() else str(p)
    if key in _cache:
        return _cache[key]
    if not p.exists():
        raise FileNotFoundError(f"找不到价表：{p}\n用 BOMCHECK_PRICEBOOK 指定，或把 pricebook.json 放到当前目录。")
    with open(p, "r", encoding="utf-8") as f:
        book = json.load(f)
    _cache[key] = book
    return book


class Book:
    """价表的一层薄封装，只做三件事：查价、查类别、查商务参数。"""

    def __init__(self, data: dict = None, path=None):
        self.data = data if data is not None else load(path)
        self.path = str(path or default_path())

    # ---------------- 单价 ----------------
    def price(self, spec: str):
        item = self.data.get("价格", {}).get(spec)
        return None if item is None else float(item["价"])

    def category(self, spec: str, fallback: str = None):
        item = self.data.get("价格", {}).get(spec) or {}
        return item.get("类别") or fallback

    # ---------------- 参数 ----------------
    def proc(self, name: str, default=None):
        return float(self.data.get("加工", {}).get(name, default))

    def loss(self, category: str) -> float:
        table = self.data.get("损耗率", {})
        return float(table.get(category, table.get("_默认", 0.03)))

    def biz(self, name: str, default=None):
        v = self.data.get("商务", {}).get(name, default)
        return v

    def tier_multiple(self, tier: str) -> float:
        return float(self.data.get("商务", {}).get("报价倍数", {}).get(tier, 2.6))

    def redline(self, name: str) -> float:
        return float(self.data.get("商务", {}).get("红旗倍数", {}).get(name, 0.0))
