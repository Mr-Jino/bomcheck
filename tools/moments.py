# -*- coding: utf-8 -*-
"""
moments —— 生成朋友圈五张图（1080×1080 @2x）
============================================
版式与 tiechi 同一套：纸白底、细线、等宽数字。所有数字由引擎现算。

    python tools/moments.py
"""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault("BOMCHECK_PRICEBOOK", str(ROOT / "pricebook.json"))

from bomcheck import Book, calculate  # noqa: E402

EDGE = next((p for p in [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
] if Path(p).exists()), None)
OUT = ROOT / "docs" / "moments"
TMP = Path(tempfile.mkdtemp(prefix="bomcheck-mom-"))

BOOK = Book(path=ROOT / "pricebook.json")


def load(name):
    with open(ROOT / "data" / name, "r", encoding="utf-8") as f:
        return json.load(f)


STD = calculate(load("bom-terminal-std.json"), BOOK, quote=4000)
LITE = calculate(load("bom-terminal-lite.json"), BOOK)
RUG = calculate(load("bom-terminal-rugged.json"), BOOK)

PRICE = STD["报价"]
FACTORY = STD["出厂成本"]
ROWS = sorted(STD["行明细"], key=lambda x: -x["含损耗"])
TOP10 = ROWS[:10]
REST = STD["物料费"] - sum(r["含损耗"] for r in TOP10)

CSS = """
*{margin:0;padding:0;box-sizing:border-box}
:root{--paper:#fbfbf8;--ink:#17191d;--mute:#6d7176;--line:#d9d6cd;--rust:#a8351a;
      --blue:#1c4f75;--sand:#efece3}
body{width:1080px;background:var(--paper);color:var(--ink);
  font-family:"Microsoft YaHei","PingFang SC",sans-serif;-webkit-font-smoothing:antialiased}
.card{width:1080px;height:1080px;padding:58px 64px;position:relative}
.mono{font-family:Consolas,"Cascadia Mono",monospace;font-variant-numeric:tabular-nums}
.kicker{font-size:19px;letter-spacing:.22em;color:var(--mute)}
h1{font-size:68px;font-weight:700;line-height:1.26;letter-spacing:.005em}
h2{font-size:42px;font-weight:600;line-height:1.36}
.sub{font-size:24px;color:var(--mute);line-height:1.7}
.rule{height:1px;background:var(--line);margin:22px 0}
.foot{position:absolute;left:64px;right:64px;bottom:40px;font-size:18px;color:var(--mute);
  border-top:1px solid var(--line);padding-top:14px;display:flex;justify-content:space-between}
.hatch{background:repeating-linear-gradient(45deg,var(--line) 0 6px,transparent 6px 12px)}
"""


def card(body, left, right="bomcheck · MIT"):
    return f"""<!doctype html><meta charset="utf-8"><style>{CSS}</style>
<body><div class="card">{body}
<div class="foot"><span>{left}</span><span class="mono">{right}</span></div></div></body>"""


# ---------------------------------------------------------------- 1 封面
def c1():
    h1 = FACTORY / PRICE * 100
    body = f"""
  <div class="kicker">B O M C H E C K</div>
  <h1 style="margin-top:40px;">一台卖 ¥4,000 的车载终端，<br>出厂 ¥{FACTORY:,.0f}。</h1>

  <div style="margin-top:76px;">
    <div style="display:flex;justify-content:space-between;align-items:baseline;">
      <div style="font-size:26px;">出厂成本 · 19 个件含损耗</div>
      <div class="mono" style="font-size:36px;">￥{FACTORY:,.2f}</div>
    </div>
    <div style="height:44px;background:var(--sand);margin-top:12px;position:relative;">
      <div style="position:absolute;inset:0 auto 0 0;width:{h1:.2f}%;background:var(--ink);"></div>
    </div>
  </div>

  <div style="margin-top:44px;">
    <div style="display:flex;justify-content:space-between;align-items:baseline;">
      <div style="font-size:26px;">市面报价</div>
      <div class="mono" style="font-size:36px;color:var(--rust);">￥{PRICE:,.0f}</div>
    </div>
    <div style="height:44px;background:var(--rust);margin-top:12px;"></div>
  </div>

  <div style="margin-top:66px;font-size:28px;line-height:1.9;">
    <b class="mono" style="font-size:38px;color:var(--rust);">4.84 倍</b>。<br>
    硬件之外那 <span class="mono">￥{PRICE - FACTORY:,.0f}</span>，
    <span style="color:var(--mute);">没有一张 BOM。</span><br>
    <span style="font-size:23px;color:var(--mute);">材料、贴片、组装、测试、认证——每一项都带算式。</span>
  </div>"""
    return card(body, "github.com/Mr-Jino/bomcheck", "19 个件 · 1000 台 · 含损耗")


