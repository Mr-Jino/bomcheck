# -*- coding: utf-8 -*-
"""
bomcheck —— 硬件 BOM 核价器
===========================
把一份 BOM 拆成九项成本，每一项都带算式；再拿它去比对面那份报价。

    from bomcheck import calculate, Book
    r = calculate(bom_dict, Book(), quote=4000)
    print(r["出厂成本"], r["报价除出厂"])
"""
from .pricebook import Book, default_path, load
from .engine import calculate, compare

__version__ = "1.0.0"
__all__ = ["calculate", "compare", "Book", "default_path", "load", "__version__"]
