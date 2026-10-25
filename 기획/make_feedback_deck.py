# -*- coding: utf-8 -*-
"""피드백 반영 수정 기획안 PPT 생성 (python-pptx)."""
import os
import numpy as np
from PIL import Image, ImageFilter
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE, MSO_CONNECTOR
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.oxml.ns import qn

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
ASSET = os.environ.get("DECK_ASSET", os.path.join(HERE, "_assets"))
os.makedirs(ASSET, exist_ok=True)
OUT = os.path.join(ROOT, "피드백_수정기획안.pptx")

# ---------- 팔레트 (기존 발표 PPT 톤) ----------
BG = RGBColor(0x14, 0x20, 0x1A)
PANEL = RGBColor(0x1F, 0x31, 0x27)
PANEL2 = RGBColor(0x29, 0x40, 0x33)
GOLD = RGBColor(0xF0, 0xC4, 0x7C)
CREAM = RGBColor(0xFB, 0xF5, 0xDE)
MUTED = RGBColor(0xB3, 0xC2, 0xAE)
GREEN = RGBColor(0x7F, 0xB0, 0x78)
DARKTXT = RGBColor(0x14, 0x20, 0x1A)

F_XB, F_SB, F_R = "Pretendard ExtraBold", "Pretendard SemiBold", "Pretendard"


# ---------- 배경 이미지 준비 ----------
def prep_assets(bg_src):
    def load(n): return Image.open(os.path.join(bg_src, n)).convert("RGB").resize((1920, 1080), Image.LANCZOS)
    dark = np.array([20, 32, 26], np.float32)
    # 표지: 초원 + 왼쪽 어둡게
    im = np.asarray(load("image.jpg")).astype(np.float32)
    x = np.linspace(0, 1, 1920)[None, :, None]
    a = np.clip(1.05 - x * 1.5, 0.15, 0.88)
    Image.fromarray((im * (1 - a) + dark * a).astype(np.uint8)).save(os.path.join(ASSET, "bg_title.jpg"), quality=92)
    # 섹션/마무리: 숲길 어둡게
    for name, src, k in (("bg_trail.jpg", "image2.jpg", 0.62), ("bg_village.jpg", "image5.jpg", 0.66)):
        im = np.asarray(load(src)).astype(np.float32)
        Image.fromarray((im * (1 - k) + dark * k).astype(np.uint8)).save(os.path.join(ASSET, name), quality=92)


# ---------- 헬퍼 ----------
prs = Presentation()
prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)
BLANK = prs.slide_layouts[6]


def set_bg(slide, color=BG, image=None):
    if image:
        slide.shapes.add_picture(image, 0, 0, prs.slide_width, prs.slide_height)
    else:
        f = slide.background.fill; f.solid(); f.fore_color.rgb = color


def set_alpha(shape, alpha):
    """채우기 투명도 (alpha 0~100, 100=불투명)"""
    sf = shape.fill._xPr.find(qn("a:solidFill"))
    clr = sf[0]
    a = clr.makeelement(qn("a:alpha"), {"val": str(int(alpha * 1000))})
    clr.append(a)


def box(slide, x, y, w, h, fill=PANEL, line=None, shape=MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.08, alpha=None):
    s = slide.shapes.add_shape(shape, Inches(x), Inches(y), Inches(w), Inches(h))
    if fill is None:
        s.fill.background()
    else:
        s.fill.solid(); s.fill.fore_color.rgb = fill
        if alpha is not None: set_alpha(s, alpha)
    if line is None: s.line.fill.background()
    else: s.line.color.rgb = line; s.line.width = Pt(1.25)
    if shape == MSO_SHAPE.ROUNDED_RECTANGLE:
        s.adjustments[0] = radius
    s.shadow.inherit = False
    s.text_frame.text = ""
    return s


def text(slide, x, y, w, h, runs, size=16, color=CREAM, font=F_R, bold=False, align=PP_ALIGN.LEFT,
         anchor=MSO_ANCHOR.TOP, spacing=1.1, name=None):
    """runs: str | [str, ...](문단) | [[(텍스트, {opts}), ...], ...]"""
    tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame; tf.word_wrap = True
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    tf.vertical_anchor = anchor
    paras = [runs] if isinstance(runs, str) else runs
    for i, p in enumerate(paras):
        para = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        para.alignment = align; para.line_spacing = spacing
        segs = [(p, {})] if isinstance(p, str) else p
        for t, o in segs:
            r = para.add_run(); r.text = t
            f = r.font; f.size = Pt(o.get("size", size)); f.name = o.get("font", font)
            f.bold = o.get("bold", bold); f.color.rgb = o.get("color", color)
            rPr = r._r.get_or_add_rPr()
            for tag in ("a:ea", "a:cs"):
                e = rPr.find(qn(tag))
                if e is None: e = rPr.makeelement(qn(tag), {}); rPr.append(e)
                e.set("typeface", o.get("font", font))
    if name: tb.name = name
    return tb


