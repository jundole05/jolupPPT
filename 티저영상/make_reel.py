# -*- coding: utf-8 -*-
"""승마 레이싱 & 육성 RPG — 게임 소개 릴 (PlantNet 릴 스타일) + BGM.
python make_reel.py                 전체 렌더
python make_reel.py preview DIR t1,t2,...   미리보기 PNG
"""
import math, os, random, subprocess, sys, wave
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
import imageio_ffmpeg
import make_teaser45 as T

HERE = T.HERE
W, H, FPS = T.W, T.H, T.FPS
BEAT = T.BEAT
TR = 0.4
AMB = (255, 196, 90)
CREAM = (255, 246, 228)
DARK_BG = (14, 18, 16)

PF = T.PF


def font(w, sz): return T.font(w, sz)


eo, eio, ex, with_alpha = T.eo, T.eio, T.ex, T.with_alpha


def eback(x, s=1.7):
    x = min(1, max(0, x)) - 1; return x * x * ((s + 1) * x + s) + 1


# ------------------------------------------------------------------ 글자 단위 텍스트
class TLine:
    P = 26

    def __init__(self, text, weight, size, color, x, y, align="left", track=0, shadow=0.75, seed=0):
        f = font(weight, size)
        ws = [f.getlength(c) for c in text]
        tw = sum(ws) + track * (len(text) - 1)
        asc, dsc = f.getmetrics()
        self.h = asc + dsc
        x0 = x if align == "left" else x - tw if align == "right" else x - tw / 2
        self.x0, self.y, self.w = x0, y, tw
        rng = random.Random(seed + hash(text) % 1000)
        self.chars, xx, word = [], x0, 0
        P = self.P
        for c, w in zip(text, ws):
            if c == " ":
                word += 1; xx += w + track; continue
            lay = Image.new("RGBA", (int(w) + P * 2 + 6, self.h + P * 2), (0, 0, 0, 0))
            ImageDraw.Draw(lay).text((P, P), c, font=f, fill=color + (255,))
            sh = None
            if shadow:
                sh = Image.new("RGBA", lay.size, (0, 0, 0, 0))
                sh.putalpha(lay.getchannel("A").filter(ImageFilter.GaussianBlur(max(3, size / 14)))
                            .point(lambda v, s=shadow: int(min(255, v * 1.4) * s)))
            self.chars.append(dict(lay=lay, blur=lay.filter(ImageFilter.GaussianBlur(max(4, size / 14))), sh=sh,
                                   x=xx - P, y=y - P, w=w, word=word, sx=rng.uniform(-1, 1), sy=rng.uniform(-1, .5),
                                   sd=rng.uniform(0, .12)))
            xx += w + track
        self.end_x = xx
        self.nwords = word + 1

    def bbox(self):
        return (self.x0, self.y, self.x0 + self.w, self.y + self.h)

    def dur_in(self, mode, step):
        n = len(self.chars)
        if mode == "fade": return 0.4
        if mode == "word": return self.nwords * step + 0.3
        return n * step + 0.3

    def draw(self, fr, t, mode="char", step=0.03, t_exit=99.0, ox=0, oy=0, scale_pop=False):
        if t < 0: return
        last = None
        for k, c in enumerate(self.chars):
            if mode == "fade": ta = 0
            elif mode == "word": ta = c["word"] * step
            else: ta = k * step
            lt = t - ta
            if lt < 0: continue
            if mode == "type":
                a, dy, bl, sc = 1.0, 0, 0, 1
            elif mode == "fade":
                a = eo(lt / 0.45); dy = 14 * (1 - a); bl = 0; sc = 1
            else:
                a = eo(lt / 0.32); dy = 24 * (1 - a); bl = 1 - a
                sc = 1 + 0.5 * (1 - eback(lt / 0.35)) if scale_pop else 1
            dx = 0
            e = eo((t - t_exit - c["sd"]) / 0.35) if t > t_exit else 0
            if e > 0:
                a *= 1 - e; dx = c["sx"] * 70 * e; dy += c["sy"] * 45 * e; bl = max(bl, e)
            if a < 0.01: continue
            last = c
            px, py = c["x"] + dx + ox, c["y"] + dy + oy
            layers = []
            if c["sh"] is not None: layers.append((c["sh"], a * (1 - bl * 0.6), 6))
            if bl > 0.02: layers.append((c["blur"], a * bl, 0))
            if bl < 0.98: layers.append((c["lay"], a * (1 - bl), 0))
            for lay, al, off in layers:
                if abs(sc - 1) > 0.01:
                    lay = lay.resize((int(lay.width * sc), int(lay.height * sc)), Image.BILINEAR)
                    qx, qy = px - (lay.width - c["lay"].width) / 2, py - (lay.height - c["lay"].height) / 2
                else:
                    qx, qy = px, py
                fr.alpha_composite(with_alpha(lay, al), (int(qx), int(qy + off)))
        return last


def fade_alpha(t, t_in, t_out, d_in=0.35, d_out=0.3):
    return eo((t - t_in) / d_in) * (1 - eo((t - t_out) / d_out))


# ------------------------------------------------------------------ UI 요소
class Headline:
    """[영문 태그] / 굵은 제목 / 설명. 위치·정렬 자유"""

    def __init__(self, x, y, align, tag, title, desc=None, size=112, mode="char", seed=0):
        self.mode = mode
        self.tag = TLine(tag, "SemiBold", 26, AMB, x, y, align, track=7, shadow=0.6, seed=seed) if tag else None
        ty = y + (42 if tag else 0)
        lines = title.split("\n")
        self.titles = []
        for i, l in enumerate(lines):
            self.titles.append(TLine(l, "ExtraBold", size, (255, 255, 255), x, ty, align, track=-2, seed=seed + i))
            ty += int(size * 1.12)
        self.desc = TLine(desc, "Regular", 32, (240, 240, 240), x, ty + 14, align, shadow=0.8, seed=seed) if desc else None
        xs, ys = [], []
        for l in [self.tag, self.desc] + self.titles:
            if l: b = l.bbox(); xs += [b[0], b[2]]; ys += [b[1], b[3]]
        self.bbox = (min(xs), min(ys), max(xs), max(ys))

    def draw(self, fr, t, t_exit):
        if self.tag: self.tag.draw(fr, t, "fade", t_exit=t_exit)
        tt = t - 0.15
        step = 0.035 if self.mode == "char" else 0.12
        for l in self.titles:
            l.draw(fr, tt, self.mode, step, t_exit=t_exit - (t - tt))
            tt -= l.dur_in(self.mode, step) - 0.25
        if self.desc:
            self.desc.draw(fr, t - 0.6, "fade", t_exit=t_exit - 0.6)


