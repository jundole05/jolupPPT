# -*- coding: utf-8 -*-
"""말파이트 15초 티저 (모던 모션그래픽 버전) + BGM.
python make_teaser15.py
"""
import math, os, random, subprocess, wave
import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont
import imageio_ffmpeg

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.dirname(os.path.abspath(__file__))
W, H, FPS = 1920, 1080, 30
BPM = 120
BEAT = 60 / BPM
F_KB = r"C:\Windows\Fonts\malgunbd.ttf"
F_KL = r"C:\Windows\Fonts\malgunsl.ttf"
F_EN = r"C:\Windows\Fonts\bahnschrift.ttf"
AMBER = (255, 190, 90)
WHITE = (255, 255, 255)
BAR = 74  # 레터박스 높이
X0 = 150  # 텍스트 왼쪽 여백

SCENES = [
    dict(img="1장 수정본.png", no="01", kicker="MEET YOUR HORSE", title="승마 레이싱 & 육성 RPG",
         desc=["직접 키우고, 직접 달린다"], pan=(-1, 0)),
    dict(img="2장 수정본.png", no="02", kicker="RACING SYSTEM", title="레이싱 시스템",
         desc=["직접 키운 말로 경마 레이싱", "승마만의 독특한 레이싱 감각"], pan=(1, -0.3)),
    dict(img="3장.png", no="03", kicker="MULTIPLAYER RACE", title="멀티 레이싱",
         desc=["다인 실시간 대전", "몸싸움 등 멀티플레이 변수 창출"], pan=(-1, 0.2)),
]
INTRO, SCENE, OUTRO = 4 * BEAT, 6 * BEAT, 8 * BEAT  # 2s, 3s, 4s → 총 15s


def timeline():
    tl, t = [("intro", None, 0.0, INTRO)], INTRO
    for i in range(len(SCENES)):
        tl.append(("scene", i, t, t + SCENE)); t += SCENE
    tl.append(("outro", None, t, t + OUTRO))
    return tl, t + OUTRO


# ------------------------------------------------------------------ 타이포
_fc = {}


def font(path, sz, var=None):
    k = (path, sz, var)
    if k not in _fc:
        f = ImageFont.truetype(path, sz)
        if var:
            f.set_variation_by_name(var)
        _fc[k] = f
    return _fc[k]


