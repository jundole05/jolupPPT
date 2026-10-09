# -*- coding: utf-8 -*-
"""말파이트 게임 티저 모션그래픽 + BGM 생성기.
사용: python make_teaser.py sample   (10초 샘플)
      python make_teaser.py full     (전체 티저)
"""
import math, os, random, subprocess, sys, wave
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
import imageio_ffmpeg

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.dirname(os.path.abspath(__file__))
W, H, FPS = 1920, 1080, 30
BPM = 120
BEAT = 60 / BPM
FONT_B = r"C:\Windows\Fonts\malgunbd.ttf"
FONT_R = r"C:\Windows\Fonts\malgun.ttf"
GOLD_HI, GOLD_LO = (255, 236, 170), (214, 150, 40)

# ---------------------------------------------------------------- 문구 (PPT 기준)
SLIDES = {
    1: dict(img="1장 수정본.png", label="승마 레이싱 & 육성 RPG",
            quote=["교수님 말입니다.", "유기는 안 됩니다."], desc=[], stamp="유기 금지",
            pan=(-1, 0)),
    2: dict(img="2장 수정본.png", label="레이싱 시스템",
            quote=["이렇게 예쁜 말을 받았는데", "일단 타봐야죠."],
            desc=["직접 키운 말로 경마 레이싱", "승마만의 독특한 레이싱 감각", "플레이어와 말이 호흡하는 시스템"],
            pan=(0, -1)),
    3: dict(img="3장.png", label="멀티 레이싱",
            quote=["왜 추월하면서 쳐다보죠?", "짜증나네? 따라가겠습니다."],
            desc=["다인 실시간 대전", "몸싸움 등 멀티플레이 변수 창출"], pan=(1, 0)),
    4: dict(img="4장.png", label="장애물 & 다양한 코스",
            quote=["네가 느린 건지 내가 못 타는 건지,", "일단 둘 다 의심스럽다."],
            desc=["특색있는 장애물과 다양한 코스", "반복 숙달 및 말 성장"], shake=True, pan=(0, 1)),
    5: dict(img="5장.png", label="마을 · 사육 · 상호작용",
            quote=["아 너 달릴 줄 잘 모르는구나.", "제가 문제였습니다."],
            desc=["육성 컨텐츠의 허브, 마을", "밥먹이기 등 애착 형성 활동", "다른 플레이어와 만나는 커뮤니티"], pan=(-1, 0)),
    6: dict(img="6장.png", label="육성 · 능력치 향상",
            quote=["진 건 괜찮습니다.", "다음에 이기면 되니까요."],
            desc=["전략적 선택을 통한 능력치 향상", "상호작용을 통한 육성 재미"], pan=(1, 0)),
    7: dict(img="7장.png", label="치장 · 내 말의 개성",
            quote=["MZ는 타는 말도", "다르게 생겼습니다."],
            desc=["말 꾸미기로 애착 형성", "나만의 말을 꾸미는 재미"], pan=(0, -1)),
    8: dict(img="8장.png", label="교배 · 새로운 말",
            quote=["나도 없는 애인,", "우리 말이라도 만들어줘야죠."],
            desc=["교배를 통한 능력치 계승", "나만의 독특한 말 생성"], pan=(-1, 0)),
    9: dict(img="9장.png", label="장애물 판단 · 직접 조작",
            quote=["여기다.", "내가 무너졌던 곳."],
            desc=["타이밍을 읽고 직접 극복하라"], pan=(0, 1)),
    10: dict(img="10장.png", label="플레이 방식 선택",
             quote=["연습 좀 할까요?", "아님 아까 그XX 잡으러 갈까요?"],
             desc=["솔로 모드  ·  AI 모드  ·  PVP 모드"], pan=(1, 0)),
    11: dict(img="11장.png", label="순위 보상 · 마을과 레이싱",
             quote=["우승해서 돈 벌었다,", "말순아 명품 사줄게."],
             desc=["대회 결과에 따른 보상", "보상으로 이어지는 육성과 치장"], pan=(-1, 0)),
    12: dict(img="12장.png", label="내 말과 함께 성장하는 승마 게임",
             quote=["이제 말순이가 지면", "좀 억울하지 않습니까?"],
             desc=["내가 돌보고 꾸민 말을 직접 탄다"], pan=(0, -1)),
}