def pill(text, size=28, fg=(28, 28, 32), bg=(255, 255, 255)):
    f = font("SemiBold", size)
    tw = f.getlength(text)
    h = int(size * 1.9); w = int(tw + size * 1.6)
    img = Image.new("RGBA", (w + 40, h + 40), (0, 0, 0, 0))
    sh = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle((20, 26, 20 + w, 26 + h), h / 2, fill=(0, 0, 0, 90))
    img.alpha_composite(sh.filter(ImageFilter.GaussianBlur(8)))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((20, 20, 20 + w, 20 + h), h / 2, fill=bg + (255,))
    d.text((20 + w / 2, 20 + h / 2), text, font=f, fill=fg + (255,), anchor="mm")
    return img


def draw_pop(fr, lay, cx, cy, t, t_exit=99):
    if t < 0: return
    a = min(1, t / 0.12) * (1 - eo((t - t_exit) / 0.25))
    if a < 0.01: return
    sc = eback(t / 0.35)
    l = lay.resize((max(1, int(lay.width * sc)), max(1, int(lay.height * sc))), Image.BILINEAR)
    fr.alpha_composite(with_alpha(l, a), (int(cx - l.width / 2), int(cy - l.height / 2)))


def callout(fr, tx, ty, label, t, t_exit=99, side=1):
    """대상 점 → 사선 → 수평선 → 라벨"""
    if t < 0: return
    fa = 1 - eo((t - t_exit) / 0.25)
    if fa < 0.01: return
    d = ImageDraw.Draw(fr)
    p1 = eo(t / 0.25); p2 = eo((t - 0.2) / 0.3)
    r = 9 * eback(min(1, t / 0.25))
    col = (255, 255, 255, int(255 * fa))
    d.ellipse((tx - r - 6, ty - r - 6, tx + r + 6, ty + r + 6), outline=(255, 255, 255, int(120 * fa)), width=2)
    d.ellipse((tx - r * 0.55, ty - r * 0.55, tx + r * 0.55, ty + r * 0.55), fill=col)
    mx, my = tx + side * 70 * p1, ty - 70 * p1
    d.line((tx, ty, mx, my), fill=col, width=3)
    if p2 > 0:
        ex_ = mx + side * 90 * p2
        d.line((mx, my, ex_, my), fill=col, width=3)
        if p2 > 0.6:
            lay = pill(label, 26, fg=(255, 255, 255), bg=(25, 28, 30))
            la = eo((t - 0.45) / 0.25) * fa
            lx = ex_ + (8 if side > 0 else -lay.width - 8)
            fr.alpha_composite(with_alpha(lay, la), (int(lx - (20 if side > 0 else -20)), int(my - lay.height / 2)))


_tagbg = None


def chapter_tag(fr, no, en, ko, t):
    global _tagbg
    if t < 0: return
    if _tagbg is None:
        g = np.clip(1 - np.sqrt(((T.XX - 60) / 700) ** 2 + ((T.YY - 40) / 170) ** 2), 0, 1) ** 1.2 * 0.6
        arr = np.zeros((H, W, 4), np.uint8); arr[..., 3] = (g * 255).astype(np.uint8)
        _tagbg = Image.fromarray(arr, "RGBA").crop((0, 0, 900, 260))
    fr.alpha_composite(with_alpha(_tagbg, eo(t / 0.4)) if t < 0.4 else _tagbg, (0, 0))
    d = ImageDraw.Draw(fr)
    lw = int(46 * ex(t / 0.5))
    d.rectangle((60, 58, 60 + lw, 60), fill=AMB + (230,))
    a = eo((t - 0.15) / 0.4)
    f1, f2, f3 = font("Bold", 24), font("Bold", 24), font("Regular", 22)
    x = 120
    col = lambda c: c + (int(255 * a),)
    d.text((x, 59), no, font=f1, fill=col(AMB), anchor="lm"); x += f1.getlength(no) + 14
    for ch in en:
        d.text((x, 59), ch, font=f2, fill=col((255, 255, 255)), anchor="lm"); x += f2.getlength(ch) + 4
    x += 12
    d.text((x, 60), ko, font=f3, fill=col((230, 230, 230)), anchor="lm")


def big_word(word, size=230, seed=0):
    return TLine(word, "ExtraBold", size, (255, 255, 255), W / 2, H / 2 - size * 0.62, "center", track=-4, seed=seed)