def tracked(text, f, fill, track=0, shadow=True):
    """자간 적용 한 줄 텍스트 RGBA (그림자 포함)"""
    widths = [f.getlength(c) for c in text]
    tw = int(sum(widths) + track * (len(text) - 1))
    asc, desc = f.getmetrics()
    pad = 40
    img = Image.new("RGBA", (tw + pad * 2, asc + desc + pad * 2), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    x = pad
    for c, w in zip(text, widths):
        d.text((x, pad), c, font=f, fill=fill + (255,) if len(fill) == 3 else fill)
        x += w + track
    if shadow:
        sh = Image.new("RGBA", img.size, (0, 0, 0, 0))
        sh.putalpha(img.getchannel("A").filter(ImageFilter.GaussianBlur(10)).point(lambda v: int(v * 0.55)))
        base = Image.new("RGBA", img.size, (0, 0, 0, 0))
        base.alpha_composite(sh, (0, 4))
        base.alpha_composite(img)
        img = base
    return img, pad


def paste(frame, lay, x, y, alpha=1.0, anchor="lt", scale=1.0, clip=None):
    """anchor: lt(왼쪽 위 = 텍스트 좌상단), mm(가운데). clip=(y_top, y_bottom) 화면 좌표로 마스크"""
    if alpha <= 0.005:
        return
    if abs(scale - 1) > 0.002:
        lay = lay.resize((max(1, int(lay.width * scale)), max(1, int(lay.height * scale))), Image.BICUBIC)
    if alpha < 0.999:
        lay = lay.copy(); lay.putalpha(lay.getchannel("A").point(lambda v: int(v * alpha)))
    if anchor == "mm":
        x, y = x - lay.width / 2, y - lay.height / 2
    x, y = int(round(x)), int(round(y))
    if clip:
        top, bot = clip
        y0, y1 = max(0, top - y), min(lay.height, bot - y)
        if y1 <= y0:
            return
        lay = lay.crop((0, y0, lay.width, y1)); y += y0
    frame.alpha_composite(lay, (x, y))


def eo(x):  # ease out cubic
    x = min(1, max(0, x)); return 1 - (1 - x) ** 3


def eio(x):
    x = min(1, max(0, x)); return 3 * x * x - 2 * x * x * x


def eexpo(x):
    x = min(1, max(0, x)); return 1 if x == 1 else 1 - 2 ** (-10 * x)


# ------------------------------------------------------------------ 이미지
_big = {}


def graded(name):
    """색보정 + 2배 업스케일(Lanczos) + 샤픈 캐시"""
    if name not in _big:
        im = Image.open(os.path.join(ROOT, name)).convert("RGB")
        im = ImageEnhance.Contrast(im).enhance(1.10)
        im = ImageEnhance.Color(im).enhance(0.92)
        arr = np.asarray(im).astype(np.float32)
        arr[..., 0] *= 1.03; arr[..., 2] *= 0.96  # 살짝 따뜻하게
        im = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
        im = im.resize((im.width * 2, im.height * 2), Image.LANCZOS).filter(ImageFilter.UnsharpMask(2.2, 70, 2))
        _big[name] = im
    return _big[name]


def camera(img, s, ox, oy):
    """s=확대율(1=화면 꽉), ox/oy=-1..1 이동"""
    sw, sh = img.size
    cw = sw / s
    ch = cw * H / W
    if ch > sh / s:
        ch = sh / s; cw = ch * W / H
    cx = sw / 2 + ox * (sw - cw) / 2
    cy = sh / 2 + oy * (sh - ch) / 2
    return img.resize((W, H), Image.BICUBIC, box=(cx - cw / 2, cy - ch / 2, cx + cw / 2, cy + ch / 2)).convert("RGBA")


def hblur(img, k):
    """수평 모션 블러 (축소 후 확대)"""
    if k < 2:
        return img
    small = img.resize((max(8, int(W / k)), H), Image.BILINEAR)
    return small.resize((W, H), Image.BILINEAR)


def make_grad():
    y = np.linspace(0, 1, H)[:, None]
    x = np.linspace(0, 1, W)[None, :]
    a = np.clip((y - 0.45) / 0.55, 0, 1) ** 1.6 * 0.78 + np.clip((0.55 - x) / 0.55, 0, 1) ** 2 * 0.35 * (y > 0.4)
    xx = np.linspace(-1, 1, W)[None, :]; yy = np.linspace(-1, 1, H)[:, None]
    a += np.clip((np.sqrt(xx ** 2 * 0.7 + yy ** 2) - 0.75) / 0.7, 0, 1) * 0.5
    arr = np.zeros((H, W, 4), np.uint8); arr[..., 3] = (np.clip(a, 0, 0.88) * 255).astype(np.uint8)
    return Image.fromarray(arr, "RGBA")


def make_grain(n=6):
    rng = np.random.default_rng(3)
    out = []
    for _ in range(n):
        g = rng.integers(0, 255, (H // 2, W // 2), dtype=np.uint8)
        im = Image.fromarray(g, "L").resize((W, H), Image.BILINEAR)
        rgba = Image.merge("RGBA", (im, im, im, Image.new("L", (W, H), 14)))
        out.append(rgba)
    return out


def light_leak(t, strength):
    if strength <= 0.01:
        return None
    lay = Image.new("RGBA", (W // 4, H // 4), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    cx = (W // 4) * (0.15 + 0.7 * ((t * 0.37) % 1))
    for r, a in [(220, 40), (150, 70), (80, 110)]:
        d.ellipse((cx - r, -r * 0.6, cx + r, r * 0.9), fill=(255, 150, 60, int(a * strength)))
    return lay.filter(ImageFilter.GaussianBlur(40)).resize((W, H), Image.BILINEAR)


# ------------------------------------------------------------------ 렌더러
class R:
    def __init__(self):
        self.grad = make_grad()
        self.grain = make_grain()
        self.sc = []
        for s in SCENES:
            no, _ = tracked(s["no"], font(F_EN, 54, "Light"), AMBER, 2)
            kick, _ = tracked(s["kicker"], font(F_EN, 32, "SemiBold"), (245, 245, 245), 10)
            title, pad = tracked(s["title"], font(F_KB, 96), WHITE, -1)
            desc = [tracked(l, font(F_KL, 36), (240, 240, 240), 1)[0] for l in s["desc"]]
            self.sc.append(dict(no=no, kick=kick, title=title, desc=desc, pad=pad))
        self.intro_a, _ = tracked("어느 날,", font(F_KL, 44), (220, 220, 220), 4)
        self.intro_chars = self._chars("당신에게 말 한 마리가 도착했다", font(F_KL, 66), 6)
        self.tag, _ = tracked("내 말과 함께 성장하는 승마 게임", font(F_KL, 42), (235, 235, 235), 6)
        self.logo, _ = tracked("말파이트", font(F_KB, 230), WHITE, 8)
        self.logo_blur = self.logo.filter(ImageFilter.GaussianBlur(14))
        self.en, _ = tracked("HORSE  FIGHT", font(F_EN, 40, "SemiBold"), AMBER, 22)
        self.team, _ = tracked("김경준  ·  정진영  ·  강석주", font(F_KL, 34), (210, 210, 210), 3)
        self.soon, _ = tracked("COMING SOON", font(F_EN, 34, "SemiBold"), WHITE, 18)
        bg = graded("12장.png").resize((W, H), Image.LANCZOS).filter(ImageFilter.GaussianBlur(18))
        self.outro_bg = Image.blend(bg, Image.new("RGB", (W, H), (8, 7, 6)), 0.62).convert("RGBA")

    def _chars(self, text, f, track):
        chars, x = [], 0
        for c in text:
            lay, pad = tracked(c, f, WHITE, 0)
            chars.append((lay, x - pad))
            x += f.getlength(c) + track
        return chars, x

    def finish(self, frame, fi, bars=1.0, leak=0.0, t=0):
        lk = light_leak(t, leak)
        if lk:
            frame.alpha_composite(lk)
        frame.alpha_composite(self.grain[fi % len(self.grain)])
        if bars > 0:
            b = int(BAR * bars)
            d = ImageDraw.Draw(frame)
            d.rectangle((0, 0, W, b), fill=(0, 0, 0, 255))
            d.rectangle((0, H - b, W, H), fill=(0, 0, 0, 255))
        return frame

    def intro(self, t, dur, fi):
        frame = Image.new("RGBA", (W, H), (5, 5, 6, 255))
        d = ImageDraw.Draw(frame)
        lw = int(560 * eexpo(t / 0.7))
        d.rectangle((W / 2 - lw / 2, H / 2 + 120, W / 2 + lw / 2, H / 2 + 121), fill=AMBER + (200,))
        paste(frame, self.intro_a, W / 2, H / 2 - 70, alpha=eo(t / 0.4), anchor="mm")
        chars, tw = self.intro_chars
        x0 = W / 2 - tw / 2
        for k, (lay, dx) in enumerate(chars):
            ct = t - 0.35 - k * 0.035
            if ct > 0:
                a = eo(ct / 0.35)
                paste(frame, lay, x0 + dx, H / 2 - 40 + 26 * (1 - a), alpha=a)
        out = eio((t - dur + 0.25) / 0.25)
        if out > 0:
            frame.alpha_composite(Image.new("RGBA", (W, H), (255, 250, 240, int(255 * out))))
        return self.finish(frame, fi, bars=eo(t / 1.0), t=t)

    def scene(self, i, t, dur, fi):
        s, c = SCENES[i], self.sc[i]
        p = t / dur
        img = graded(s["img"])
        frame = camera(img, 1.03 + 0.06 * p, s["pan"][0] * (p - 0.5) * 0.8, s["pan"][1] * (p - 0.5) * 0.8)
        # 휩 트랜지션: 수평 모션블러 + 줌
        TR = 0.22
        if t < TR or t > dur - TR:
            k = (1 - eo(t / TR)) if t < TR else eio((t - (dur - TR)) / TR)
            ox = s["pan"][0] * (p - 0.5) * 0.8 + (0.25 * k if t < TR else -0.25 * k)
            frame = camera(img, 1.03 + 0.06 * p + 0.10 * k, max(-1, min(1, ox)), s["pan"][1] * (p - 0.5) * 0.8)
            frame = hblur(frame, 1 + 45 * k)
        frame.alpha_composite(self.grad)
        # 텍스트 블록 (왼쪽 아래)
        exit_k = eio((t - (dur - 0.3)) / 0.25)
        xo = -40 * exit_k
        ta = 1 - exit_k
        ty = H - BAR - 330
        # 번호 + 라인 + 키커
        a1 = eo((t - 0.2) / 0.35)
        paste(frame, c["no"], X0 - c["pad"] + xo, ty - 100 - c["pad"] + 10 * (1 - a1), alpha=a1 * ta)
        ld = ImageDraw.Draw(frame)
        lw = int(70 * eexpo((t - 0.3) / 0.5) * ta)
        if lw > 0:
            ly = ty - 64
            ld.rectangle((X0 + 82 + xo, ly, X0 + 82 + lw + xo, ly + 2), fill=AMBER + (int(230 * ta),))
        paste(frame, c["kick"], X0 + 175 - c["pad"] + xo, ty - 84 - c["pad"], alpha=eo((t - 0.4) / 0.35) * ta)
        # 타이틀: 아래에서 위로 마스크 리빌
        tt = eexpo((t - 0.3) / 0.6)
        th = c["title"].height - c["pad"] * 2
        clip = (ty, ty + th + 30)
        paste(frame, c["title"], X0 - c["pad"] + xo, ty - c["pad"] + (th + 20) * (1 - tt), alpha=ta, clip=clip)
        # 설명
        for k, dl in enumerate(c["desc"]):
            dt = t - (0.85 + k * 0.18)
            if dt > 0:
                a = eo(dt / 0.4)
                paste(frame, dl, X0 - 40 + xo, ty + th + 40 + k * 56 + 18 * (1 - a), alpha=a * ta)
        # 진행 표시 (상단 오른쪽)
        pg, _ = None, None
        flash = (1 - t / 0.08) * 0.5 if t < 0.08 else 0
        if flash > 0:
            frame.alpha_composite(Image.new("RGBA", (W, H), (255, 245, 230, int(255 * flash))))
        return self.finish(frame, fi, leak=max(0, 1 - t / 0.5) * 0.8 if i else max(0, 1 - t / 0.6), t=t + i)

    def outro(self, t, dur, fi):
        frame = self.outro_bg.copy()
        lk = light_leak(t * 0.5, 0.35)
        frame.alpha_composite(lk)
        cy = H / 2 - 30
        # 태그라인
        a = eo((t - 0.1) / 0.5)
        paste(frame, self.tag, W / 2, cy - 175 + 14 * (1 - a), alpha=a, anchor="mm")
        # 로고: 블러→선명, 스케일 다운
        lt = t - 0.25
        if lt > 0:
            k = eexpo(lt / 0.7)
            sc = 1.10 - 0.10 * k
            paste(frame, self.logo_blur, W / 2, cy, alpha=(1 - k) * min(1, lt / 0.15), anchor="mm", scale=sc)
            paste(frame, self.logo, W / 2, cy, alpha=k, anchor="mm", scale=sc)
            # 텍스트 안에서만 지나가는 빛
            sx = (lt - 0.8) * 1.4
            if 0 < sx < 1:
                lw, lh = self.logo.size
                g = np.zeros((lh, lw), np.float32)
                xs = np.arange(lw)[None, :] + np.arange(lh)[:, None] * 0.35
                cxp = -200 + sx * (lw + 400)
                g = np.clip(1 - np.abs(xs - cxp) / 70, 0, 1) * 0.85
                al = np.asarray(self.logo.getchannel("A")).astype(np.float32) / 255
                shine = np.zeros((lh, lw, 4), np.uint8)
                shine[..., 0] = 255; shine[..., 1] = 225; shine[..., 2] = 160
                shine[..., 3] = (g * al * 255).astype(np.uint8)
                paste(frame, Image.fromarray(shine, "RGBA"), W / 2, cy, anchor="mm", scale=sc)
        # 영문
        a = eo((t - 0.75) / 0.5)
        paste(frame, self.en, W / 2, cy + 185 + 10 * (1 - a), alpha=a, anchor="mm")
        # 팀명
        a = eo((t - 1.4) / 0.5)
        paste(frame, self.team, W / 2, cy + 275, alpha=a * 0.9, anchor="mm")
        # COMING SOON + 양옆 라인
        a = eo((t - 1.9) / 0.5)
        paste(frame, self.soon, W / 2, H - BAR - 95, alpha=a, anchor="mm")
        d = ImageDraw.Draw(frame)
        lw = int(180 * eexpo((t - 1.9) / 0.7))
        sw = self.soon.width / 2 - 30
        yy = H - BAR - 97
        if lw > 0:
            d.rectangle((W / 2 - sw - 30 - lw, yy, W / 2 - sw - 30, yy + 1), fill=AMBER + (200,))
            d.rectangle((W / 2 + sw + 30, yy, W / 2 + sw + 30 + lw, yy + 1), fill=AMBER + (200,))
        fl = (1 - lt / 0.12) * 0.7 if 0 < lt < 0.12 else 0
        if fl > 0:
            frame.alpha_composite(Image.new("RGBA", (W, H), (255, 245, 230, int(255 * fl))))
        fade = eio((t - dur + 0.5) / 0.5)
        if fade > 0:
            frame.alpha_composite(Image.new("RGBA", (W, H), (0, 0, 0, int(255 * fade))))
        return self.finish(frame, fi, t=t)


# ------------------------------------------------------------------ 음악
SR = 44100
NOTE = {n: i for i, n in enumerate(["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"])}


def mn(s): return 12 * (int(s[-1]) + 1) + NOTE[s[:-1]]
def mf(m): return 440 * 2 ** ((m - 69) / 12)


def sos(kind, fc, order=2):
    from scipy.signal import butter
    return butter(order, fc, btype=kind, fs=SR, output="sos")


def filt(x, kind, fc, order=2):
    from scipy.signal import sosfilt
    return sosfilt(sos(kind, fc, order), x)


def env(n, a, d, s, r, hold):
    a, d, r = int(a * SR), int(d * SR), int(r * SR)
    sl = max(0, int(hold * SR) - a - d)
    e = np.concatenate([np.linspace(0, 1, a, False), np.linspace(1, s, d, False), np.full(sl, s), np.linspace(s, 0, r)])
    return e[:n] if len(e) >= n else np.pad(e, (0, n - len(e)))


def saw(f, n, cents=(0,), seed=0, vib=0.0):
    t = np.arange(n) / SR
    rng = np.random.default_rng(seed)
    out = np.zeros(n)
    for c in cents:
        ff = f * 2 ** (c / 1200) * (1 + vib * np.sin(2 * np.pi * (5 + rng.random()) * t + rng.random() * 6))
        ph = np.cumsum(ff) / SR + rng.random()
        out += 2 * (ph % 1) - 1
    return out / len(cents)


def put(buf, x, t0, gain=1.0):
    i = int(t0 * SR)
    if i >= len(buf): return
    e = min(len(buf), i + len(x))
    buf[i:e] += x[:e - i] * gain


def strings(notes, dur, amp, seed):
    n = int((dur + 0.8) * SR)
    x = sum(saw(mf(m), n, (-11, -4, 3, 10), seed + m, 0.003) for m in notes)
    x = filt(x, "low", 2000)
    return x * env(n, 0.35, 0.3, 0.9, 0.8, dur) * amp


def choir(notes, dur, amp, seed):
    n = int((dur + 1.0) * SR)
    src = sum(saw(mf(m), n, (-8, 0, 8), seed + m, 0.006) for m in notes)
    x = sum(filt(filt(src, "high", f * 0.85, 1), "low", f * 1.15, 1) * g for f, g in [(800, 1), (1150, 0.6), (2900, 0.25)])
    return x * env(n, 0.6, 0.4, 0.9, 1.0, dur) * amp


def brass(m, dur, amp):
    n = int((dur + 0.5) * SR)
    t = np.arange(n) / SR
    f = mf(m) * (1 + 0.005 * np.sin(2 * np.pi * 5.2 * t) * np.clip(t / 0.4, 0, 1))
    ph = 2 * np.pi * np.cumsum(f) / SR
    x = sum(np.sin(ph * k) / k ** 1.05 for k in range(1, 14))
    # 필터가 열리는 브라스 어택
    bright = filt(x, "low", 3200)
    dark = filt(x, "low", 900)
    mixk = np.clip(t / 0.12, 0, 1)
    x = dark * (1 - mixk * 0.7) + bright * mixk * 0.7
    return x * env(n, 0.07, 0.2, 0.8, 0.4, dur) * amp


def braam(dur, amp=0.5):
    n = int((dur + 0.8) * SR)
    t = np.arange(n) / SR
    x = sum(saw(mf(mn(s)), n, (-12, 0, 12), k) for k, s in enumerate(["D1", "D2", "A2", "D3", "F3"]))
    out = np.zeros(n)
    blk = 2048
    for i in range(0, n, blk):  # 서서히 열리는 필터
        fc = 180 + 1800 * min(1, (i / SR) / 0.5) * math.exp(-max(0, i / SR - 0.5) * 0.8)
        out[i:i + blk] = filt(x[i:i + blk], "low", fc, 1)
    return out * env(n, 0.02, 0.4, 0.75, 0.8, dur) * amp


def taiko(amp=1.0, f0=100, f1=46, dec=6, seed=0):
    n = int(0.9 * SR); t = np.arange(n) / SR
    f = f1 + (f0 - f1) * np.exp(-t * 20)
    body = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * dec)
    skin = filt(np.random.default_rng(seed).standard_normal(n), "low", 1500) * np.exp(-t * 35) * 0.5
    return (body + skin) * amp


def snare(amp, seed):
    n = int(0.25 * SR); t = np.arange(n) / SR
    x = filt(np.random.default_rng(seed).standard_normal(n), "band", (1500, 6000)) * np.exp(-t * 22)
    return x * amp


def impact(seed):
    n = int(2.5 * SR); t = np.arange(n) / SR
    rng = np.random.default_rng(seed)
    sub = np.sin(2 * np.pi * np.cumsum(36 + 60 * np.exp(-t * 10)) / SR) * np.exp(-t * 2.0)
    crash = filt(rng.standard_normal(n), "high", 4000) * np.exp(-t * 2.5) * 0.25
    body = filt(rng.standard_normal(n), "low", 300) * np.exp(-t * 6) * 0.7
    return sub * 1.2 + crash + body


def whoosh(sec, seed):
    n = int(sec * SR)
    x = np.random.default_rng(seed).standard_normal(n)
    out = np.zeros(n); steps = 30
    for k in range(steps):
        a, b = k * n // steps, (k + 1) * n // steps
        out[a:b] = filt(x[a:b], "band", (300 + 2500 * k / steps, 900 + 7000 * k / steps), 1)
    return out * np.sin(np.linspace(0, np.pi, n)) ** 2 * np.linspace(0.3, 1, n)


def reverb(x, sec, wet, seed):
    from scipy.signal import fftconvolve
    n = int(sec * SR)
    ir = np.random.default_rng(seed).standard_normal(n) * np.exp(-np.arange(n) / SR * (6.9 / sec))
    ir = filt(ir, "low", 6000); ir /= np.sqrt((ir ** 2).sum())
    return x * (1 - wet) + fftconvolve(x, ir)[:len(x)] * wet * 1.3


CHORDS = [("D", 3), ("A#", 4), ("F", 4), ("C", 4)]  # (근음, 장/단 구분용 3=단3도)


def triad(root, third, octv):
    r = mn(root + str(octv)); return [r, r + third, r + 7]


MELODY = [[("A4", 1), ("D5", .5), ("E5", .5), ("F5", 2)],
          [("F5", 1), ("D5", 1), ("A#4", 2)],
          [("A4", 1), ("C5", 1), ("F5", 1), ("G5", 1)],
          [("A5", 2.5), ("G5", .5), ("E5", 1)]]


def make_music(tl, total, path):
    N = int((total + 3) * SR)
    mus, drm = np.zeros(N), np.zeros(N)
    s0, out_t = tl[1][2], tl[-1][2]
    # 인트로: 저음 현 + 합창 + 상승
    put(mus, strings([mn("D2"), mn("A2"), mn("D3")], s0, 0.10, 1), 0)
    put(mus, choir([mn("D4"), mn("A4")], s0, 0.05, 2), 0.2)
    put(drm, whoosh(s0, 4), 0, 0.45)
    put(drm, taiko(0.6, 70, 40, 3, 5), 0.0)
    bar = 4 * BEAT
    nb = int(math.ceil((out_t - s0) / bar))
    for b in range(nb):
        t0 = s0 + b * bar
        root, third = CHORDS[b % 4]
        bl = min(bar, out_t - t0)
        put(mus, strings(triad(root, third, 3) + [triad(root, third, 4)[0]], bl, 0.075, b), t0)
        put(mus, choir(triad(root, third, 4), bl, 0.035, 10 + b), t0)
        # 베이스 오스티나토 (8분)
        for k in range(int(bl / (BEAT / 2) + 0.01)):
            n = int(0.25 * SR)
            x = filt(saw(mf(mn(root + "2")), n, (-5, 5), k), "low", 450) * env(n, 0.004, 0.12, 0.45, 0.08, 0.2)
            put(mus, x, t0 + k * BEAT / 2, 0.20)
        # 현 스타카토 16분
        cn = triad(root, third, 4); pat = [cn[0], cn[2], cn[1], cn[2]]
        for k in range(int(bl / (BEAT / 4) + 0.01)):
            n = int(0.16 * SR)
            x = filt(saw(mf(pat[k % 4]), n, (-7, 7), k + b), "low", 3500) * env(n, 0.003, 0.09, 0, 0.04, 0.1)
            put(mus, x, t0 + k * BEAT / 4, 0.06 * (1 + 0.4 * (k % 4 == 0)))
        # 타악: 타이코 + 스네어
        for k, a in [(0, 1.0), (3, 0.55), (4, 0.8), (6, 0.65), (7, 0.5)]:
            if k * BEAT / 2 < bl - 0.01:
                put(drm, taiko(a, seed=b * 9 + k), t0 + k * BEAT / 2, 0.55)
        for k in (2, 6):
            if k * BEAT / 2 < bl - 0.01:
                put(drm, snare(0.25, b * 5 + k), t0 + k * BEAT / 2)
        # 금관 멜로디 (2마디째부터)
        if b >= 1:
            tt = t0
            for note, beats in MELODY[(b - 1) % 4]:
                if tt - t0 < bl - 0.01:
                    d = min(beats * BEAT * 0.95, out_t - tt)
                    put(mus, brass(mn(note), d, 0.22), tt)
                    put(mus, brass(mn(note) - 12, d, 0.14), tt)
                tt += beats * BEAT
    # 아웃트로 직전 스네어 롤
    for k in range(16):
        tr = out_t - BEAT * 2 + k * BEAT / 8
        put(drm, snare(0.08 + 0.3 * k / 16, 200 + k), tr)
    # 장면 전환: 휩 + 임팩트
    for kind, arg, s, e in tl[1:]:
        put(drm, whoosh(0.35, int(s * 7)), s - 0.3, 0.35)
        put(drm, impact(int(s * 11)), s, 0.55 if kind == "scene" else 0.9)
    # 아웃트로: 브라암 + 최종 화음
    od = total - out_t
    put(mus, braam(od * 0.7, 0.32), out_t + 0.25)
    put(mus, strings(triad("D", 3, 3) + triad("D", 3, 4) + [mn("D2")], od, 0.09, 77), out_t + 0.25)
    put(mus, choir(triad("D", 3, 4) + [mn("D5")], od, 0.05, 78), out_t + 0.25)
    put(mus, brass(mn("D5"), od * 0.8, 0.25), out_t + 0.25)
    put(mus, brass(mn("A4"), od * 0.8, 0.18), out_t + 0.25)
    put(drm, taiko(1.4, 80, 38, 2.5, 9), out_t + 0.25)
    L = reverb(mus, 2.8, 0.38, 11) + reverb(drm, 1.8, 0.2, 12)
    Rr = reverb(mus, 2.8, 0.38, 21) + reverb(drm, 1.8, 0.2, 22)
    st = np.stack([L, Rr], 1)[:int(total * SR)]
    fade = int(0.7 * SR); st[-fade:] *= np.linspace(1, 0, fade)[:, None]
    st = np.tanh(st / np.abs(st).max() * 1.5) * 0.92
    with wave.open(path, "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((st * 32767).astype(np.int16).tobytes())


# ------------------------------------------------------------------ 메인
def main():
    tl, total = timeline()
    mdir = os.path.join(OUT, "음악"); os.makedirs(mdir, exist_ok=True)
    wav = os.path.join(mdir, "말파이트_BGM_15초.wav")
    print("음악 합성...", flush=True)
    make_music(tl, total, wav)
    ff = imageio_ffmpeg.get_ffmpeg_exe()
    subprocess.run([ff, "-y", "-loglevel", "error", "-i", wav, "-b:a", "320k", wav[:-4] + ".mp3"], check=True)
    tmp = os.path.join(OUT, "_tmp.mp4")
    p = subprocess.Popen([ff, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                          "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "slow", "-crf", "15",
                          "-pix_fmt", "yuv420p", tmp], stdin=subprocess.PIPE)
    r = R()
    nf = int(round(total * FPS))
    for fi in range(nf):
        t = fi / FPS
        for kind, arg, s, e in tl:
            if s <= t < e or (kind == "outro" and t >= s):
                lt, d = t - s, e - s
                fr = r.intro(lt, d, fi) if kind == "intro" else r.scene(arg, lt, d, fi) if kind == "scene" else r.outro(lt, d, fi)
                break
        p.stdin.write(fr.convert("RGB").tobytes())
        if fi % 45 == 0:
            print(f"  {fi}/{nf}", flush=True)
    p.stdin.close(); p.wait()
    final = os.path.join(OUT, "말파이트_티저_15초.mp4")
    subprocess.run([ff, "-y", "-loglevel", "error", "-i", tmp, "-i", wav, "-c:v", "copy", "-c:a", "aac", "-b:a", "256k",
                    "-shortest", "-movflags", "+faststart", final], check=True)
    os.remove(tmp)
    print("완료:", final)


if __name__ == "__main__":
    main()