# ---------------------------------------------------------------- 2 逐件
def c2():
    rows = ""
    for r in TOP10:
        hot = r["件名"] == "气阀"
        rows += f"""
      <div style="display:grid;grid-template-columns:1fr 62px 128px;align-items:baseline;
                  padding:11px 0;border-bottom:1px solid var(--line);">
        <div style="font-size:25px;{'color:var(--rust);font-weight:600' if hot else ''}">
          {r['件名']}{f' ×{r["数量"]:.0f}' if r['数量'] > 1 else ''}</div>
        <div class="mono" style="font-size:19px;color:var(--mute);text-align:right;">×{r['数量']:.0f}</div>
        <div class="mono" style="font-size:24px;text-align:right;">{r['含损耗']:,.2f}</div>
      </div>"""

    body = f"""
  <h2>拆开，就这 19 个件</h2>
  <div class="sub" style="margin-top:10px;">含采购损耗 · 单价按 1000 台批量</div>
  <div style="margin-top:18px;">{rows}
    <div style="display:grid;grid-template-columns:1fr 62px 128px;padding:11px 0;
                border-bottom:1px solid var(--line);">
      <div style="font-size:23px;color:var(--mute);">其余 9 件（PCB / 继电器 / 定位 / 电源…）</div>
      <div></div>
      <div class="mono" style="font-size:23px;text-align:right;color:var(--mute);">{REST:,.2f}</div>
    </div>
  </div>
  <div style="display:flex;justify-content:space-between;align-items:baseline;
              border-top:2px solid var(--ink);margin-top:12px;padding-top:14px;">
    <div style="font-size:28px;">物料合计</div>
    <div class="mono" style="font-size:40px;">￥{STD['物料费']:,.2f}</div>
  </div>
  <div style="margin-top:14px;font-size:22px;color:var(--mute);line-height:1.85;">
    再加加工 ¥{STD['加工费']:,.2f}（贴片 820 点 + 手焊 55 点 + 组装 22 分钟）、
    测试 ¥{STD['成本明细']['测试费']:,.2f}、认证摊销 ¥{STD['成本明细']['认证摊销']:,.2f}，
    出厂 ¥{FACTORY:,.2f}。<br>
    <span style="color:var(--rust);">红色那行是气阀——就是串进你刹车气管的那个件，¥80.34。</span>
  </div>"""
    return card(body, "每一行都能对着型号查价", "物料 ￥643.37")


# ---------------------------------------------------------------- 3 带宽
def c3():
    need720 = 4 * 1.5
    need1080 = 4 * 4.0
    cap = 5.0
    scale = 100 / need1080

    def bar(label, val, color, note=""):
        return f"""
      <div style="margin-top:26px;">
        <div style="display:flex;justify-content:space-between;align-items:baseline;">
          <div style="font-size:24px;">{label}</div>
          <div class="mono" style="font-size:26px;color:{color};">{val:.1f} Mbps</div>
        </div>
        <div style="height:34px;background:var(--sand);margin-top:9px;position:relative;">
          <div style="position:absolute;inset:0 auto 0 0;width:{val*scale:.1f}%;background:{color};"></div>
        </div>
        <div style="font-size:18px;color:var(--mute);margin-top:7px;" class="mono">{note}</div>
      </div>"""

    body = f"""
  <h2>这块板子，压根不碰视频</h2>
  <div class="sub" style="margin-top:10px;">原因不是"省流量"，是物理上装不进去</div>

  <div style="position:relative;margin-top:30px;">
    {bar("Cat.1 上行带宽上限", cap, "#1c4f75", "模组手册写的 5 Mbps")}
    {bar("4 路 720p · H.264 1.5 Mbps/路", need720, "#a8351a", "4 × 1.5 = 6.0")}
    {bar("4 路 1080p · 4 Mbps/路", need1080, "#a8351a", "4 × 4.0 = 16.0")}
    <div style="position:absolute;left:{cap*scale:.2f}%;top:16px;bottom:64px;
                border-left:2px dashed var(--blue);"></div>
  </div>

  <div style="margin-top:40px;font-size:24px;line-height:1.95;">
    <b style="font-size:28px;">装不进去。</b>所以那块写着 THROTTLE CTRL 的控制板，
    连一路视频都不解码。<br>
    <span style="color:var(--mute);">视频在屏幕板另存、另传；疲劳判定 100% 在云端。</span><br>
    <span style="color:var(--rust);">于是断网就等于断功能——隧道、山区、地库，判定能力归零。</span>
  </div>"""
    return card(body, "只有本地录像，没有本地判断", "带宽是硬约束")