def info_card(en, ko, rows, badge=None, w=560):
    f_en, f_ko, f_r, f_v = font("SemiBold", 24), font("ExtraBold", 80), font("Regular", 28), font("Bold", 30)
    h = 190 + 56 * len(rows) + 30
    img = Image.new("RGBA", (w + 60, h + 60), (0, 0, 0, 0))
    sh = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle((30, 40, 30 + w, 40 + h), 26, fill=(0, 0, 0, 120))
    img.alpha_composite(sh.filter(ImageFilter.GaussianBlur(16)))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((30, 30, 30 + w, 30 + h), 26, fill=(18, 20, 24, 225), outline=(255, 255, 255, 30), width=2)
    x = 30 + 44
    xx = x
    for ch in en:
        d.text((xx, 30 + 50), ch, font=f_en, fill=AMB + (255,), anchor="lm"); xx += f_en.getlength(ch) + 6
    d.text((x, 30 + 78), ko, font=f_ko, fill=(255, 255, 255, 255))
    if badge:
        bl = pill(badge, 22, fg=(25, 20, 10), bg=AMB)
        img.alpha_composite(bl, (int(30 + w - bl.width - 6), 30 + 24))
    y = 30 + 200
    d.line((x, y - 18, 30 + w - 44, y - 18), fill=(255, 255, 255, 40), width=1)
    for k, v in rows:
        d.text((x, y + 14), k, font=f_r, fill=(170, 170, 176, 255), anchor="lm")
        d.text((x + 150, y + 14), v, font=f_v, fill=(255, 255, 255, 255), anchor="lm")
        y += 56
    return img


def draw_card(fr, card, x, y, t, t_exit=99):
    if t < 0: return
    a = eo(t / 0.35) * (1 - eo((t - t_exit) / 0.3))
    if a < 0.01: return
    off = -80 * (1 - eo(t / 0.4)) + (-60 * eo((t - t_exit) / 0.3) if t > t_exit else 0)
    c = card
    if t < 0.25: c = card.filter(ImageFilter.GaussianBlur(10 * (1 - t / 0.25)))
    fr.alpha_composite(with_alpha(c, a), (int(x + off), int(y)))


def rings(fr, cx, cy, t, n=6, gap=70, base=90, col=(120, 200, 140), alpha=110, squash=1.0, width=3):
    d = ImageDraw.Draw(fr)
    for k in range(n):
        p = ex((t - k * 0.12) / 0.9)
        if p <= 0: continue
        r = base + k * gap
        ang = 360 * p
        box = (cx - r, cy - r * squash, cx + r, cy + r * squash)
        a = int(alpha * (1 - k / (n + 2)))
        d.arc(box, -90, -90 + ang, fill=col + (a,), width=width)


def particles(fr, t, n=60, seed=3, col=(255, 220, 140), strength=1.0):
    r = random.Random(seed)
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    for _ in range(n):
        x, y, s, sp, ph = r.uniform(0, W), r.uniform(0, H), r.uniform(1.5, 4.5), r.uniform(15, 50), r.uniform(0, 6.3)
        yy = (y - t * sp) % H; xx = x + math.sin(t + ph) * 25
        al = int(200 * strength * (0.5 + 0.5 * math.sin(t * 2.5 + ph)))
        d.ellipse((xx - s, yy - s, xx + s, yy + s), fill=col + (max(0, al),))
    fr.alpha_composite(lay.filter(ImageFilter.GaussianBlur(1.2)))


def gold_text(text, size, weight="ExtraBold", stroke=8):
    f = font(weight, size)
    tw = f.getlength(text); asc, dsc = f.getmetrics(); P = 50
    w, h = int(tw + P * 2), asc + dsc + P * 2
    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask).text((P, P), text, font=f, fill=255)
    stroke_m = Image.new("L", (w, h), 0)
    ImageDraw.Draw(stroke_m).text((P, P), text, font=f, fill=255, stroke_width=stroke, stroke_fill=255)
    grad = np.zeros((h, w, 3), np.float32)
    yy = np.linspace(0, 1, h)[:, None]
    top, bot = np.array([255, 244, 200]), np.array([222, 150, 40])
    k = np.clip((yy - 0.3) / 0.5, 0, 1)
    col = top[None, :] * (1 - k) + bot[None, :] * k  # (h,3)
    grad = np.ascontiguousarray(np.broadcast_to(col[:, None, :], (h, w, 3)))
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    shadow = Image.new("RGBA", (w, h), (0, 0, 0, 0)); shadow.putalpha(stroke_m.filter(ImageFilter.GaussianBlur(10)).point(lambda v: int(v * .7)))
    img.alpha_composite(shadow, (0, 0))
    img.paste(Image.new("RGBA", (w, h), (60, 32, 8, 255)), (0, 0), stroke_m)
    img.paste(Image.fromarray(grad.astype(np.uint8), "RGB").convert("RGBA"), (0, 0), mask)
    return img


# ------------------------------------------------------------------ 배경
def photo(name, p, pan=(1, 0), zoom=(1.03, 1.10), shake=(0, 0)):
    return T.camera(T.graded(name), zoom[0] + (zoom[1] - zoom[0]) * p,
                    pan[0] * (p - 0.5) * 0.8 + shake[0], pan[1] * (p - 0.5) * 0.8 + shake[1])


_scrims = {}


def scrim(key, bbox, s=0.6):
    if key not in _scrims: _scrims[key] = T.scrim_for(tuple(int(v) for v in bbox), s)
    return _scrims[key]


_vig = None


