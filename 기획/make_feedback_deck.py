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


def tag(slide, label):
    s = box(slide, 10.55, 0.62, 2.1, 0.4, fill=None, line=GOLD, radius=0.5)
    shape_text(s, label, size=11, color=GOLD, font=F_SB)


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

    # 2. 피드백과 대응
    s = prs.slides.add_slide(BLANK); set_bg(s)
    title(s, "받은 피드백과 우리의 답")
    rows = [("말 레이싱 그 이상도 이하도 아니다", "기승 조작 시스템", "실제 승마 기술을 조작으로"),
            ("기수는 어떤 조작을 하는가?", "7가지 승마 조작", "고삐 · 다리 · 자세 · 보법 · 리듬 · 점프 · 채찍"),
            ("게임의 규모가 너무 작다", "오픈 필드", "마을 3곳 + 필드 + 퀘스트"),
            ("RPG가 미흡하다 · 적정선을 찾아라", "먹이 육성 시스템", "모든 성장은 레이스 성능으로")]
    y = 1.75
    for i, (fb, ans, sub) in enumerate(rows):
        b = box(s, 0.7, y, 5.2, 1.0, fill=PANEL)
        text(s, 0.95, y, 4.8, 1.0, [[(f"피드백  ", {"size": 11, "color": MUTED, "font": F_SB})], fb],
             size=16, font=F_SB, color=CREAM, anchor=MSO_ANCHOR.MIDDLE)
        arrow(s, 6.05, y + 0.5, 6.85, y + 0.5)
        b2 = box(s, 7.0, y, 5.65, 1.0, fill=PANEL2, line=GOLD)
        text(s, 7.3, y, 5.2, 1.0, [[(ans, {"size": 19, "font": F_XB, "color": GOLD})], [(sub, {"size": 13, "color": CREAM})]],
             anchor=MSO_ANCHOR.MIDDLE)
        y += 1.18
    text(s, 0.7, 6.6, 12, 0.4, "* 아트 관련 피드백(말 모델링 · 배경 퀄리티)은 추후 아트 방향 수립 시 반영 예정", size=12, color=MUTED)
    notes(s, "교수님께서 주신 피드백을 크게 네 가지로 정리했고, 각각 이렇게 답을 준비했습니다. 아트 관련 피드백은 이후 아트 방향을 세우면서 반영하겠습니다.")

    # 3. 핵심 콘셉트
    s = prs.slides.add_slide(BLANK); set_bg(s)
    photo(s, "2장 수정본.png", 7.2, 0, 6.133, 7.5)
    ov = box(s, 7.2, 0, 6.133, 7.5, fill=BG, shape=MSO_SHAPE.RECTANGLE, alpha=35)
    tag(s, "피드백 1 · 2 대응")
    text(s, 0.7, 0.9, 6, 0.4, "PART 1  기승 조작 시스템", size=14, font=F_SB, color=GOLD)
    text(s, 0.7, 1.6, 6.3, 2.2, ["말은 탈것이 아니라,", "신호를 주고받는", "파트너다"], size=40, font=F_XB, spacing=1.08)
    labels = [("입력", "플레이어의 신호"), ("말의 상태", "스태미나 · 능력치"), ("움직임", "속도 · 회전 · 점프")]
    x = 0.7
    for i, (a, b) in enumerate(labels):
        bx = box(s, x, 4.75, 1.85, 1.25, fill=PANEL2 if i != 1 else GOLD, line=None)
        col = CREAM if i != 1 else DARKTXT
        text(s, x, 4.75, 1.85, 1.25, [[(a, {"size": 18, "font": F_XB, "color": col})], [(b, {"size": 11, "color": col})]],
             align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
        if i < 2: arrow(s, x + 1.9, 5.375, x + 2.2, 5.375)
        x += 2.25
    text(s, 0.7, 6.3, 6.3, 0.5, "같은 조작이라도 말의 상태에 따라 결과가 달라진다", size=14, color=MUTED)
    notes(s, "실제 승마에서 기수는 말을 직접 움직이지 않고 고삐, 다리, 몸으로 신호를 보냅니다. 저희 게임의 조작도 이 구조를 따릅니다. 플레이어의 입력은 말에게 보내는 신호이고, 말은 스태미나와 능력치에 따라 반응합니다.")

    # 4. 7가지 승마 조작
    s = prs.slides.add_slide(BLANK); set_bg(s)
    title(s, "실제 승마 기술을 게임으로", "7가지 기승 조작")
    tag(s, "피드백 2 대응")
    items = [("고삐", "방향 전환 · 감속"), ("다리(박차)", "가속, 스태미나 소모"), ("자세", "코너링 · 최고 속도"),
             ("보법", "구보 / 습보 모드 전환"), ("리듬", "박자에 맞추면 효율 가속"), ("점프", "장애물 타이밍"),
             ("채찍", "레이스당 횟수 제한 순간 가속")]
    pos = [(0.7, 2.0), (3.75, 2.0), (6.8, 2.0), (9.85, 2.0), (2.22, 4.35), (5.27, 4.35), (8.32, 4.35)]
    for i, ((nm, ef), (x, y)) in enumerate(zip(items, pos)):
        hl = i in (3, 4)
        box(s, x, y, 2.8, 2.05, fill=PANEL2 if hl else PANEL, line=GOLD if hl else None)
        circle(s, x + 0.55, y + 0.55, 0.62, GOLD if hl else GREEN, str(i + 1), size=16)
        text(s, x + 0.3, y + 1.0, 2.3, 0.5, nm, size=20, font=F_XB, color=GOLD if hl else CREAM)
        text(s, x + 0.3, y + 1.5, 2.35, 0.5, ef, size=13, color=CREAM)
    text(s, 0.7, 6.65, 12, 0.4, "강조된 보법 · 리듬이 우리 게임만의 차별점", size=12, color=MUTED)
    notes(s, "실제 승마의 부조 기술을 일곱 가지 조작으로 옮겼습니다. 고삐, 다리, 자세, 보법, 리듬, 점프, 채찍입니다. 이 중 보법과 리듬이 일반 레이싱 게임과 가장 다른 부분입니다.")

    # 5. 보법 모드 + 리듬
    s = prs.slides.add_slide(BLANK); set_bg(s)
    title(s, "직선은 습보, 코너는 구보", "보법 모드와 리듬 — 우리 게임만의 차별점")
    tag(s, "피드백 1 대응")
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

    # 6. 조작 키
    s = prs.slides.add_slide(BLANK); set_bg(s)
    title(s, "왼손은 말을, 오른손은 기수의 몸을", "키보드 조작")
    tag(s, "피드백 2 · 3 대응")

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

    # 8. 월드 구조
    s = prs.slides.add_slide(BLANK); set_bg(s)
    tag(s, "피드백 4 대응")
    text(s, 0.7, 0.9 - 0.35, 6, 0.4, "PART 2  필드 · 육성", size=14, font=F_SB, color=GOLD)
    title_y = 1.0
    text(s, 0.7, title_y, 10, 0.8, "마을 3곳과 그 사이의 필드", size=34, font=F_XB)
    # 지도
    xs = [1.6, 4.55, 7.5]
    for i in range(2):
        c = s.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, Inches(xs[i] + 0.7), Inches(3.3), Inches(xs[i + 1] - 0.7), Inches(3.3))
        c.line.color.rgb = GREEN; c.line.width = Pt(3); c.line.dash_style = 4
        text(s, xs[i] + 0.75, 3.45, xs[i + 1] - xs[i] - 1.5, 0.4, "필드", size=13, font=F_SB, color=GREEN, align=PP_ALIGN.CENTER)
    for i, x in enumerate(xs):
        circle(s, x, 3.3, 1.35, GOLD, f"마을 {i + 1}", size=16)
    text(s, 0.7, 4.35, 8.2, 1.2, ["·  마을마다 다른 콘셉트(분위기)",
                                   "·  공통 시설: 마구간 · 대회장 · 상점 · 퀘스트 게시판"], size=15, spacing=1.4)
    # 레이스 vs 필드
    box(s, 9.3, 1.95, 3.35, 4.6, fill=PANEL)
    text(s, 9.6, 2.15, 2.9, 0.4, "레이스", size=18, font=F_XB, color=GOLD)
    text(s, 9.6, 2.6, 2.9, 1.2, ["긴장감 있는 승부", "7가지 기승 조작", "스태미나 · 리듬"], size=13, spacing=1.3)
    c = s.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, Inches(9.6), Inches(4.0), Inches(12.35), Inches(4.0))
    c.line.color.rgb = PANEL2; c.line.width = Pt(1.5)
    text(s, 9.6, 4.2, 2.9, 0.4, "필드", size=18, font=F_XB, color=GREEN)
    text(s, 9.6, 4.65, 2.9, 1.5, ["편안한 탐험", "이동 · 달리기 · 점프", "말에서 내리기 / 타기"], size=13, spacing=1.3)
    notes(s, "규모를 키우기 위해 오픈 필드를 추가했습니다. 콘셉트가 다른 마을 세 곳이 필드로 이어지고, 마을마다 마구간, 대회장, 상점, 퀘스트 게시판이 있습니다. 필드에서는 레이스와 달리 조작을 단순하게 해서 편하게 돌아다니는 탐험 공간으로 구분했습니다.")

    # 9. 필드에서 하는 일
    s = prs.slides.add_slide(BLANK); set_bg(s)
    title(s, "필드에서 하는 일")
    tag(s, "피드백 4 · 5 대응")
    cards = [("5장.png", "파밍", ["먹이: 과일 · 채소 · 곡물 · 견과류", "치장 재료: 꽃 · 깃털 · 염료 · 가죽"]),
             ("9장.png", "점프 코스 · 수집품", ["필드 곳곳의 점프 코스", "숨겨진 말굽 문양 수집품"]),
             ("11장.png", "마을 퀘스트", ["마을에서 여러 퀘스트 수주", "보상: 돈 · 재료 · 아이템"])]
    x = 0.7
    for img, nm, pts in cards:
        box(s, x, 1.75, 3.85, 4.2, fill=PANEL)
        photo(s, img, x, 1.75, 3.85, 2.25)
        text(s, x + 0.3, 4.2, 3.3, 0.5, nm, size=21, font=F_XB, color=GOLD)
        text(s, x + 0.3, 4.8, 3.35, 1.6, ["·  " + p for p in pts], size=13.5, spacing=1.4)
        x += 4.05
    notes(s, "필드에서는 세 가지를 합니다. 먹이와 치장 재료를 채집하고, 점프 코스를 넘어 숨겨진 수집품을 찾고, 마을에서 받은 퀘스트를 수행해 보상을 얻습니다.")

    # 10. 먹이 육성
    s = prs.slides.add_slide(BLANK); set_bg(s)
    title(s, "먹이로 키우는 육성", "모든 성장은 레이스 성능으로 이어진다")
    tag(s, "피드백 5 · 6 대응")
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