def shape_text(s, t, size=14, color=CREAM, font=F_SB, bold=False, align=PP_ALIGN.CENTER):
    tf = s.text_frame; tf.word_wrap = True
    tf.margin_left = tf.margin_right = Inches(0.05); tf.margin_top = tf.margin_bottom = 0
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    lines = t.split("\n")
    for i, l in enumerate(lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        r = p.add_run(); r.text = l
        r.font.size = Pt(size); r.font.name = font; r.font.bold = bold; r.font.color.rgb = color
        rPr = r._r.get_or_add_rPr()
        for tag in ("a:ea", "a:cs"):
            e = rPr.makeelement(qn(tag), {"typeface": font}); rPr.append(e)


def title(slide, t, sub=None):
    text(slide, 0.7, 0.55, 10.5, 0.8, t, size=34, font=F_XB, color=CREAM)
    if sub: text(slide, 0.72, 1.32, 10.5, 0.4, sub, size=15, font=F_SB, color=GOLD)


def arrow(slide, x1, y1, x2, y2, color=GOLD, width=2.25):
    c = slide.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, Inches(x1), Inches(y1), Inches(x2), Inches(y2))
    c.line.color.rgb = color; c.line.width = Pt(width)
    ln = c.line._get_or_add_ln()
    ln.append(ln.makeelement(qn("a:tailEnd"), {"type": "triangle", "w": "med", "len": "med"}))
    return c


def circle(slide, cx, cy, d, fill, label=None, size=14, color=DARKTXT, font=F_XB):
    s = box(slide, cx - d / 2, cy - d / 2, d, d, fill=fill, shape=MSO_SHAPE.OVAL)
    if label: shape_text(s, label, size=size, color=color, font=font)
    return s


def photo(slide, name, x, y, w, h, crop_center=True):
    """사진을 지정 영역에 꽉 차게 (가운데 크롭)"""
    p = os.path.join(ROOT, name)
    iw, ih = Image.open(p).size
    pic = slide.shapes.add_picture(p, Inches(x), Inches(y), Inches(w), Inches(h))
    tr, ir = w / h, iw / ih
    if ir > tr:
        c = (1 - tr / ir) / 2; pic.crop_left = pic.crop_right = c
    else:
        c = (1 - ir / tr) / 2; pic.crop_top = pic.crop_bottom = c
    return pic


def notes(slide, t):
    slide.notes_slide.notes_text_frame.text = t