def vignette():
    global _vig
    if _vig is None: _vig = T.scrim_for((W // 2 - 1, H // 2 - 1, W // 2 + 1, H // 2 + 1), 0.0)
    return _vig


def dark_bg(t, tint=(18, 30, 22)):
    arr = np.zeros((H, W, 3), np.float32)
    d = T.DIST_C / (math.hypot(W, H) / 2)
    c = np.array(tint, np.float32)
    arr[:] = (c[None, None, :] * (1.25 - d[..., None] * 0.9)).clip(0, 255)
    return Image.fromarray(arr.astype(np.uint8), "RGB").convert("RGBA")


_dark_cache = {}


def dark(tint=(18, 30, 22)):
    if tint not in _dark_cache: _dark_cache[tint] = dark_bg(0, tint)
    return _dark_cache[tint].copy()


# ------------------------------------------------------------------ 장면 정의
class Scene:
    def __init__(self, dur, draw, tr="flash", chapter=None):
        self.dur, self.draw, self.tr, self.chapter = dur, draw, tr, chapter


def build():
    S = []
    # 0. 오프닝: 어두운 배경 + 트랙 링
    l1 = TLine("이름 없는", "Light", 40, (200, 215, 205), W / 2, H / 2 - 120, "center", track=4, shadow=0)
    l2 = TLine("말 한 마리", "ExtraBold", 96, (255, 255, 255), W / 2, H / 2 - 70, "center", track=-2)
    l3 = TLine("언젠가는", "Light", 40, (200, 215, 205), W / 2, H / 2 - 150, "center", track=4, shadow=0)
    l4 = TLine("1위", "ExtraBold", 200, (255, 255, 255), W / 2, H / 2 - 120, "center", track=-4)

    def s0(t, d):
        fr = dark()
        particles(fr, t, 40, 1, (140, 230, 160), 0.5)
        rings(fr, W / 2, H / 2 + 10, t - 0.1, n=6, gap=80, base=130, col=(110, 200, 130), alpha=120, squash=0.62)
        l1.draw(fr, t - 0.3, "fade", t_exit=2.3)
        l2.draw(fr, t - 0.6, "char", 0.06, t_exit=2.3 - 0.3)
        if t > 2.6:
            rings(fr, W / 2, H / 2 + 10, t - 2.6, n=3, gap=60, base=210, col=AMB, alpha=200, squash=0.62, width=4)
        l3.draw(fr, t - 2.7, "fade", t_exit=d - 0.45 - 2.7)
        l4.draw(fr, t - 2.95, "char", 0.09, t_exit=d - 0.45 - 2.95, scale_pop=True)
        return fr
    S.append(Scene(10 * BEAT, s0))

    # 1. 타이틀 카드
    title = gold_text("승마 레이싱 & 육성 RPG", 132)
    sub = TLine("내 말을 키우고 직접 달리는 승마 게임", "SemiBold", 34, (255, 255, 255), W / 2, H / 2 + 110, "center", track=6, shadow=0.7)
    bg1 = T.graded("1장 수정본.png").resize((W, H), Image.LANCZOS).filter(ImageFilter.GaussianBlur(10)).convert("RGBA")
    bg1 = Image.blend(bg1, Image.new("RGBA", (W, H), (255, 240, 210, 255)), 0.25)

    def s1(t, d):
        fr = T.camera(bg1, 1.02 + 0.04 * t / d, 0, 0)
        lk = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        r = int(300 + 900 * ex(t / 1.2))
        ImageDraw.Draw(lk).ellipse((W / 2 - r, H / 2 - r * 0.7 - 40, W / 2 + r, H / 2 + r * 0.7 - 40), outline=(255, 255, 240, int(160 * (1 - ex(t / 1.2)))), width=6)
        fr.alpha_composite(lk.filter(ImageFilter.GaussianBlur(4)))
        particles(fr, t, 70, 9, (255, 225, 150), 1.0)
        sc = 1.25 - 0.25 * eback(t / 0.55) if t > 0 else 0
        if t > 0:
            a = min(1, t / 0.15)
            ttl = title.resize((int(title.width * sc), int(title.height * sc)), Image.BICUBIC)
            fr.alpha_composite(with_alpha(ttl, a), (int(W / 2 - ttl.width / 2), int(H / 2 - 30 - ttl.height / 2)))
        dd = ImageDraw.Draw(fr)
        lw = int(150 * ex((t - 0.7) / 0.6))
        sw = sub.w / 2 + 40
        if lw > 0:
            for sg in (-1, 1):
                x0 = W / 2 + sg * sw
                dd.rectangle((min(x0, x0 + sg * lw), H / 2 + 132, max(x0, x0 + sg * lw), H / 2 + 134), fill=(255, 255, 255, 220))
        sub.draw(fr, t - 0.7, "fade")
        return fr
    S.append(Scene(8 * BEAT, s1, "circle"))

    # ---- 01 RACE
    h2 = Headline(W - 150, 330, "right", "RIDE", "직접 달린다", "직접 키운 말로 경마 레이싱", seed=2)

    def s2(t, d):
        fr = photo("2장 수정본.png", t / d, (1, -0.3)); fr.alpha_composite(scrim("s2", h2.bbox))
        chapter_tag(fr, "01", "RACE", "레이싱", t - 0.2)
        h2.draw(fr, t - 0.35, d - 0.75)
        callout(fr, 960, 470, "말순이 · Lv.1", t - 1.0, d - 0.6, side=-1)
        return fr
    S.append(Scene(7 * BEAT, s2, "flash", "01"))

    h3 = Headline(150, 360, "left", "MULTIPLAYER", "옆집 말과\n한판 승부", "다인 실시간 대전 · 몸싸움 변수", size=104, mode="word", seed=3)

    def s3(t, d):
        fr = photo("3장.png", t / d, (-1, 0.2)); fr.alpha_composite(scrim("s3", h3.bbox))
        chapter_tag(fr, "01", "RACE", "레이싱", 99)
        h3.draw(fr, t - 0.3, d - 0.75)
        callout(fr, 1310, 400, "라이벌", t - 0.9, d - 0.6, side=1)
        return fr
    S.append(Scene(7 * BEAT, s3, "whip", "01"))

    # ---- 02 OBSTACLE
    bw = big_word("넘어지고", 220, 4)

    def s4(t, d):
        sh = (0, 0)
        if 0.2 < t < 0.9:
            k = (0.9 - t) / 0.7; r = random.Random(int(t * 999)); sh = (r.uniform(-1, 1) * .05 * k, r.uniform(-1, 1) * .05 * k)
        fr = photo("4장.png", t / d, (0, 1), shake=sh)
        fr.alpha_composite(scrim("s4", (W / 2 - 400, H / 2 - 150, W / 2 + 400, H / 2 + 150), 0.55))
        chapter_tag(fr, "02", "OBSTACLE", "장애물", t - 0.1)
        bw.draw(fr, t - 0.25, "char", 0.06, t_exit=d - 0.65, scale_pop=True)
        dd = ImageDraw.Draw(fr)
        lw = int(bw.w * 0.55 * ex((t - 0.6) / 0.5) * (1 - eo((t - (d - 0.45)) / 0.25)))
        if lw > 2:
            dd.rectangle((W / 2 - lw / 2, H / 2 + 115, W / 2 + lw / 2, H / 2 + 121), fill=AMB + (255,))
        return fr
    S.append(Scene(6 * BEAT, s4, "zoom", "02"))

    h5 = Headline(W - 150, 300, "right", "TIMING", "다시 도전", "타이밍을 읽고 직접 넘어라", seed=5)
    p5a, p5b = pill("특색있는 장애물"), pill("다양한 코스")

    def s5(t, d):
        fr = photo("9장.png", t / d, (0, 1)); fr.alpha_composite(scrim("s5", h5.bbox, 0.7))
        chapter_tag(fr, "02", "OBSTACLE", "장애물", 99)
        h5.draw(fr, t - 0.3, d - 0.75)
        draw_pop(fr, p5a, W - 150 - p5b.width - p5a.width / 2 + 10, 640, t - 1.0, d - 0.55 - 1.0)
        draw_pop(fr, p5b, W - 150 - p5b.width / 2 + 20, 640, t - 1.12, d - 0.55 - 1.12)
        callout(fr, 1020, 620, "점프 타이밍", t - 1.3, d - 0.6, side=-1)
        return fr
    S.append(Scene(7 * BEAT, s5, "whipL", "02"))

    # ---- 03 VILLAGE
    h6 = Headline(150, 250, "left", "CARE", "마을에서\n돌보고", None, size=104, mode="word", seed=6)
    pills6 = [pill(s) for s in ("밥먹이기", "상호작용", "커뮤니티")]

    def s6(t, d):
        fr = photo("5장.png", t / d, (-1, 0)); fr.alpha_composite(scrim("s6", (150, 250, 700, 620), 0.65))
        chapter_tag(fr, "03", "VILLAGE", "마을 & 육성", t - 0.1)
        h6.draw(fr, t - 0.3, d - 0.75)
        x = 150
        for k, pl in enumerate(pills6):
            draw_pop(fr, pl, x + pl.width / 2 - 20, 560, t - 1.0 - k * 0.15, d - 0.55 - 1.0 - k * 0.15)
            x += pl.width - 28
        return fr
    S.append(Scene(7 * BEAT, s6, "wipe", "03"))

    h7 = Headline(150, 330, "left", "LEVEL UP", "능력치 성장", "선택에 따라 달라지는 육성", seed=7)

    def s7(t, d):
        fr = photo("6장.png", t / d, (1, 0)); fr.alpha_composite(scrim("s7", h7.bbox, 0.7))
        chapter_tag(fr, "03", "VILLAGE", "마을 & 육성", 99)
        h7.draw(fr, t - 0.3, d - 0.75)
        callout(fr, 1690, 520, "능력치 상승", t - 1.0, d - 0.6, side=-1)
        return fr
    S.append(Scene(7 * BEAT, s7, "whip", "03"))

    # ---- 04 STYLE
    h8 = Headline(W / 2, 700, "center", "CUSTOMIZE", "나만의 스타일", None, size=108, seed=8)
    pills8 = [pill(s) for s in ("갈기", "색상", "안장", "액세서리")]

    def s8(t, d):
        fr = photo("7장.png", t / d, (0, -1), zoom=(1.02, 1.06))
        fr.alpha_composite(scrim("s8", (W / 2 - 400, 700, W / 2 + 400, 900), 0.8))
        chapter_tag(fr, "04", "STYLE", "치장 & 교배", t - 0.1)
        h8.draw(fr, t - 0.3, d - 0.75)
        tot = sum(p.width - 28 for p in pills8)
        x = W / 2 - tot / 2
        for k, pl in enumerate(pills8):
            draw_pop(fr, pl, x + pl.width / 2 - 14, 900, t - 0.95 - k * 0.12, d - 0.55 - 0.95 - k * 0.12)
            x += pl.width - 28
        callout(fr, 1500, 330, "선글라스 장착", t - 1.3, d - 0.6, side=1)
        return fr
    S.append(Scene(7 * BEAT, s8, "circle", "04"))

    card9 = info_card("FOAL", "망아지", [("엄마", "말순이"), ("아빠", "옆집 말"), ("특징", "능력치 계승")], badge="NEW")

    def s9(t, d):
        fr = photo("8장.png", t / d, (-1, 0)); fr.alpha_composite(scrim("s9", (120, 300, 700, 800), 0.6))
        chapter_tag(fr, "04", "STYLE", "치장 & 교배", 99)
        draw_card(fr, card9, 110, 300, t - 0.3, d - 0.65)
        callout(fr, 1040, 600, "새 가족", t - 1.1, d - 0.6, side=1)
        return fr
    S.append(Scene(8 * BEAT, s9, "flash", "04"))

    # ---- 05 MODES (카드 3장 순차)
    cards10 = [info_card("SOLO", "솔로 모드", [("상대", "없음"), ("목표", "코스 숙달")]),
               info_card("VS AI", "AI 모드", [("상대", "컴퓨터"), ("목표", "몸싸움 연습")]),
               info_card("PVP", "PVP 모드", [("상대", "플레이어"), ("목표", "실전 레이싱")], badge="HOT")]
    cnt = [TLine(f"0{k + 1} / 03", "SemiBold", 26, (230, 230, 230), W - 120, H - 110, "right", track=3, shadow=0.6) for k in range(3)]

    def s10(t, d):
        fr = photo("10장.png", t / d, (1, 0), zoom=(1.02, 1.06)); fr.alpha_composite(scrim("s10", (100, 300, 700, 760), 0.7))
        chapter_tag(fr, "05", "MODES", "플레이 방식", t - 0.1)
        seg = (d - 0.3) / 3
        for k in range(3):
            st = 0.3 + k * seg
            te = st + seg - 0.3 if k < 2 else d - 0.65
            if st - 0.05 <= t <= te + 0.35:
                draw_card(fr, cards10[k], 110, 330, t - st, te - st)
                cnt[k].draw(fr, t - st, "fade", t_exit=te - st)
        return fr
    S.append(Scene(12 * BEAT, s10, "wipe", "05"))

    # ---- 06 REWARD
    h11 = Headline(W - 150, 300, "right", "REWARD", "우승하면\n보상", None, size=104, mode="word", seed=11)
    pills11 = [pill(s) for s in ("육성", "치장", "다시 레이싱")]

    def s11(t, d):
        fr = photo("11장.png", t / d, (-1, 0)); fr.alpha_composite(scrim("s11", (1100, 300, W - 150, 660), 0.7))
        chapter_tag(fr, "06", "REWARD", "순위 보상", t - 0.1)
        h11.draw(fr, t - 0.3, d - 0.75)
        tot = sum(p.width - 28 for p in pills11)
        x = W - 150 - tot + 14
        for k, pl in enumerate(pills11):
            draw_pop(fr, pl, x + pl.width / 2 - 14, 610, t - 1.0 - k * 0.14, d - 0.55 - 1.0 - k * 0.14)
            x += pl.width - 28
        return fr
    S.append(Scene(7 * BEAT, s11, "zoom", "06"))

    # ---- 07 LOOP 다이어그램 (어두운 배경)
    orbit = ["레이싱", "보상", "육성", "치장", "교배", "재도전"]
    orbit_p = [pill(s, 26, fg=(30, 26, 18), bg=(255, 240, 210)) for s in orbit]
    head12 = TLine("달리고, 키우고, 다시 달린다", "Bold", 52, (255, 255, 255), W / 2, 120, "center", seed=12)
    core = TLine("성장", "ExtraBold", 120, AMB, W / 2, H / 2 - 95, "center", seed=13)
    core_s = TLine("내 말과 함께", "Light", 32, (225, 225, 225), W / 2, H / 2 + 50, "center", shadow=0)

    def s12(t, d):
        fr = dark((30, 24, 16))
        particles(fr, t, 50, 5, (255, 210, 130), 0.6)
        chapter_tag(fr, "07", "LOOP", "성장 루프", t - 0.1)
        cy = H / 2 + 20
        rings(fr, W / 2, cy, t - 0.1, n=4, gap=95, base=170, col=(255, 200, 110), alpha=150, width=3)
        # 진행 링
        dd = ImageDraw.Draw(fr)
        pr = ex((t - 0.4) / (d - 1.2))
        dd.arc((W / 2 - 150, cy - 150, W / 2 + 150, cy + 150), -90, -90 + 360 * pr, fill=AMB + (255,), width=10)
        head12.draw(fr, t - 0.2, "word", 0.12, t_exit=d - 0.7)
        core.draw(fr, t - 0.5, "char", 0.12, t_exit=d - 0.7 - 0.5, scale_pop=True)
        core_s.draw(fr, t - 0.9, "fade", t_exit=d - 0.7 - 0.9)
        R = 360
        for k, pl in enumerate(orbit_p):
            ang = -math.pi / 2 + k * 2 * math.pi / len(orbit_p) + t * 0.25
            draw_pop(fr, pl, W / 2 + math.cos(ang) * R * 1.25, cy + math.sin(ang) * R * 0.78, t - 0.8 - k * 0.12, d - 0.7 - 0.8 - k * 0.12)
        return fr
    S.append(Scene(10 * BEAT, s12, "white", "07"))

    # ---- 성공 배너
    def banner_img():
        w, h = 980, 190
        img = Image.new("RGBA", (w + 80, h + 80), (0, 0, 0, 0))
        sh = Image.new("RGBA", img.size, (0, 0, 0, 0))
        ImageDraw.Draw(sh).rounded_rectangle((40, 54, 40 + w, 54 + h), 40, fill=(0, 0, 0, 140))
        img.alpha_composite(sh.filter(ImageFilter.GaussianBlur(14)))
        d = ImageDraw.Draw(img)
        d.rounded_rectangle((40, 40, 40 + w, 40 + h), 40, fill=(70, 40, 18, 255), outline=(240, 190, 90, 255), width=8)
        d.rounded_rectangle((58, 58, 22 + w, 22 + h), 30, outline=(255, 220, 140, 120), width=2)
        g = gold_text("나만의 말 완성", 104, stroke=5)
        img.alpha_composite(g, (int(40 + w / 2 - g.width / 2), int(40 + h / 2 - g.height / 2)))
        return img
    ban = banner_img()
    sub13 = TLine("Lv.1  →  Lv.MAX", "Bold", 40, (255, 255, 255), W / 2, H / 2 + 120, "center", track=3)

    def s13(t, d):
        fr = photo("12장.png", t / d, (0, -1)); fr.alpha_composite(scrim("s13", (W / 2 - 500, H / 2 - 150, W / 2 + 500, H / 2 + 200), 0.55))
        # 방사형 빛
        if t > 0.2:
            rays = Image.new("RGBA", (W // 4, H // 4), (0, 0, 0, 0))
            rd = ImageDraw.Draw(rays)
            for k in range(16):
                a0 = k * 22.5 + t * 12
                rd.pieslice((-W // 4, -H // 4, W // 2, H // 2), a0, a0 + 9, fill=(255, 230, 160, int(50 * eo((t - 0.2) / 0.5))))
            fr.alpha_composite(rays.resize((W, H), Image.BILINEAR).filter(ImageFilter.GaussianBlur(8)))
        particles(fr, t, 80, 11, (255, 225, 150), 1.0)
        draw_pop(fr, ban, W / 2, H / 2 - 20, t - 0.25, d - 0.6)
        sub13.draw(fr, t - 0.8, "fade", t_exit=d - 0.6 - 0.8)
        return fr
    S.append(Scene(8 * BEAT, s13, "circle"))

    # ---- 엔딩: 모니터 목업
    title_e = gold_text("승마 레이싱 & 육성 RPG", 84, stroke=6)
    tag_e = TLine("처음엔 그냥 말이었는데, 이제는 나만의 말", "Bold", 40, (255, 255, 255), W / 2, H - 250, "center", seed=20)
    cred = TLine("김경준  ·  정진영  ·  강석주       COMING SOON", "SemiBold", 24, (190, 200, 190), W / 2, H - 160, "center", track=5, shadow=0)
    screens = ["2장 수정본.png", "3장.png", "9장.png", "5장.png", "11장.png"]
    SW, SH = 920, 518
    shots = [T.graded(n).resize((SW, SH), Image.LANCZOS).convert("RGBA") for n in screens]

    def s14(t, d):
        fr = dark()
        rings(fr, W / 2, H / 2 - 20, t, n=7, gap=110, base=300, col=(110, 200, 130), alpha=70, squash=0.6, width=2)
        particles(fr, t, 50, 15, (255, 215, 140), 0.6)
        a = eo(t / 0.5)
        fr.alpha_composite(with_alpha(title_e, a), (int(W / 2 - title_e.width / 2), int(70 + 20 * (1 - a))))
        # 모니터
        mt = eo((t - 0.3) / 0.6)
        if mt > 0:
            mx, my = W / 2 - SW / 2, 230 + 40 * (1 - mt)
            mon = Image.new("RGBA", (SW + 120, SH + 160), (0, 0, 0, 0))
            sh = Image.new("RGBA", mon.size, (0, 0, 0, 0))
            ImageDraw.Draw(sh).rounded_rectangle((40, 50, 40 + SW + 40, 50 + SH + 40), 26, fill=(0, 0, 0, 160))
            mon.alpha_composite(sh.filter(ImageFilter.GaussianBlur(18)))
            md = ImageDraw.Draw(mon)
            md.rounded_rectangle((40, 30, 40 + SW + 40, 30 + SH + 40), 24, fill=(22, 24, 26, 255), outline=(70, 74, 78, 255), width=3)
            seg = 1.1
            k = int(max(0, t - 0.6) / seg) % len(shots)
            lt = max(0, t - 0.6) % seg
            scr = shots[k]
            if lt < 0.25 and t > 0.6 + seg:
                scr = Image.blend(shots[(k - 1) % len(shots)], shots[k], lt / 0.25)
            mon.alpha_composite(scr, (60, 50))
            md.rectangle((40 + SW / 2 - 30 + 20, 30 + SH + 40, 40 + SW / 2 + 30 + 20, 30 + SH + 80), fill=(40, 42, 46, 255))
            md.rounded_rectangle((40 + SW / 2 - 130 + 20, 30 + SH + 78, 40 + SW / 2 + 170, 30 + SH + 92), 6, fill=(50, 52, 56, 255))
            fr.alpha_composite(with_alpha(mon, mt), (int(mx - 60), int(my - 30)))
        tag_e.draw(fr, t - 1.2, "word", 0.12)
        cred.draw(fr, t - 2.0, "fade")
        fade = eio((t - d + 0.8) / 0.8)
        if fade > 0: fr.alpha_composite(Image.new("RGBA", (W, H), (0, 0, 0, int(255 * fade))))
        return fr
    S.append(Scene(16 * BEAT, s14, "white"))
    return S


# ------------------------------------------------------------------ 타임라인 / 렌더
def timeline(S):
    tl, t = [], 0.0
    for sc in S:
        tl.append((sc, t, t + sc.dur)); t += sc.dur
    return tl, t


def frame_at(tl, t):
    for idx, (sc, s, e) in enumerate(tl):
        if s <= t < e or (idx == len(tl) - 1 and t >= s):
            lt = t - s
            random.seed(int(t * 1000))
            cur = sc.draw(lt, sc.dur)
            if idx > 0 and lt < TR:
                ps, pst, pe = tl[idx - 1]
                out = ps.draw(pe - pst + lt, ps.dur)
                cur = T.Renderer.transition(None, sc.tr, out, cur, lt / TR)
            return cur


# ------------------------------------------------------------------ 음악
def make_music(tl, total, path):
    SR = T.SR; put, pad, brass, taiko, impact, riser, whoosh, click, reverb = T.put, T.pad, T.brass, T.taiko, T.impact, T.riser, T.whoosh, T.click, T.reverb
    mn, triad, filt, env, saw, mf = T.mn, T.triad, T.filt, T.env, T.saw, T.mf
    N = int((total + 3) * SR); mus, drm = np.zeros(N), np.zeros(N)
    starts = [s for _, s, _ in tl]
    t_title, t_body, t_loop, t_end = starts[1], starts[2], starts[12], starts[14]
    # 오프닝: 신비로운 드론 + 맥박
    put(mus, pad([T.mn("D2"), T.mn("A2")], t_title, 0.12, 1), 0)
    put(mus, pad([T.mn("A3"), T.mn("D4")], t_title - 2.5, 0.05, 2), 2.5)
    for k in range(int(t_title / BEAT)):
        put(drm, taiko(0.35 if k % 2 else 0.5, 70, 40, 7, k), k * BEAT, 0.5)
    put(drm, riser(2.5, 3), t_title - 2.5, 0.9)
    # 타이틀 임팩트 + 짧은 팡파레
    put(drm, impact(1), t_title, 1.1)
    for m, a in (("D5", 0.3), ("A4", 0.22), ("F4", 0.2), ("D4", 0.22)):
        put(mus, brass(mn(m), 2.6, a), t_title)
    put(mus, pad(triad("D", 3, 3) + [mn("D2")], t_body - t_title, 0.12, 5), t_title)
    # 본문
    bar = 4 * BEAT
    CH, MEL = T.CHORDS, T.MELODY
    nb = int(math.ceil((t_end - t_body) / bar - 1e-6))
    for b in range(nb):
        t0 = t_body + b * bar; bl = min(bar, t_end - t0)
        root, third = CH[b % 4]
        sec = 1 if starts[6] <= t0 < starts[10] else 2 if t0 >= starts[10] else 0
        if t0 >= t_loop: sec = 3
        put(mus, pad(triad(root, third, 3) + [triad(root, third, 4)[0]], bl, 0.11 if sec != 1 else 0.13, b), t0)
        for k in range(int(bl / (BEAT / 2) + 1e-6)):
            n = int(0.24 * SR)
            x = filt(saw(mf(mn(root + "2")), n, (0, 5)), "low", 500) * env(n, 0.005, 0.1, 0.5, 0.08, 0.18)
            put(mus, x, t0 + k * BEAT / 2, 0.2 if sec != 1 else 0.11)
        cn = triad(root, third, 4); pat = [cn[0], cn[1], cn[2], cn[0] + 12]
        for k in range(int(bl / (BEAT / 4) + 1e-6)):
            n = int(0.2 * SR)
            x = filt(saw(mf(pat[k % 4]), n, (-6, 6), k), "low", 3200) * env(n, 0.005, 0.12, 0, 0.05, 0.12)
            put(mus, x, t0 + k * BEAT / 4, 0.085 if sec != 1 else 0.05)
        hits = {0: [(0, 1), (3, .6), (4, .85), (6, .7), (7, .45)], 1: [(0, .7), (4, .45)],
                2: [(0, 1), (2, .5), (3, .6), (4, .9), (5, .5), (6, .75), (7, .6)], 3: [(0, .8), (4, .6), (6, .5)]}[sec]
        for k, a in hits:
            if k * BEAT / 2 < bl - 1e-6: put(drm, taiko(a, seed=b * 10 + k), t0 + k * BEAT / 2, 0.55)
        if b >= 1:
            tt = t0
            for note, beats in MEL[b % 4]:
                if tt - t0 < bl - 1e-6:
                    dd = min(beats * BEAT * 0.95, t_end - tt)
                    amp = 0.28 if sec != 1 else 0.18
                    put(mus, brass(mn(note), dd, amp), tt); put(mus, brass(mn(note) - 12, dd, amp * .55), tt)
                    if sec >= 2: put(mus, brass(mn(note) + 12, dd, amp * .22), tt)
                tt += beats * BEAT
    for idx, (sc, s, e) in enumerate(tl[2:], 2):
        put(drm, whoosh(0.4, idx), s - 0.25, 0.3)
        put(drm, impact(idx * 7), s, 0.55 if idx not in (12, 13) else 0.8)
    put(drm, impact(77), starts[4] + 0.2, 0.9)  # 넘어짐
    for k in range(3):  # 카드 넘김
        put(drm, whoosh(0.25, 40 + k), starts[10] + 0.3 + k * (tl[10][0].dur - 0.3) / 3 - 0.1, 0.25)
    # 엔딩
    od = total - t_end
    put(drm, impact(500), t_end, 1.0)
    put(mus, pad(triad("D", 3, 3) + triad("D", 3, 4) + [mn("D2")], od - 0.5, 0.13, 42), t_end)
    for m, a in (("D5", 0.32), ("A4", 0.24), ("D4", 0.24)): put(mus, brass(mn(m), 3.0, a), t_end)
    put(drm, taiko(1.5, 80, 40, 2.5, 7, 1.2), t_end)
    mix = reverb(mus, 2.4, 0.35, 1) + reverb(drm, 1.6, 0.18, 2)
    mix = mix[:int(total * SR)]
    fade = int(1.5 * SR); mix[-fade:] *= np.linspace(1, 0, fade)
    mix = np.tanh(mix / np.abs(mix).max() * 1.6) * 0.9
    st = np.stack([mix, np.roll(mix, 220) * 0.97], 1)
    with wave.open(path, "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((st * 32767).astype(np.int16).tobytes())


def main():
    S = build()
    tl, total = timeline(S)
    if len(sys.argv) > 1 and sys.argv[1] == "preview":
        for t in [float(x) for x in sys.argv[3].split(",")]:
            frame_at(tl, t).convert("RGB").resize((640, 360), Image.LANCZOS).save(os.path.join(sys.argv[2], f"r_{t:05.2f}.png"))
        print("total", total, [round(s, 2) for _, s, _ in tl])
        return
    mdir = os.path.join(HERE, "음악"); os.makedirs(mdir, exist_ok=True)
    wav = os.path.join(mdir, "BGM_소개릴.wav")
    print("음악 합성...", flush=True)
    make_music(tl, total, wav)
    ff = imageio_ffmpeg.get_ffmpeg_exe()
    subprocess.run([ff, "-y", "-loglevel", "error", "-i", wav, "-b:a", "320k", wav[:-4] + ".mp3"], check=True)
    tmp = os.path.join(HERE, "_tmp_reel.mp4")
    p = subprocess.Popen([ff, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                          "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "slow", "-crf", "16",
                          "-pix_fmt", "yuv420p", tmp], stdin=subprocess.PIPE)
    nf = int(round(total * FPS))
    for fi in range(nf):
        p.stdin.write(frame_at(tl, fi / FPS).convert("RGB").tobytes())
        if fi % 90 == 0: print(f"  {fi}/{nf}", flush=True)
    p.stdin.close(); p.wait()
    final = os.path.join(HERE, "게임소개_릴.mp4")
    subprocess.run([ff, "-y", "-loglevel", "error", "-i", tmp, "-i", wav, "-c:v", "copy", "-c:a", "aac", "-b:a", "256k",
                    "-shortest", "-movflags", "+faststart", final], check=True)
    os.remove(tmp)
    print("완료:", final)


if __name__ == "__main__":
    main()