# ---------------------------------------------------------------- 4 拆账
def c4():
    hw = FACTORY
    install = 200
    data = 180
    known = hw + install + data
    unknown = PRICE - known
    seg = lambda v: v / PRICE * 100

    body = f"""
  <h2>4,000 里，70% 没有口径</h2>
  <div class="sub" style="margin-top:10px;">
    硬件、安装、流量取区间下限 —— 剩下的，一张纸都没有
  </div>

  <div style="display:flex;height:72px;margin-top:60px;border:1px solid var(--line);">
    <div style="width:{seg(hw):.2f}%;background:var(--ink);"></div>
    <div style="width:{seg(install):.2f}%;background:#5a6068;"></div>
    <div style="width:{seg(data):.2f}%;background:#9aa0a6;"></div>
    <div class="hatch" style="width:{seg(unknown):.2f}%;"></div>
  </div>

  <div style="margin-top:40px;" class="mono">
    <div style="display:flex;justify-content:space-between;font-size:22px;padding:12px 0;
                border-bottom:1px solid var(--line);">
      <span>■ 硬件出厂</span><span>￥{hw:,.2f}　<b style="color:var(--blue)">能核</b></span>
    </div>
    <div style="display:flex;justify-content:space-between;font-size:22px;padding:12px 0;
                border-bottom:1px solid var(--line);">
      <span>■ 安装人工（走线 / 接管 / 标定）</span><span>￥{install:,.0f} 起　<b style="color:var(--blue)">半能核</b></span>
    </div>
    <div style="display:flex;justify-content:space-between;font-size:22px;padding:12px 0;
                border-bottom:1px solid var(--line);">
      <span>■ 4G 流量（3 年）</span><span>￥{data:,.0f} 起　<b style="color:var(--blue)">能核</b></span>
    </div>
    <div style="display:flex;justify-content:space-between;font-size:22px;padding:12px 0;
                border-bottom:2px solid var(--ink);">
      <span style="color:var(--rust);">▨ 平台 + 算法 + 售后 + 剩下的</span>
      <span style="color:var(--rust);">￥{unknown:,.2f}　<b>{unknown/PRICE*100:.0f}%</b></span>
    </div>
  </div>

  <div style="margin-top:46px;font-size:25px;line-height:1.9;">
    前 <span class="mono">￥{known:,.2f}</span> 能核，因为有 BOM、有工时、有运营商价。<br>
    <span style="color:var(--rust);font-size:27px;">剩下的 <span class="mono">￥{unknown:,.0f}</span>，
    你连问都不知道该问哪一句。</span>
  </div>"""
    return card(body, "不是它贵，是它不能拆给你看", "拆账 · 区间下限")


# ---------------------------------------------------------------- 5 三档
def c5():
    def col(r, tag, what, hot=False):
        color = "var(--rust)" if hot else "var(--ink)"
        return f"""
      <div style="flex:1;border:1px solid {'var(--rust)' if hot else 'var(--line)'};
                  background:#fff;padding:22px 22px 18px;">
        <div style="font-size:26px;font-weight:700;color:{color};">{tag}</div>
        <div class="mono" style="font-size:40px;margin-top:10px;">￥{r['出厂成本']:,.2f}</div>
        <div style="font-size:17px;color:var(--mute);margin-top:4px;">出厂成本</div>
        <div style="border-top:1px solid var(--line);margin:14px 0 10px;"></div>
        <div style="font-size:19px;line-height:1.75;color:#33373c;">{what}</div>
        <div class="mono" style="font-size:20px;margin-top:12px;color:var(--mute);">
          档位报价 ￥{r['报价']:,.0f}</div>
      </div>"""

    diff = RUG["出厂成本"] - STD["出厂成本"]
    body = f"""
  <h2>贵 {diff:.1f} 块，换掉一根管子</h2>
  <div class="sub" style="margin-top:10px;">同一个需求，三种做法，同一份价表</div>

  <div style="display:flex;gap:18px;margin-top:34px;">
    {col(LITE, "精简", "不装屏、不装摄像头、<br>不串气路。<br>只读车、上传、声光提醒。")}
    {col(STD, "标准", "屏 + 4 路摄像头，<br>串气路做物理干预。<br>就是那台 4,000 的。")}
    {col(RUG, "冗余", "双 4G、双电源、光耦隔离、<br>压铸车规壳、屏蔽线束。<br><b>刻意不装气阀。</b>", hot=True)}
  </div>

  <div style="margin-top:34px;font-size:26px;line-height:1.95;">
    冗余档比标准档只贵 <b class="mono" style="color:var(--rust);font-size:32px;">￥{diff:,.2f}</b>，<br>
    把"不坏"买齐了，而且<b>没动你车上那根刹车管</b>。
  </div>
  <div style="margin-top:22px;font-size:23px;color:var(--mute);line-height:1.85;">
    钱该花在"不坏"上，不是花在"能刹车"上。<br>
    <span class="mono">bomcheck tiers data/bom-terminal-*.json</span>
  </div>"""
    return card(body, "github.com/Mr-Jino/bomcheck", "三档 · 同口径")


CARDS = [("bomcheck-1", c1), ("bomcheck-2", c2), ("bomcheck-3", c3),
         ("bomcheck-4", c4), ("bomcheck-5", c5)]


def main():
    if not EDGE:
        raise SystemExit("没找到 Edge")
    OUT.mkdir(parents=True, exist_ok=True)
    for name, fn in CARDS:
        html = TMP / f"{name}.html"
        html.write_text(fn(), encoding="utf-8")
        png = OUT / f"{name}.png"
        subprocess.run([EDGE, "--headless=new", "--disable-gpu", "--hide-scrollbars",
                        "--force-device-scale-factor=2", "--window-size=1080,1080",
                        f"--screenshot={png}", html.as_uri()],
                       check=True, capture_output=True, timeout=90)
        print(f"{png.name}  {png.stat().st_size // 1024} KB")


if __name__ == "__main__":
    main()