# =================================================================== 슬라이드
def build():
    # 1. 표지
    s = prs.slides.add_slide(BLANK); set_bg(s, image=os.path.join(ASSET, "bg_title.jpg"))
    text(s, 0.9, 1.0, 6, 0.4, "졸업작품 기획 · 피드백 반영", size=15, font=F_SB, color=GOLD)
    text(s, 0.9, 1.55, 7.5, 2.0, ["피드백 반영", "수정 기획안"], size=54, font=F_XB, color=CREAM, spacing=1.05)
    text(s, 0.92, 3.75, 7, 0.5, "승마 레이싱 & 육성 RPG", size=22, font=F_SB, color=CREAM)
    text(s, 0.92, 5.9, 7, 0.4, "김경준  ·  정진영  ·  강석주", size=14, color=MUTED)
    notes(s, "지난 발표에서 받은 피드백을 바탕으로 게임 기획을 수정했습니다. 오늘은 무엇을 바꾸고 무엇을 더했는지 말씀드리겠습니다.")

    # 2. PART 1 도입 — 실제 승마의 구조
    s = prs.slides.add_slide(BLANK); set_bg(s)
    text(s, 0.7, 0.55, 8, 0.4, "PART 1  기승 조작 시스템", size=14, font=F_SB, color=GOLD)
    text(s, 0.7, 0.95, 11.5, 0.8, "기수는 부조로 말을 움직인다", size=32, font=F_XB)
    text(s, 0.72, 1.7, 11.8, 0.4, "부조(扶助, Aids): 기수가 손 · 다리 · 체중 · 도구로 말에게 보내는 신호", size=14, color=MUTED)

    # 구조 도식: 기수 → 부조 → 말 → 움직임
    flow = [("기수", "신호를 보낸다", PANEL2, CREAM), ("부조", "손 · 다리 · 체중 · 도구", GOLD, DARKTXT),
            ("말", "보법과 리듬으로 반응", PANEL2, CREAM), ("움직임", "방향 · 속도 · 도약", PANEL2, CREAM)]
    x = 0.7
    for i, (a_, b_, fc, tc) in enumerate(flow):
        box(s, x, 2.45, 2.6, 1.25, fill=fc)
        text(s, x, 2.45, 2.6, 1.25, [[(a_, {"size": 22, "font": F_XB, "color": tc})], [(b_, {"size": 12.5, "color": tc})]],
             align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE, spacing=1.25)
        if i < 3: arrow(s, x + 2.66, 3.075, x + 3.06, 3.075)
        x += 3.1

    # 부조의 종류 + 말의 움직임
    cards = [("자연 부조", "기수의 몸으로 보내는 신호", [("손 (고삐)", "방향 전환 · 감속"), ("다리", "전진 · 가속"), ("기좌 · 체중", "균형 · 코너링 · 자세")], GREEN),
             ("인공 부조", "도구로 보강하는 신호", [("채찍", "다리 신호 보강, 순간 추진"), ("박차", "더 강한 다리 신호")], GREEN),
             ("말의 움직임", "기수가 맞춰야 하는 리듬", [("보법", "평보 → 속보 → 구보 → 습보"), ("리듬", "걸음마다 일정한 박자")], GOLD)]
    x = 0.7
    for nm, sub, rows_, col in cards:
        box(s, x, 4.05, 3.83, 2.85, fill=PANEL)
        text(s, x + 0.3, 4.27, 3.4, 0.45, nm, size=21, font=F_XB, color=col)
        text(s, x + 0.3, 4.75, 3.4, 0.35, sub, size=12.5, color=MUTED)
        yy = 5.3
        for k_, v_ in rows_:
            text(s, x + 0.3, yy, 3.5, 0.4, [[(k_ + "   ", {"font": F_SB, "size": 14.5, "color": CREAM}), (v_, {"size": 13, "color": MUTED})]])
            yy += 0.5
        x += 3.99
    notes(s, "실제 승마에서 기수는 부조라는 신호로 말을 움직입니다. 부조에는 고삐, 다리, 체중처럼 몸을 쓰는 자연 부조와, "
             "채찍이나 박차처럼 도구를 쓰는 인공 부조가 있습니다. 말은 이 신호를 받아 평보, 속보, 구보, 습보의 보법으로 움직이고, "
             "걸음마다 일정한 리듬이 있습니다. 이 구조를 게임에 어떻게 옮겼는지 설명드리겠습니다.")

    # 4. 7가지 승마 조작
    s = prs.slides.add_slide(BLANK); set_bg(s)
    title(s, "실제 승마 기술을 게임으로", "7가지 기승 조작")
    items = [("고삐", "방향 전환 · 감속"), ("다리(박차)", "가속, 스태미나 소모"), ("자세", "코너링 · 최고 속도"),
             ("보법", "구보 / 습보 모드 전환"), ("리듬", "박자에 맞추면 효율 가속"), ("점프", "장애물 타이밍"),
             ("채찍", "레이스당 횟수 제한 순간 가속")]
    pos = [(0.7, 2.0), (3.75, 2.0), (6.8, 2.0), (9.85, 2.0), (2.22, 4.35), (5.27, 4.35), (8.32, 4.35)]
    for i, ((nm, ef), (x, y)) in enumerate(zip(items, pos)):
        hl = False
        box(s, x, y, 2.8, 2.05, fill=PANEL2 if hl else PANEL, line=GOLD if hl else None)
        circle(s, x + 0.55, y + 0.55, 0.62, GOLD if hl else GREEN, str(i + 1), size=16)
        text(s, x + 0.3, y + 1.0, 2.3, 0.5, nm, size=20, font=F_XB, color=GOLD if hl else CREAM)
        text(s, x + 0.3, y + 1.5, 2.35, 0.5, ef, size=13, color=CREAM)
    notes(s, "실제 승마의 부조 기술을 일곱 가지 조작으로 옮겼습니다. 고삐, 다리, 자세, 보법, 리듬, 점프, 채찍입니다. 이 중 보법과 리듬이 일반 레이싱 게임과 가장 다른 부분입니다.")

    # 4. 조작 키
    s = prs.slides.add_slide(BLANK); set_bg(s)
    title(s, "왼손은 말을, 오른손은 기수의 몸을", "키보드 조작")

    def key(x, y, w, lab, desc, fill):
        k = box(s, x, y, w, 0.78, fill=fill, radius=0.18)
        shape_text(k, lab, size=15, color=DARKTXT, font=F_XB)
        if desc: text(s, x - 0.2, y + 0.85, w + 0.4, 0.35, desc, size=10.5, color=CREAM, align=PP_ALIGN.CENTER)
    L = GOLD
    key(0.9, 2.2, 1.1, "Tab", "채찍", L)
    key(2.25, 2.2, 0.8, "W", "가속 · 리듬", L)
    key(0.9, 3.45, 1.3, "Shift", "구보↔습보", L)
    key(2.4, 3.45, 0.8, "A", "좌", L); key(3.3, 3.45, 0.8, "S", "감속", L); key(4.2, 3.45, 0.8, "D", "우", L)
    key(1.6, 4.7, 3.0, "Space", "점프", L)
    R = GREEN
    key(9.45, 2.85, 0.85, "↑", "레이싱 자세", R)
    key(8.5, 3.95, 0.85, "←", "몸 기울이기", R); key(10.4, 3.95, 0.85, "→", "몸 기울이기", R)
    text(s, 0.9, 1.75, 5, 0.35, "왼손 — 말 조작", size=15, font=F_XB, color=GOLD)
    text(s, 8.3, 1.75, 4, 0.35, "오른손 — 기수의 몸 (홀드)", size=15, font=F_XB, color=GREEN)
    # 난이도
    lv = [("입문", "W/S · A/D · Space"), ("기본", "+ 모드 전환 · 자세"), ("숙련", "+ 리듬 가속 · 채찍 타이밍")]
    x = 0.9
    for i, (a, b) in enumerate(lv):
        box(s, x, 6.05, 3.75, 0.7, fill=PANEL)
        text(s, x + 0.25, 6.05, 3.4, 0.7, [[(a + "   ", {"font": F_XB, "color": GOLD, "size": 15}), (b, {"size": 13})]],
             anchor=MSO_ANCHOR.MIDDLE)
        if i < 2: arrow(s, x + 3.8, 6.4, x + 4.05, 6.4, width=1.5)
        x += 4.0
    notes(s, "왼손으로는 말을 다룹니다. W와 S로 가속과 감속, A와 D로 방향, Shift로 보법 전환, Space로 점프, Tab으로 채찍입니다. 오른손은 기수의 몸입니다. 위 방향키를 누르고 있으면 몸을 숙인 레이싱 자세, 좌우 방향키는 몸을 기울여 코너를 돕습니다. 처음에는 가속, 방향, 점프만으로도 충분히 탈 수 있게 단계별로 익힙니다.")

    # 5. 보법 모드 + 리듬 (조작 키 다음)
    s = prs.slides.add_slide(BLANK); set_bg(s)
    title(s, "직선은 습보, 코너는 구보", "보법 모드와 리듬 — 우리 게임만의 차별점")
    # 트랙 도식: 직선(습보) — 코너(구보) — 직선(습보)
    ty = 2.95
    seg = box(s, 0.9, ty, 4.4, 0.42, fill=GOLD, radius=0.5)
    cor = box(s, 5.45, ty - 0.05, 2.4, 0.52, fill=GREEN, radius=0.5)
    seg2 = box(s, 8.0, ty, 4.4, 0.42, fill=GOLD, radius=0.5)
    shape_text(seg, "직선  ·  습보", size=13, color=DARKTXT, font=F_XB)
    shape_text(cor, "코너  ·  구보", size=13, color=DARKTXT, font=F_XB)
    shape_text(seg2, "직선  ·  습보", size=13, color=DARKTXT, font=F_XB)
    # 리듬 박자 점
    for k in range(7):
        circle(s, 1.35 + k * 0.6, ty - 0.35, 0.16, CREAM)
        circle(s, 8.45 + k * 0.6, ty - 0.35, 0.16, CREAM)
    text(s, 0.9, ty - 0.95, 5, 0.4, "♪  W를 말발굽 박자에 맞춰 누르면 리듬 가속", size=13, color=CREAM)
    # 비교 카드
    cards = [("습보", "직선용 전력 질주", ["최고 속도 높음", "회전 둔함", "스태미나 소모 큼"], GOLD),
             ("구보", "코너용 안정 주행", ["회전 안정", "스태미나 절약", "최고 속도 낮음"], GREEN),
             ("리듬", "말과 호흡 맞추기", ["W를 박자에 맞춰 입력", "스태미나 효율 · 속도 상승", "놓쳐도 기본 가속 유지"], CREAM)]
    x = 0.9
    for nm, sub, pts, col in cards:
        box(s, x, 3.75, 3.7, 2.6, fill=PANEL)
        text(s, x + 0.35, 3.95, 3.1, 0.5, nm, size=24, font=F_XB, color=col)
        text(s, x + 0.35, 4.5, 3.1, 0.4, sub, size=13, font=F_SB, color=MUTED)
        text(s, x + 0.35, 4.95, 3.1, 1.4, ["·  " + p for p in pts], size=14, color=CREAM, spacing=1.35)
        x += 3.85
    text(s, 0.9, 6.6, 11.5, 0.4, "언제 모드를 바꾸고, 얼마나 리듬을 맞추는지가 곧 실력", size=13, color=MUTED)
    notes(s, "직선에서는 빠른 습보로, 코너 전에는 안정적인 구보로 모드를 바꿉니다. 습보로 코너에 들어가면 밀려납니다. 또 W를 말발굽 박자에 맞춰 누르면 스태미나를 아끼면서 더 빨리 달릴 수 있습니다. 말과 호흡을 맞추는 감각을 손으로 느끼게 하는 것이 목표입니다.")

    # 7. 레이스 흐름
    s = prs.slides.add_slide(BLANK); set_bg(s, image=os.path.join(ASSET, "bg_trail.jpg"))
    title(s, "레이스 한 판의 흐름")
    steps = [("출발", "W 가속\nShift 습보\n↑ 레이싱 자세"), ("직선", "W 리듬 가속으로\n스태미나 절약"),
             ("코너", "S 감속 · Shift 구보\nA/D + ←/→\n몸 기울이기"), ("장애물", "기본 자세로 접근\nSpace 점프"),
             ("마지막 직선", "습보 + 레이싱 자세\nTab 채찍 추월")]
    x0, gap = 0.8, 2.48
    c = s.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, Inches(1.4), Inches(2.6), Inches(11.75), Inches(2.6))
    c.line.color.rgb = GOLD; c.line.width = Pt(2)
    for i, (nm, d) in enumerate(steps):
        x = x0 + i * gap
        circle(s, x + 0.6, 2.6, 0.75, GOLD, str(i + 1), size=18)
        text(s, x - 0.2, 3.2, 1.6 + 0.4, 0.5, nm, size=20, font=F_XB, align=PP_ALIGN.CENTER)
        b = box(s, x - 0.35, 3.85, 1.9, 1.45, fill=BG, alpha=75)
        text(s, x - 0.25, 3.98, 1.7, 1.3, d.split("\n"), size=12.5, align=PP_ALIGN.CENTER, spacing=1.3)
    text(s, 0.8, 6.55, 12, 0.4, "일곱 가지 조작이 한 판 안에서 모두 의미 있게 쓰인다", size=13, color=MUTED)
    notes(s, "실제 레이스 한 판은 이렇게 흘러갑니다. 출발해서 습보로 올리고, 직선에서는 리듬으로 체력을 아끼고, 코너 전에는 구보로 내려 몸을 기울여 돕니다. 장애물은 점프로 넘고, 마지막 직선에서 아껴둔 채찍으로 추월합니다.")

    # 8. 월드 구조 — 광활한 필드 위의 마을
    s = prs.slides.add_slide(BLANK); set_bg(s)
    text(s, 0.7, 0.55, 6, 0.4, "PART 2  필드 · 육성", size=14, font=F_SB, color=GOLD)
    text(s, 0.7, 0.95, 10, 0.8, "광활한 오픈 필드 위의 마을 3곳", size=34, font=F_XB)
    # 지도 (ChatGPT로 생성한 필드 지도, 비율 유지 · 모서리 둥글게)
    MX, MY, MH = 0.7, 1.95, 4.85
    iw_, ih_ = Image.open(os.path.join(ROOT, "필드지도.png")).size
    MW = MH * iw_ / ih_
    pic = s.shapes.add_picture(os.path.join(ROOT, "필드지도.png"), Inches(MX), Inches(MY), Inches(MW), Inches(MH))
    geom = pic._element.spPr.find(qn("a:prstGeom"))
    geom.set("prst", "roundRect")
    av = geom.find(qn("a:avLst"))
    if av is None: av = geom.makeelement(qn("a:avLst"), {}); geom.append(av)
    av.append(av.makeelement(qn("a:gd"), {"name": "adj", "fmla": "val 4500"}))
    # 마을 라벨 (그림 속 마을 위치 비율)
    for nm, fx, fy in [("마을 1", 0.15, 0.27), ("마을 2", 0.53, 0.07), ("마을 3", 0.86, 0.55)]:
        lb = box(s, MX + MW * fx - 0.55, MY + MH * fy - 0.2, 1.1, 0.4, fill=BG, alpha=78, line=GOLD, radius=0.5)
        shape_text(lb, nm, size=12, color=GOLD, font=F_XB)
    # 오른쪽 설명
    RX = MX + MW + 0.3
    RW = 12.65 - RX
    box(s, RX, MY, RW, MH, fill=PANEL)
    text(s, RX + 0.3, MY + 0.25, 3.3, 0.4, "마을 3곳", size=18, font=F_XB, color=GOLD)
    text(s, RX + 0.3, MY + 0.7, 3.4, 0.4, "마을마다 다른 콘셉트 · 분위기", size=13.5)
    text(s, RX + 0.3, MY + 1.35, 3.3, 0.4, "공통 시설", size=18, font=F_XB, color=GOLD)
    for k_, fac in enumerate(["마구간", "대회장", "상점", "퀘스트 게시판"]):
        cw_ = (RW - 0.7) / 2
        cx_ = RX + 0.3 + (k_ % 2) * (cw_ + 0.1); cy_ = MY + 1.85 + (k_ // 2) * 0.55
        c_ = box(s, cx_, cy_, cw_, 0.42, fill=PANEL2, radius=0.5)
        shape_text(c_, fac, size=12, color=CREAM, font=F_SB)
    text(s, RX + 0.3, MY + 3.1, 3.3, 0.4, "오픈 필드", size=18, font=F_XB, color=GOLD)
    text(s, RX + 0.3, MY + 3.55, 3.4, 1.2, ["마을 사이 어디든 자유롭게 탐험", "채집 · 점프 코스 · 숨겨진 수집품"],
         size=13, spacing=1.4)
    notes(s, "규모를 키우기 위해 오픈 필드를 추가했습니다. 마을과 마을을 잇는 길이 아니라, 넓은 필드 위에 콘셉트가 서로 다른 마을 세 곳이 자리 잡은 구조입니다. "
             "마을마다 마구간, 대회장, 상점, 퀘스트 게시판이 있고, 필드에서는 어디든 자유롭게 달리며 채집하고, 점프 코스를 넘어 숨겨진 수집품을 찾을 수 있습니다.")

    # 9. 필드 콘텐츠 — 기능 하나당 한 페이지
    field_pages = [
        dict(img="파밍.png", no="01", name="파밍", head=["필드에서", "먹이와 치장 재료를 모은다"],
             groups=[("먹이", "과일 · 채소 · 곡물 · 견과류", "말의 능력치 성장에 사용"),
                     ("치장 재료", "꽃 · 깃털 · 염료 열매 · 철광석 · 가죽", "치장 아이템 제작에 사용")],
             points=["E 키로 채집, 일정 시간 후 다시 생성", "말에서 내려야 닿는 채집 장소도 존재 (F 키)"],
             note="필드에서는 먹이와 치장 재료를 채집합니다. 과일, 채소, 곡물, 견과류 같은 먹이는 말의 능력치를 키우는 데 쓰고, "
                  "꽃, 깃털, 염료 열매, 철광석, 가죽 같은 재료는 치장 아이템을 만드는 데 씁니다. "
                  "채집물은 일정 시간이 지나면 다시 생기고, 일부는 말에서 내려야만 닿을 수 있는 곳에 있습니다."),
        dict(img="점프코스.png", no="02", name="점프 코스 · 수집품", head=["점프 코스를 넘어", "숨겨진 보물을 찾는다"],
             groups=[("점프 코스", "통나무 · 돌담 · 개울", "필드 곳곳에 배치, Space로 넘기"),
                     ("숨겨진 수집품", "황금 말굽 문양", "모으면 특별 치장 보상")],
             points=["필드에서 유일한 실력 요소", "탐험할 이유를 만드는 장치"],
             note="필드 곳곳에는 통나무, 돌담, 개울 같은 점프 코스가 있습니다. 점프 코스를 넘어야 갈 수 있는 숨겨진 장소에 황금 말굽 수집품이 있고, "
                  "일정 개수를 모으면 특별한 치장 아이템을 받습니다. 필드에서 유일하게 실력이 필요한 요소이자, 구석구석 탐험하게 만드는 장치입니다."),
        dict(img="퀘스트.png", no="03", name="마을 퀘스트", head=["마을에서 의뢰를 받아", "필드를 누빈다"],
             groups=[("수주", "퀘스트 게시판 · 마을 NPC", "마을마다 여러 종류의 퀘스트"),
                     ("보상", "돈 · 재료 · 아이템", "육성과 치장으로 이어짐")],
             points=["퀘스트 종류와 내용은 상세 설계 예정"],
             note="각 마을의 퀘스트 게시판이나 마을 사람들에게서 여러 종류의 퀘스트를 받을 수 있습니다. "
                  "퀘스트를 완료하면 돈, 재료, 아이템을 보상으로 받고, 이 보상은 말을 키우고 꾸미는 데 쓰입니다. 퀘스트의 구체적인 종류는 앞으로 상세하게 설계할 예정입니다."),
    ]
    for fp in field_pages:
        s = prs.slides.add_slide(BLANK); set_bg(s)
        text(s, 0.7, 0.55, 8, 0.4, f"필드 콘텐츠  {fp['no']}", size=14, font=F_SB, color=GOLD)
        text(s, 0.7, 0.95, 10, 0.8, fp["name"], size=34, font=F_XB)
        IX, IY, IW = 0.7, 1.9, 8.1
        iw_, ih_ = Image.open(os.path.join(ROOT, fp["img"])).size
        IH = IW * ih_ / iw_
        pic = s.shapes.add_picture(os.path.join(ROOT, fp["img"]), Inches(IX), Inches(IY), Inches(IW), Inches(IH))
        geom = pic._element.spPr.find(qn("a:prstGeom")); geom.set("prst", "roundRect")
        av = geom.find(qn("a:avLst"))
        if av is None: av = geom.makeelement(qn("a:avLst"), {}); geom.append(av)
        av.append(av.makeelement(qn("a:gd"), {"name": "adj", "fmla": "val 4500"}))
        RX = IX + IW + 0.3; RW = 12.65 - RX
        box(s, RX, IY, RW, IH, fill=PANEL)
        text(s, RX + 0.3, IY + 0.25, RW - 0.5, 0.8, fp["head"], size=16, font=F_XB, color=CREAM, spacing=1.2)
        yy = IY + 1.2
        for gname, gitems, guse in fp["groups"]:
            text(s, RX + 0.3, yy, RW - 0.5, 0.35, gname, size=15, font=F_XB, color=GOLD)
            text(s, RX + 0.3, yy + 0.36, RW - 0.5, 0.35, gitems, size=12.5, font=F_SB, color=CREAM)
            text(s, RX + 0.3, yy + 0.68, RW - 0.5, 0.35, guse, size=11.5, color=MUTED)
            yy += 1.12
        text(s, RX + 0.3, yy + 0.05, RW - 0.5, 0.9, ["·  " + p_ for p_ in fp["points"]], size=11.5, color=CREAM, spacing=1.35)
        notes(s, fp["note"])

    # 10. 먹이 육성
    s = prs.slides.add_slide(BLANK); set_bg(s)
    title(s, "먹이로 키우는 육성", "모든 성장은 레이스 성능으로 이어진다")
    foods = [("과일", "속도"), ("채소", "지구력"), ("곡물", "순발력"), ("견과류", "점프력")]
    cols = [RGBColor(0xE8, 0x7A, 0x5D), RGBColor(0xE9, 0xA2, 0x4A), RGBColor(0xD8, 0xC0, 0x6A), RGBColor(0xB0, 0x86, 0x5A)]
    x = 1.0
    for (f, st), col in zip(foods, cols):
        circle(s, x + 0.75, 2.75, 1.25, col, f, size=17)
        arrow(s, x + 0.75, 3.48, x + 0.75, 3.95, color=CREAM, width=1.75)
        b = box(s, x, 4.0, 1.5, 0.62, fill=PANEL2, radius=0.5)
        shape_text(b, st, size=15, color=GOLD, font=F_XB)
        x += 1.95
    side = [("밥 (사료)", "경험치 → 레벨업, 모든 능력치 소폭 상승"), ("포만감", "한 번에 먹일 수 있는 양 제한"),
            ("교배", "망아지가 부모 능력치 일부 계승"), ("치장", "재료로 제작, 외형만 변경")]
    y = 1.85
    for a, b in side:
        box(s, 8.85, y, 3.8, 1.05, fill=PANEL)
        text(s, 9.1, y, 3.4, 1.05, [[(a, {"font": F_XB, "color": GOLD, "size": 15})], [(b, {"size": 12})]], anchor=MSO_ANCHOR.MIDDLE)
        y += 1.2
    text(s, 1.0, 5.1, 7.5, 1.2, ["어떤 음식을 주느냐에 따라 속도형 · 지구력형 · 점프형으로",
                                 "같은 말도 다르게 키울 수 있다"], size=15, color=CREAM, spacing=1.35)
    text(s, 0.7, 6.65, 12, 0.4, "기수 성장 · 말 특성 · 기능 장비는 넣지 않아 레이싱에 집중", size=12, color=MUTED)
    notes(s, "육성은 먹이로 합니다. 밥을 먹이면 레벨이 올라 전체 능력치가 오르고, 과일은 속도, 채소는 지구력, 곡물은 순발력, 견과류는 점프력을 올립니다. 포만감으로 한 번에 먹일 수 있는 양을 제한합니다. RPG 요소가 레이싱을 흐리지 않도록 모든 성장이 레이스 성능으로만 이어지게 했습니다.")

    # 11. 성장 루프
    s = prs.slides.add_slide(BLANK); set_bg(s, image=os.path.join(ASSET, "bg_village.jpg"))
    title(s, "게임 전체 구조 — 성장 루프")
    nodes = [(6.67, 2.55, "필드", "파밍 · 퀘스트 · 수집품"), (9.9, 5.25, "마을", "먹이 · 치장 · 교배"), (3.43, 5.25, "레이스", "대회 · 상금")]
    for cx, cy, nm, sub in nodes:
        circle(s, cx, cy, 1.75, GOLD, nm, size=22)
        text(s, cx - 1.6, cy + 0.98, 3.2, 0.4, sub, size=13, font=F_SB, align=PP_ALIGN.CENTER)
    arrow(s, 7.55, 3.15, 9.05, 4.55); arrow(s, 9.0, 5.25, 4.35, 5.25); arrow(s, 4.25, 4.55, 5.8, 3.15)
    text(s, 8.55, 3.4, 2.5, 0.4, "재료 · 돈", size=12, color=CREAM)
    text(s, 5.6, 4.85, 2.2, 0.4, "강해진 말", size=12, color=CREAM, align=PP_ALIGN.CENTER)
    text(s, 2.25, 3.4, 2.5, 0.4, "상금 · 다시 탐험", size=12, color=CREAM, align=PP_ALIGN.RIGHT)
    notes(s, "정리하면 필드에서 재료와 돈을 모으고, 마을에서 말을 키우고 꾸미고, 강해진 말로 레이스에 나가 상금을 받아 다시 필드로 나가는 구조입니다.")

    # 12. 마무리
    s = prs.slides.add_slide(BLANK); set_bg(s, image=os.path.join(ASSET, "bg_trail.jpg"))
    text(s, 0.9, 1.0, 8, 0.5, "다음 단계", size=16, font=F_SB, color=GOLD)
    nxt = [("기승 조작 프로토타입", "구보 · 습보 · 리듬 손맛 검증"), ("콘텐츠 상세 설계", "마을 콘셉트 · 퀘스트 · 교배 규칙"), ("아트 방향 수립", "말 모델링 · 배경 퀄리티")]
    y = 1.65
    for i, (a, b) in enumerate(nxt):
        circle(s, 1.3, y + 0.42, 0.62, GOLD, str(i + 1), size=16)
        text(s, 1.85, y, 7, 0.85, [[(a, {"font": F_XB, "size": 20})], [(b, {"size": 13, "color": MUTED})]], anchor=MSO_ANCHOR.MIDDLE)
        y += 1.1
    text(s, 0.9, 5.4, 11, 1.0, "감사합니다", size=44, font=F_XB)
    notes(s, "앞으로는 기승 조작 프로토타입으로 손맛을 먼저 검증하고, 마을 콘셉트와 퀘스트 같은 콘텐츠를 상세 설계하고, 아트 방향을 세우겠습니다. 감사합니다.")

    prs.save(OUT)
    print("saved", OUT)


if __name__ == "__main__":
    import sys
    prep_assets(sys.argv[1])
    build()