SEG = 6 * BEAT  # 슬라이드 1장 = 6박 = 3초


def timeline(mode):
    """[(kind, arg, start, end)]"""
    tl, t = [("intro", None, 0.0, 4 * BEAT)], 4 * BEAT
    ids = [1, 2] if mode == "sample" else list(range(1, 13))
    for i in ids:
        tl.append(("slide", i, t, t + SEG)); t += SEG
    end_len = 4 * BEAT if mode == "sample" else 8 * BEAT
    tl.append(("outro", mode, t, t + end_len))
    return tl, t + end_len


# ---------------------------------------------------------------- 텍스트 렌더링
_fc = {}


def font(sz, bold=True):
    k = (sz, bold)
    if k not in _fc:
        _fc[k] = ImageFont.truetype(FONT_B if bold else FONT_R, sz)
    return _fc[k]


def text_layer(lines, sz, fill=(255, 255, 255), strokes=(), gold=False, spacing=1.18, bold=True, glow=None):
    """여러 줄 텍스트를 RGBA 이미지로. strokes=[(width,(r,g,b,a)), ...] 바깥→안쪽 순서."""
    f = font(sz, bold)
    pad = max([w for w, _ in strokes] + [0]) + 30
    widths = [f.getbbox(l)[2] - f.getbbox(l)[0] for l in lines]
    lh = int(sz * spacing)
    w, h = max(widths) + pad * 2, lh * len(lines) + pad * 2
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    for sw, col in strokes:
        d = ImageDraw.Draw(img)
        for i, l in enumerate(lines):
            d.text((w / 2, pad + i * lh), l, font=f, anchor="ma", fill=col, stroke_width=sw, stroke_fill=col)
    mask = Image.new("L", (w, h), 0)
    md = ImageDraw.Draw(mask)
    for i, l in enumerate(lines):
        md.text((w / 2, pad + i * lh), l, font=f, anchor="ma", fill=255)
    if gold:
        grad = Image.new("RGBA", (w, h))
        gd = ImageDraw.Draw(grad)
        for y in range(h):
            k = ((y - pad) % lh) / lh
            c = tuple(int(GOLD_HI[j] + (GOLD_LO[j] - GOLD_HI[j]) * min(1, k * 1.3)) for j in range(3))
            gd.line([(0, y), (w, y)], fill=c + (255,))
        img.paste(grad, (0, 0), mask)
    else:
        img.paste(Image.new("RGBA", (w, h), fill + (255,)), (0, 0), mask)
    if glow:
        g = Image.new("RGBA", (w, h), glow[:3] + (0,))
        g.putalpha(mask.filter(ImageFilter.GaussianBlur(glow[3])).point(lambda v: min(255, v * 2)))
        base = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        base.alpha_composite(g)
        base.alpha_composite(img)
        img = base
    return img


def label_layer(text):
    t = text_layer([text], 58, gold=True, strokes=[(4, (60, 30, 0, 230))], glow=(255, 190, 80, 10))
    w, h = t.size
    lay = Image.new("RGBA", (w + 260, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    cy = h // 2
    for side in (-1, 1):
        x0 = (lay.width // 2) + side * (w // 2 - 10)
        x1 = x0 + side * 120
        d.line([(x0, cy), (x1, cy)], fill=(240, 200, 110, 230), width=3)
        dx = x1 + side * 12
        d.polygon([(dx - 10, cy), (dx, cy - 10), (dx + 10, cy), (dx, cy + 10)], fill=(255, 220, 130, 255))
    lay.alpha_composite(t, ((lay.width - w) // 2, 0))
    return lay


def quote_layer(lines):
    # 예능 자막 스타일: 흰 글씨 + 검정 테두리 + 노란 바깥 테두리
    return text_layer(["“" + lines[0]] + lines[1:-1] + [lines[-1] + "”"] if len(lines) > 1 else ["“" + lines[0] + "”"],
                      74, fill=(255, 255, 255), strokes=[(16, (255, 200, 40, 255)), (9, (20, 20, 30, 255))])


def desc_layer(line):
    t = text_layer(["◆  " + line + "  ◆"], 42, fill=(255, 246, 225), strokes=[(5, (10, 10, 10, 200))], bold=False)
    return t


def stamp_layer(text):
    f = font(70)
    tw = f.getbbox(text)[2]
    w, h = tw + 80, 130
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    red = (225, 30, 40, 255)
    d.rounded_rectangle((6, 6, w - 6, h - 6), 18, fill=(255, 245, 235, 200), outline=red, width=9)
    d.text((w / 2, h / 2), text, font=f, fill=red, anchor="mm")
    return img.rotate(-12, expand=True, resample=Image.BICUBIC)


# ---------------------------------------------------------------- 연출 유틸
def ease_out(x):
    x = max(0, min(1, x)); return 1 - (1 - x) ** 3


def ease_back(x, s=1.9):
    x = max(0, min(1, x)); x -= 1; return x * x * ((s + 1) * x + s) + 1


def paste(frame, layer, cx, cy, alpha=1.0, scale=1.0, rot=0):
    if alpha <= 0.01 or scale <= 0.01:
        return
    lay = layer
    if abs(scale - 1) > 0.005:
        lay = lay.resize((max(1, int(lay.width * scale)), max(1, int(lay.height * scale))), Image.BILINEAR)
    if rot:
        lay = lay.rotate(rot, expand=True, resample=Image.BILINEAR)
    if alpha < 0.999:
        a = lay.getchannel("A").point(lambda v: int(v * alpha))
        lay = lay.copy(); lay.putalpha(a)
    frame.alpha_composite(lay, (int(cx - lay.width / 2), int(cy - lay.height / 2)))


def make_overlay():
    """하단 어둡게 + 비네팅"""
    y = np.linspace(0, 1, H)[:, None]
    x = np.linspace(-1, 1, W)[None, :]
    yy = np.linspace(-1, 1, H)[:, None]
    bottom = np.clip((y - 0.42) / 0.58, 0, 1) ** 1.4 * 0.82
    top = np.clip((0.22 - y) / 0.22, 0, 1) * 0.55
    vig = np.clip((np.sqrt(x ** 2 * 0.8 + yy ** 2) - 0.6) / 0.8, 0, 1) * 0.6
    a = np.clip(bottom + top + vig, 0, 0.9)
    arr = np.zeros((H, W, 4), np.uint8)
    arr[..., 3] = (a * 255).astype(np.uint8)
    return Image.fromarray(arr, "RGBA")


class Particles:
    def __init__(self, n=70, seed=7):
        r = random.Random(seed)
        self.p = [(r.uniform(0, W), r.uniform(0, H), r.uniform(1.5, 5), r.uniform(10, 45), r.uniform(0, 6.28), r.uniform(0.3, 1))
                  for _ in range(n)]

    def draw(self, frame, t, strength=1.0):
        lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(lay)
        for x, y, s, sp, ph, a in self.p:
            yy = (y - t * sp) % H
            xx = x + math.sin(t * 0.8 + ph) * 25
            al = int(255 * a * strength * (0.55 + 0.45 * math.sin(t * 3 + ph)))
            d.ellipse((xx - s, yy - s, xx + s, yy + s), fill=(255, 220, 140, max(0, al)))
        frame.alpha_composite(lay.filter(ImageFilter.GaussianBlur(1.2)))


_img_cache = {}


def load_img(name):
    if name not in _img_cache:
        _img_cache[name] = Image.open(os.path.join(ROOT, name)).convert("RGB")
    return _img_cache[name]


def ken_burns(img, p, pan, shake=(0, 0), zoom=(1.04, 1.16)):
    sw, sh = img.size
    s = zoom[0] + (zoom[1] - zoom[0]) * p
    # 16:9 cover
    cw = sw / s
    ch = cw * H / W
    if ch > sh / s * (sw / sw):
        ch = min(ch, sh / s * 1.0)
    cx = sw / 2 + pan[0] * (p - 0.5) * (sw - cw) * 0.8 + shake[0]
    cy = sh / 2 + pan[1] * (p - 0.5) * (sh - ch) * 0.8 + shake[1]
    box = (cx - cw / 2, cy - ch / 2, cx + cw / 2, cy + ch / 2)
    return img.resize((W, H), Image.BILINEAR, box=box).convert("RGBA")


# ---------------------------------------------------------------- 장면 렌더
class Renderer:
    def __init__(self, mode):
        self.mode = mode
        self.overlay = make_overlay()
        self.parts = Particles()
        self.cache = {}
        for i, s in SLIDES.items():
            self.cache[i] = dict(
                label=label_layer(s["label"]),
                quote=quote_layer(s["quote"]),
                desc=[desc_layer(l) for l in s["desc"]],
                stamp=stamp_layer(s["stamp"]) if s.get("stamp") else None)
        self.intro1 = text_layer(["어느 날,"], 50, fill=(240, 225, 190), strokes=[(3, (0, 0, 0, 160))], bold=False)
        self.intro2 = text_layer(["당신에게 말 한 마리가 도착했다"], 78, gold=True,
                                 strokes=[(5, (50, 25, 0, 220))], glow=(255, 180, 60, 16))
        self.logo = text_layer(["말파이트"], 230, gold=True, strokes=[(14, (40, 18, 0, 255))], glow=(255, 170, 40, 30))
        self.logo_en = text_layer(["H O R S E   F I G H T"], 44, fill=(255, 240, 200), strokes=[(3, (0, 0, 0, 180))])
        self.tagline = text_layer(["내 말과 함께 성장하는 승마 게임"], 52, fill=(255, 250, 235),
                                  strokes=[(5, (0, 0, 0, 200))])
        self.team = text_layer(["김경준  ·  정진영  ·  강석주"], 40, fill=(235, 225, 200), strokes=[(3, (0, 0, 0, 180))], bold=False)
        self.soon = text_layer(["COMING SOON"], 64, gold=True, strokes=[(5, (40, 18, 0, 230))], glow=(255, 190, 80, 14))
        bg = load_img("12장.png").resize((W, H), Image.BILINEAR).filter(ImageFilter.GaussianBlur(14))
        self.outro_bg = Image.blend(bg, Image.new("RGB", (W, H), (10, 8, 5)), 0.55).convert("RGBA")

    def flash(self, frame, a):
        if a > 0.01:
            frame.alpha_composite(Image.new("RGBA", (W, H), (255, 245, 225, int(255 * min(1, a)))))

    def intro(self, t, dur):
        frame = Image.new("RGBA", (W, H), (6, 5, 4, 255))
        # 금빛 빛줄기
        streak = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(streak)
        sw = int(W * ease_out(t / dur * 1.3))
        d.rectangle((W / 2 - sw / 2, H / 2 + 70, W / 2 + sw / 2, H / 2 + 74), fill=(255, 200, 100, 200))
        frame.alpha_composite(streak.filter(ImageFilter.GaussianBlur(4)))
        self.parts.draw(frame, t, 0.6)
        paste(frame, self.intro1, W / 2, H / 2 - 90, alpha=ease_out(t / 0.4))
        p = ease_out((t - 0.35) / 0.8)
        paste(frame, self.intro2, W / 2, H / 2 + 5, alpha=p, scale=1.15 - 0.15 * p)
        return frame

    def slide(self, i, t, dur):
        s, c = SLIDES[i], self.cache[i]
        p = t / dur
        shake = (0, 0)
        if s.get("shake") and 0.35 < t < 0.95:
            k = (0.95 - t) / 0.6
            shake = (random.uniform(-1, 1) * 40 * k, random.uniform(-1, 1) * 30 * k)
        zoom = (1.0, 1.07) if t > 0.15 else (1.0 + (0.15 - t) * 0.8, 1.07)  # 시작 펀치 줌
        frame = ken_burns(load_img(s["img"]), p, s["pan"], shake, zoom)
        frame.alpha_composite(self.overlay)
        self.parts.draw(frame, t + i * 3, 0.7)
        # 시스템 라벨 (금색, 상단)
        la = ease_out(t / 0.3) * (1 - ease_out((t - dur + 0.2) / 0.2))
        paste(frame, c["label"], W / 2, 105 - 30 * (1 - ease_out(t / 0.35)), alpha=la)
        # 따옴표 대사 (예능 자막, 팝)
        qt = t - 0.35
        if qt > 0:
            sc = 0.6 + 0.4 * ease_back(qt / 0.32)
            qa = min(1, qt / 0.12) * (1 - ease_out((t - dur + 0.15) / 0.15))
            qy = 700 if c["desc"] else 760
            paste(frame, c["quote"], W / 2, qy, alpha=qa, scale=sc, rot=1.5 * (1 - min(1, qt / 0.3)))
        # 시스템 설명
        n = len(c["desc"])
        for k, dl in enumerate(c["desc"]):
            dt = t - (1.25 + k * 0.28)
            if dt > 0:
                a = ease_out(dt / 0.3) * (1 - ease_out((t - dur + 0.15) / 0.15))
                y = 875 + k * 60 - (60 * (n - 1) / 2 if n > 2 else 0) + (n > 2) * 30
                paste(frame, dl, W / 2 - 60 * (1 - ease_out(dt / 0.3)), y, alpha=a)
        # 도장 개그
        if c["stamp"] is not None:
            st = t - 1.35
            if st > 0:
                sc = 2.2 - 1.2 * ease_out(st / 0.16)
                paste(frame, c["stamp"], W / 2 + 470, 610, alpha=min(1, st / 0.08), scale=sc)
        # 장면 시작 플래시
        self.flash(frame, (1 - t / 0.12) * 0.85 if t < 0.12 else 0)
        return frame

    def outro(self, t, dur):
        frame = self.outro_bg.copy()
        self.parts.draw(frame, t, 1.0)
        full = self.mode == "full"
        tag_t = 0.0 if not full else 0.0
        paste(frame, self.tagline, W / 2, 330, alpha=ease_out((t - tag_t) / 0.4))
        lt = t - 0.25
        if lt > 0:
            sc = 1.0 + 0.8 * (1 - ease_out(lt / 0.22))
            paste(frame, self.logo, W / 2, 520, alpha=min(1, lt / 0.1), scale=sc)
            # 빛 반사 스윕
            sx = -400 + (lt - 0.3) * 2600
            if -400 < sx < W + 400:
                sweep = Image.new("RGBA", (W, H), (0, 0, 0, 0))
                ImageDraw.Draw(sweep).polygon([(sx, 380), (sx + 90, 380), (sx - 60, 660), (sx - 150, 660)],
                                              fill=(255, 255, 240, 120))
                frame.alpha_composite(sweep.filter(ImageFilter.GaussianBlur(18)))
        paste(frame, self.logo_en, W / 2, 712, alpha=ease_out((t - 0.55) / 0.4))
        if full:
            paste(frame, self.team, W / 2, 790, alpha=ease_out((t - 1.2) / 0.5))
            paste(frame, self.soon, W / 2, 900, alpha=ease_out((t - 1.8) / 0.5))
        else:
            paste(frame, self.soon, W / 2, 830, alpha=ease_out((t - 0.9) / 0.4))
        self.flash(frame, (1 - lt / 0.15) * 0.9 if 0 < lt < 0.15 else 0)
        fade = ease_out((t - dur + 0.6) / 0.6) if full else 0
        if fade > 0:
            frame.alpha_composite(Image.new("RGBA", (W, H), (0, 0, 0, int(255 * fade))))
        return frame

    def render(self, kind, arg, t, dur):
        if kind == "intro":
            return self.intro(t, dur)
        if kind == "slide":
            return self.slide(arg, t, dur)
        return self.outro(t, dur)


# ---------------------------------------------------------------- 음악 (직접 합성)
SR = 44100


def mf(m):
    return 440 * 2 ** ((m - 69) / 12)


NOTE = {n: i for i, n in enumerate(["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"])}


def mn(s):  # "D4" -> midi
    return 12 * (int(s[-1]) + 1) + NOTE[s[:-1]]


def env(n, a, d, s, r, sus_len):
    a, d, r = int(a * SR), int(d * SR), int(r * SR)
    sl = max(0, int(sus_len * SR) - a - d)
    e = np.concatenate([np.linspace(0, 1, a, False) if a else [], np.linspace(1, s, d, False) if d else [],
                        np.full(sl, s), np.linspace(s, 0, r)])
    return e[:n] if len(e) >= n else np.pad(e, (0, n - len(e)))


def saw(f, n, detune=(0,), phase_seed=0):
    t = np.arange(n) / SR
    rng = np.random.default_rng(phase_seed)
    out = np.zeros(n)
    for dc in detune:
        ff = f * 2 ** (dc / 1200)
        out += 2 * ((t * ff + rng.random()) % 1) - 1
    return out / len(detune)


def lowpass(x, fc, order=2):
    from scipy.signal import butter, sosfilt
    return sosfilt(butter(order, fc, fs=SR, output="sos"), x)


def highpass(x, fc, order=2):
    from scipy.signal import butter, sosfilt
    return sosfilt(butter(order, fc, btype="high", fs=SR, output="sos"), x)


def add(buf, sig, t0):
    i = int(t0 * SR)
    if i >= len(buf):
        return
    e = min(len(buf), i + len(sig))
    buf[i:e] += sig[:e - i]


def reverb(x, sec=2.2, wet=0.3, seed=1):
    from scipy.signal import fftconvolve
    n = int(sec * SR)
    rng = np.random.default_rng(seed)
    ir = rng.standard_normal(n) * np.exp(-np.arange(n) / SR * 3.2)
    ir = lowpass(ir, 5000)
    ir /= np.sqrt(np.sum(ir ** 2))
    y = fftconvolve(x, ir)[:len(x)]
    return x * (1 - wet) + y * wet * 1.2


CHORDS = [("D", "minor"), ("A#", "major"), ("F", "major"), ("C", "major")]


def chord_notes(root, q, octv):
    r = mn(root + str(octv))
    return [r, r + (3 if q == "minor" else 4), r + 7]


MELODY = [  # 마디별 (음, 박)
    [("A4", 1), ("D5", .5), ("E5", .5), ("F5", 2)],
    [("F5", 1), ("D5", 1), ("A#4", 2)],
    [("A4", 1), ("C5", 1), ("F5", 1), ("E5", 1)],
    [("E5", 1), ("G5", 1), ("E5", .5), ("D5", .5), ("C5", 1)],
]


def taiko(n_sec=0.7, f0=95, f1=48, amp=1.0, seed=0):
    n = int(n_sec * SR)
    t = np.arange(n) / SR
    f = f1 + (f0 - f1) * np.exp(-t * 18)
    ph = 2 * np.pi * np.cumsum(f) / SR
    body = np.sin(ph) * np.exp(-t * 6)
    rng = np.random.default_rng(seed)
    skin = lowpass(rng.standard_normal(n), 1800) * np.exp(-t * 40) * 0.6
    return (body + skin) * amp


def impact(seed=3):
    n = int(2.2 * SR)
    t = np.arange(n) / SR
    sub = np.sin(2 * np.pi * np.cumsum(38 + 50 * np.exp(-t * 9)) / SR) * np.exp(-t * 2.2)
    rng = np.random.default_rng(seed)
    crash = highpass(rng.standard_normal(n), 3000) * np.exp(-t * 2.8) * 0.35
    boom = lowpass(rng.standard_normal(n), 400) * np.exp(-t * 5) * 0.8
    return sub * 1.3 + crash + boom


def riser(sec, seed=5):
    n = int(sec * SR)
    rng = np.random.default_rng(seed)
    x = rng.standard_normal(n)
    out = np.zeros(n)
    steps = 40
    for k in range(steps):
        a, b = k * n // steps, (k + 1) * n // steps
        out[a:b] = highpass(x[a:b], 300 + 6000 * (k / steps) ** 2, 1)
    return out * np.linspace(0, 1, n) ** 2 * 0.5


def brass(m, dur, amp=0.32):
    n = int((dur + 0.4) * SR)
    t = np.arange(n) / SR
    f = mf(m) * (1 + 0.004 * np.sin(2 * np.pi * 5.5 * t) * np.clip(t / 0.3, 0, 1))
    ph = 2 * np.pi * np.cumsum(f) / SR
    x = sum(np.sin(ph * k) / k ** 1.1 for k in range(1, 12))
    x = lowpass(x, 2600)
    return x * env(n, 0.06, 0.15, 0.8, 0.35, dur) * amp


def strings_pad(notes, dur, amp=0.12, seed=0):
    n = int((dur + 0.6) * SR)
    x = sum(saw(mf(m), n, (-9, 0, 8), seed + m) for m in notes)
    x = lowpass(x, 2200)
    return x * env(n, 0.25, 0.3, 0.85, 0.6, dur) * amp


def ostinato_note(m, amp=0.09):
    n = int(0.2 * SR)
    x = saw(mf(m), n, (-6, 6), m)
    x = lowpass(x, 3200)
    return x * env(n, 0.005, 0.12, 0.0, 0.05, 0.12) * amp


def make_music(tl, total, path):
    buf_m = np.zeros(int((total + 3) * SR))  # 악기 (리버브 많이)
    buf_d = np.zeros_like(buf_m)  # 타악
    start_music = tl[1][2]  # 첫 슬라이드 시작 = 본곡 시작
    outro_t = tl[-1][2]
    # 인트로: 저음 드론 + 상승 노이즈
    add(buf_m, strings_pad([mn("D2"), mn("A2"), mn("D3")], start_music, amp=0.16), 0)
    add(buf_d, riser(start_music, 9) * 0.8, 0)
    bar = 4 * BEAT
    nbars = int(math.ceil((outro_t - start_music) / bar))
    for b in range(nbars):
        t0 = start_music + b * bar
        root, q = CHORDS[b % 4]
        blen = min(bar, outro_t - t0)
        add(buf_m, strings_pad(chord_notes(root, q, 3) + [chord_notes(root, q, 4)[0]], blen, seed=b), t0)
        bassm = mn(root + "2")
        # 베이스 8분음 맥동
        for k in range(int(blen / (BEAT / 2))):
            n = int(0.24 * SR)
            x = lowpass(saw(mf(bassm), n, (0, 5)), 500) * env(n, 0.005, 0.1, 0.5, 0.08, 0.18) * 0.22
            add(buf_m, x, t0 + k * BEAT / 2)
        # 16분 오스티나토 (2마디째부터)
        if b >= 1:
            cn = chord_notes(root, q, 4)
            pat = [cn[0], cn[1], cn[2], cn[1] + 12 if False else cn[0] + 12]
            for k in range(int(blen / (BEAT / 4))):
                add(buf_m, ostinato_note(pat[k % 4]), t0 + k * BEAT / 4)
        # 타이코 패턴 (8분음 기준 0,3,4,6) + 빠른 필
        for k, a in [(0, 1.0), (3, 0.6), (4, 0.85), (6, 0.7), (7, 0.45)]:
            if k * BEAT / 2 < blen:
                add(buf_d, taiko(amp=a, seed=b * 10 + k) * 0.55, t0 + k * BEAT / 2)
        # 금관 멜로디 (3마디째부터)
        if b >= 2:
            tt = t0
            for note, beats in MELODY[b % 4]:
                if tt - t0 < blen:
                    add(buf_m, brass(mn(note), beats * BEAT * 0.95), tt)
                    add(buf_m, brass(mn(note) - 12, beats * BEAT * 0.95, amp=0.18), tt)
                tt += beats * BEAT
    # 장면 전환마다 임팩트
    for kind, arg, s, e in tl[1:]:
        add(buf_d, impact(int(s * 10)) * (0.7 if kind == "slide" else 1.1), s)
        if kind == "slide" and SLIDES[arg].get("stamp"):
            add(buf_d, taiko(0.5, 160, 70, 1.3, 99), s + 1.35)  # 도장 쾅
        if kind == "slide" and SLIDES[arg].get("shake"):
            add(buf_d, impact(77) * 0.9, s + 0.35)  # 넘어짐 쿵
    # 아웃트로: 최종 화음 + 멜로디 마무리
    od = total - outro_t
    final = chord_notes("D", "minor", 3) + chord_notes("D", "minor", 4) + [mn("D2")]
    add(buf_m, strings_pad(final, od, amp=0.15, seed=42), outro_t)
    add(buf_m, brass(mn("D5"), od * 0.9, 0.36), outro_t + 0.25)
    add(buf_m, brass(mn("A4"), od * 0.9, 0.26), outro_t + 0.25)
    add(buf_m, brass(mn("D4"), od * 0.9, 0.26), outro_t + 0.25)
    add(buf_d, taiko(1.2, 80, 40, 1.6, 7), outro_t + 0.25)
    mix = reverb(buf_m, 2.4, 0.35) + reverb(buf_d, 1.6, 0.18, 2)
    mix = mix[:int(total * SR)]
    fade = int(0.8 * SR)
    mix[-fade:] *= np.linspace(1, 0, fade)
    mix = np.tanh(mix / np.max(np.abs(mix)) * 1.6) * 0.9
    st = np.stack([mix, np.roll(mix, 220) * 0.97], 1)  # 살짝 스테레오
    with wave.open(path, "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((st * 32767).astype(np.int16).tobytes())


# ---------------------------------------------------------------- 메인
def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "sample"
    tl, total = timeline(mode)
    tag = "샘플10초" if mode == "sample" else "전체"
    music_dir = os.path.join(OUT, "음악")
    os.makedirs(music_dir, exist_ok=True)
    wav = os.path.join(music_dir, f"말파이트_BGM_{tag}.wav")
    print("음악 합성...", flush=True)
    make_music(tl, total, wav)
    ff = imageio_ffmpeg.get_ffmpeg_exe()
    subprocess.run([ff, "-y", "-loglevel", "error", "-i", wav, "-b:a", "256k", wav[:-4] + ".mp3"], check=True)
    silent = os.path.join(OUT, "_video_tmp.mp4")
    p = subprocess.Popen([ff, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                          "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "18",
                          "-pix_fmt", "yuv420p", silent], stdin=subprocess.PIPE)
    r = Renderer(mode)
    nf = int(total * FPS)
    random.seed(1)
    for fi in range(nf):
        t = fi / FPS
        for kind, arg, s, e in tl:
            if s <= t < e or (kind == "outro" and t >= s):
                fr = r.render(kind, arg, t - s, e - s)
                break
        p.stdin.write(fr.convert("RGB").tobytes())
        if fi % 30 == 0:
            print(f"  {fi}/{nf}", flush=True)
    p.stdin.close(); p.wait()
    final = os.path.join(OUT, f"말파이트_티저_{tag}.mp4")
    subprocess.run([ff, "-y", "-loglevel", "error", "-i", silent, "-i", wav, "-c:v", "copy", "-c:a", "aac",
                    "-b:a", "256k", "-shortest", final], check=True)
    os.remove(silent)
    print("완료:", final)


if __name__ == "__main__":
    main()
