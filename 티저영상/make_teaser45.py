# -*- coding: utf-8 -*-
"""승마 레이싱 & 육성 RPG — 45초 본편 티저 (모션그래픽) + BGM.
python make_teaser45.py            전체 렌더
python make_teaser45.py preview    프레임 미리보기 PNG만
"""
import math, os, random, subprocess, sys, wave
import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont
import imageio_ffmpeg

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
FD = os.path.join(HERE, "fonts")
W, H, FPS = 1920, 1080, 30
BPM = 120
BEAT = 60 / BPM
TR = 0.4  # 전환 길이

PF = {k: os.path.join(FD, f"Pretendard-{k}.otf") for k in ("Light", "Regular", "SemiBold", "Bold", "ExtraBold")}

# ------------------------------------------------------------------ 장면 구성
# pos: tl/tr/bl/br/c/cl/split   mode: word/char/type   tr: 이 장면으로 들어오는 전환
SCENES = [
    dict(img="1장 수정본.png", kicker="MEET YOUR HORSE", light="오늘부터", bold="당신의 말입니다",
         desc="직접 키우고, 직접 달린다", pos="tl", mode="word", tr="circle", pan=(-1, 0)),
    dict(img="2장 수정본.png", kicker="RACING SYSTEM", light="직접 키운 말로 달리는", bold="레이싱 시스템",
         desc="승마만의 독특한 레이싱 감각", pos="c", mode="char", tr="whip", pan=(1, -0.3)),
    dict(img="3장.png", kicker="MULTIPLAYER RACE", light="다인 실시간 대전", bold="멀티 레이싱",
         desc="몸싸움으로 만드는 승부의 변수", pos="split", mode="word", tr="whipL", pan=(-1, 0.2)),
    dict(img="4장.png", kicker="OBSTACLES & COURSES", light="특색있는 장애물과", bold="다양한 코스",
         desc="반복 숙달과 말의 성장", pos="br", mode="word", tr="zoom", pan=(0, 1), shake=True),
    dict(img="5장.png", kicker="VILLAGE", light="육성 컨텐츠의 허브", bold="마을",
         desc="밥먹이기  ·  상호작용  ·  커뮤니티", pos="tl", mode="type", tr="flash", pan=(-1, 0)),
    dict(img="6장.png", kicker="GROWTH", light="선택에 따라 달라지는", bold="능력치 성장",
         desc="상호작용으로 키우는 재미", pos="cl", mode="char", tr="wipe", pan=(1, 0)),
    dict(img="7장.png", kicker="CUSTOMIZE", light="나만의 스타일로", bold="말 꾸미기",
         desc="꾸밀수록 깊어지는 애착", pos="tr", mode="word", tr="circle", pan=(0, -1), scrim=0.75),
    dict(img="8장.png", kicker="BREEDING", light="능력치를 물려받는", bold="교배 시스템",
         desc="나만의 독특한 말 생성", pos="bl", mode="char", tr="flash", pan=(-1, 0)),
    dict(img="9장.png", kicker="CONTROL", light="타이밍을 읽고", bold="직접 조작해서 극복",
         desc="한 번 무너졌던 그 장애물 앞에서", pos="split", mode="type", tr="whip", pan=(0, 1), scrim=0.75),
    dict(img="10장.png", kicker="GAME MODES", light="솔로  ·  AI  ·  PVP", bold="플레이 방식 선택",
         desc="코스 숙달부터 실전 레이싱까지", pos="c", mode="word", tr="zoom", pan=(1, 0), scrim=0.8),
    dict(img="11장.png", kicker="REWARDS", light="레이싱과 마을을 잇는", bold="순위 보상",
         desc="보상으로 다시 육성과 치장", pos="tr", mode="char", tr="wipe", pan=(-1, 0)),
    dict(img="12장.png", kicker="GROW TOGETHER", light="처음엔 그냥 말이었는데", bold="이제는 나만의 말",
         desc="말의 성장과 내 실력이 함께 만드는 재미", pos="tl", mode="word", tr="circle", pan=(0, -1)),
]
INTRO, SCENE, OUTRO = 6 * BEAT, 6 * BEAT, 12 * BEAT  # 3s + 12×3s + 6s = 45s


def timeline():
    tl, t = [("intro", None, 0.0, INTRO)], INTRO
    for i in range(len(SCENES)):
        tl.append(("scene", i, t, t + SCENE)); t += SCENE
    tl.append(("outro", None, t, t + OUTRO))
    return tl, t + OUTRO


# ------------------------------------------------------------------ 유틸
_fc = {}


def font(w, sz):
    k = (w, sz)
    if k not in _fc:
        _fc[k] = ImageFont.truetype(PF[w], sz)
    return _fc[k]


def eo(x): x = min(1, max(0, x)); return 1 - (1 - x) ** 3
def eio(x): x = min(1, max(0, x)); return x * x * (3 - 2 * x)
def ex(x): x = min(1, max(0, x)); return 1 if x >= 1 else 1 - 2 ** (-10 * x)


def with_alpha(lay, a):
    if a >= 0.999: return lay
    l = lay.copy(); l.putalpha(lay.getchannel("A").point(lambda v: int(v * a))); return l


# ------------------------------------------------------------------ 텍스트 블록
class TextBlock:
    """kicker / light / bold(+커서 점) / desc 를 글자 단위로 배치하고 등장·퇴장 애니메이션"""
    PAD = 24

    def __init__(self, sc, theme="photo", seed=0):
        self.mode = sc.get("mode", "word")
        dark = theme == "white"
        C = dict(kicker=(200, 135, 30) if dark else (255, 200, 110),
                 light=(140, 140, 146) if dark else (232, 232, 232),
                 bold=(18, 18, 22) if dark else (255, 255, 255),
                 desc=(110, 110, 116) if dark else (238, 238, 238))
        self.dot_col = (230, 150, 40) if dark else (255, 196, 90)
        self.shadow = not dark
        bsz = sc.get("bsize", 108)
        spec = []
        if sc.get("kicker"): spec.append(("kicker", sc["kicker"], font("SemiBold", 28), C["kicker"], 7))
        if sc.get("light"): spec.append(("light", sc["light"], font("Light", 50), C["light"], 0))
        if sc.get("bold"): spec.append(("bold", sc["bold"], font("Bold", bsz), C["bold"], -2))
        if sc.get("desc"): spec.append(("desc", sc["desc"], font("Regular", 34), C["desc"], 1))
        gaps = dict(kicker=18, light=6, bold=22, desc=0)
        pos = sc.get("pos", "tl")
        rng = random.Random(seed)
        self.chars = []  # dict(lay, blur, x, y, line, word)
        self.lines = {}
        # 줄 크기 계산
        info = []
        for name, txt, f, col, trk in spec:
            ws = [f.getlength(c) for c in txt]
            lw = sum(ws) + trk * (len(txt) - 1)
            asc, dsc = f.getmetrics()
            info.append((name, txt, f, col, trk, ws, lw, asc + dsc))
        total_h = sum(i[7] + gaps[i[0]] for i in info)
        X = dict(tl=150, cl=150, bl=150, tr=W - 150, br=W - 150, c=W / 2, split=W / 2)[pos]
        Y = dict(tl=150, tr=150, cl=(H - total_h) / 2, c=(H - total_h) / 2, split=(H - total_h) / 2 - 20,
                 bl=H - 150 - total_h, br=H - 150 - total_h)[pos]
        align = "left" if pos in ("tl", "cl", "bl") else "right" if pos in ("tr", "br") else "center"
        y = Y
        if pos == "split":  # light | bold 가 한 줄, 가운데 기준 좌우
            lt = next(i for i in info if i[0] == "light"); bd = next(i for i in info if i[0] == "bold")
            rest = [i for i in info if i[0] not in ("light", "bold")]
            row_h = bd[7]
            ky = (H - row_h) / 2 - 70
            for it in rest:
                if it[0] == "kicker": self._place(it, W / 2 - it[6] / 2, ky)
            self._place(lt, W / 2 - 40 - lt[6], (H - row_h) / 2 + (bd[7] - lt[7]) * 0.62)
            self._place(bd, W / 2 + 40, (H - row_h) / 2)
            for it in rest:
                if it[0] == "desc": self._place(it, W / 2 - it[6] / 2, (H + row_h) / 2 + 26)
        else:
            for it in info:
                x = X if align == "left" else X - it[6] if align == "right" else X - it[6] / 2
                self._place(it, x, y)
                y += it[7] + gaps[it[0]]
        for c in self.chars:
            c["sx"], c["sy"] = rng.uniform(-1, 1), rng.uniform(-1, 0.6)
            c["sd"] = rng.uniform(0, 0.14)
        xs = [c["x"] for c in self.chars] + [c["x"] + c["lay"].width for c in self.chars]
        ys = [c["y"] for c in self.chars] + [c["y"] + c["lay"].height for c in self.chars]
        self.bbox = (int(min(xs)) - 60, int(min(ys)) - 60, int(max(xs)) + 120, int(max(ys)) + 60)
        self._schedule()

    def _place(self, it, x0, y0):
        name, txt, f, col, trk, ws, lw, lh = it
        P = self.PAD
        x, word = x0, 0
        idxs = []
        for ch, w in zip(txt, ws):
            if ch == " ":
                word += 1; x += w + trk; continue
            lay = Image.new("RGBA", (int(w) + P * 2 + 4, lh + P * 2), (0, 0, 0, 0))
            ImageDraw.Draw(lay).text((P, P), ch, font=f, fill=col + (255,))
            self.chars.append(dict(lay=lay, blur=lay.filter(ImageFilter.GaussianBlur(7)), x=x - P, y=y0 - P,
                                   line=name, word=word, w=w))
            idxs.append(len(self.chars) - 1)
            x += w + trk
        self.lines[name] = dict(idx=idxs, end=x, y=y0, h=lh, f=f)

    def _schedule(self, t0=0.0):
        m = self.mode
        t = t0
        for name in ("kicker", "light", "bold", "desc"):
            if name not in self.lines: continue
            idx = self.lines[name]["idx"]
            if name in ("kicker", "desc"):  # 통째로 페이드
                for i in idx: self.chars[i]["ta"] = t
                t += 0.18 if name == "kicker" else 0
                continue
            if m == "word":
                step = 0.06 if name == "light" else 0.10
                for i in idx: self.chars[i]["ta"] = t + self.chars[i]["word"] * step
                t += (max(self.chars[i]["word"] for i in idx) + 1) * step + 0.05
            else:
                step = 0.025 if m == "char" else 0.04
                if name == "light": step *= 0.8
                for k, i in enumerate(idx): self.chars[i]["ta"] = t + k * step
                t += len(idx) * step + 0.05
        self.reveal_end = t

    def render(self, frame, t, t_exit, ox=0, oy=0):
        """t: 블록 시작 기준 시간. t_exit: 퇴장 시작 시각"""
        x0, y0, x1, y1 = self.bbox
        lay = Image.new("RGBA", (x1 - x0, y1 - y0), (0, 0, 0, 0))
        last_bold = None
        any_drawn = False
        for c in self.chars:
            ta = c.get("ta", 0)
            if t < ta: continue
            a = eo((t - ta) / (0.12 if self.mode == "type" else 0.3))
            dy = 0 if self.mode == "type" else 22 * (1 - a)
            bl = 0 if self.mode == "type" else 1 - a
            dx = 0
            if c["line"] in ("kicker", "desc"):
                a = eo((t - ta) / 0.45); dy = 12 * (1 - a); bl = 0
            # 퇴장: 흩어지며 블러
            e = eo((t - t_exit - c["sd"]) / 0.35) if t > t_exit else 0
            if e > 0:
                a *= 1 - e; dx += c["sx"] * 60 * e; dy += c["sy"] * 40 * e; bl = max(bl, e)
            if a <= 0.01: continue
            any_drawn = True
            px, py = int(c["x"] - x0 + dx + ox), int(c["y"] - y0 + dy + oy)
            if bl > 0.02:
                lay.alpha_composite(with_alpha(c["blur"], a * bl), (px, py))
            if bl < 0.98:
                lay.alpha_composite(with_alpha(c["lay"], a * (1 - bl)), (px, py))
            if c["line"] == "bold" and t < t_exit + 0.1:
                last_bold = c
        # 커서 (점 또는 타이핑 바)
        if "bold" in self.lines and last_bold is not None:
            L = self.lines["bold"]
            fa = 1 - eo((t - t_exit) / 0.2) if t > t_exit else 1
            cx = last_bold["x"] + self.PAD + last_bold["w"] + (16 if self.mode != "type" else 10) - x0 + ox
            cy = L["y"] - y0 + oy
            d = ImageDraw.Draw(lay)
            col = self.dot_col + (int(255 * fa),)
            if self.mode == "type":
                if int(t * 3) % 2 == 0 or t < self.reveal_end:
                    d.rectangle((cx, cy + L["h"] * 0.18, cx + 6, cy + L["h"] * 0.86), fill=col)
            else:
                r = L["h"] * 0.075
                cyy = cy + L["h"] * 0.70
                d.ellipse((cx, cyy - r, cx + 2 * r, cyy + r), fill=col)
        if not any_drawn: return
        if self.shadow:
            sh = Image.new("RGBA", lay.size, (0, 0, 0, 0))
            sh.putalpha(lay.getchannel("A").filter(ImageFilter.GaussianBlur(14)).point(lambda v: int(v * 0.6)))
            frame.alpha_composite(sh, (x0, y0 + 5))
        frame.alpha_composite(lay, (x0, y0))


# ------------------------------------------------------------------ 이미지
_big = {}


def graded(name):
    if name not in _big:
        im = Image.open(os.path.join(ROOT, name)).convert("RGB")
        im = ImageEnhance.Contrast(im).enhance(1.08)
        im = ImageEnhance.Color(im).enhance(0.94)
        im = im.resize((im.width * 2, im.height * 2), Image.LANCZOS).filter(ImageFilter.UnsharpMask(2.2, 70, 2))
        _big[name] = im
    return _big[name]


def camera(img, s, ox, oy):
    sw, sh = img.size
    cw = sw / s; ch = cw * H / W
    if ch > sh / s: ch = sh / s; cw = ch * W / H
    cx = sw / 2 + max(-1, min(1, ox)) * (sw - cw) / 2
    cy = sh / 2 + max(-1, min(1, oy)) * (sh - ch) / 2
    return img.resize((W, H), Image.BICUBIC, box=(cx - cw / 2, cy - ch / 2, cx + cw / 2, cy + ch / 2)).convert("RGBA")


def hblur(img, k):
    if k < 1.5: return img
    return img.resize((max(8, int(W / k)), H), Image.BILINEAR).resize((W, H), Image.BILINEAR)


YY, XX = np.mgrid[0:H, 0:W].astype(np.float32)
DIST_C = np.sqrt((XX - W / 2) ** 2 + (YY - H / 2) ** 2)
DIAG = (XX + YY * 0.6) / (W + H * 0.6)


def scrim_for(bbox, strength=0.55):
    x0, y0, x1, y1 = bbox
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    rx, ry = (x1 - x0) / 2 + 380, (y1 - y0) / 2 + 260
    d = np.sqrt(((XX - cx) / rx) ** 2 + ((YY - cy) / ry) ** 2)
    a = np.clip(1 - d, 0, 1) ** 0.9 * strength
    vx = (XX / W - 0.5) * 2; vy = (YY / H - 0.5) * 2
    a = np.clip(a + np.clip((np.sqrt(vx ** 2 * 0.7 + vy ** 2) - 0.8) / 0.6, 0, 1) * 0.45, 0, 0.85)
    arr = np.zeros((H, W, 4), np.uint8); arr[..., 3] = (a * 255).astype(np.uint8)
    return Image.fromarray(arr, "RGBA")


def mask_img(arr):
    return Image.fromarray((np.clip(arr, 0, 1) * 255).astype(np.uint8), "L")


# ------------------------------------------------------------------ 렌더러
BG_WHITE = (247, 247, 249)


class Renderer:
    def __init__(self):
        self.blocks, self.scrims = [], []
        for i, s in enumerate(SCENES):
            b = TextBlock(s, "photo", seed=i + 1)
            self.blocks.append(b); self.scrims.append(scrim_for(b.bbox, s.get("scrim", 0.62)))
        self.intro_block = TextBlock(dict(light="어느 날,", bold="당신에게 말 한 마리가 도착했다", pos="cl", mode="word",
                                          bsize=96), "white", seed=99)
        self.outro_block = TextBlock(dict(bold="승마 레이싱 & 육성 RPG", pos="c", mode="char", bsize=120), "white", seed=98)
        self.team = TextBlock(dict(desc="김경준  ·  정진영  ·  강석주", pos="c"), "white", seed=97)
        f = font("Regular", 34)
        self.soon_f = f

    # -- 장면들 (전환 없이 단독 프레임) --
    def intro_frame(self, t, dur):
        fr = Image.new("RGBA", (W, H), BG_WHITE + (255,))
        self.intro_block.render(fr, t - 0.25, dur - 0.75)
        return fr

    def scene_frame(self, i, t, dur, text=True):
        s = SCENES[i]
        p = t / dur
        sx = sy = 0
        if s.get("shake") and 0.35 < t < 1.0:
            k = (1.0 - t) / 0.65; r = random.Random(int(t * 1000))
            sx, sy = r.uniform(-1, 1) * 0.05 * k, r.uniform(-1, 1) * 0.05 * k
        fr = camera(graded(s["img"]), 1.04 + 0.07 * p, s["pan"][0] * (p - 0.5) * 0.8 + sx, s["pan"][1] * (p - 0.5) * 0.8 + sy)
        fr.alpha_composite(self.scrims[i])
        if text:
            self.blocks[i].render(fr, t - 0.25, dur - 0.5 - 0.25)
        return fr

    def outro_frame(self, t, dur):
        fr = Image.new("RGBA", (W, H), BG_WHITE + (255,))
        ob = self.outro_block
        # 메인 타이틀은 살짝 위로
        ob.render(fr, t - 0.5, 99, oy=-90)
        self.team.render(fr, t - 1.6, 99, oy=40)
        # Coming Soon 입력창 (타이핑)
        ct = t - 2.4
        if ct > 0:
            a = eo(ct / 0.4)
            bw, bh = 520, 76
            bx, by = W / 2 - bw / 2, H / 2 + 150 + 16 * (1 - a)
            box = Image.new("RGBA", (bw + 60, bh + 60), (0, 0, 0, 0))
            sh = Image.new("RGBA", box.size, (0, 0, 0, 0))
            ImageDraw.Draw(sh).rounded_rectangle((30, 36, 30 + bw, 36 + bh), bh / 2, fill=(0, 0, 0, 40))
            box.alpha_composite(sh.filter(ImageFilter.GaussianBlur(12)))
            d = ImageDraw.Draw(box)
            d.rounded_rectangle((30, 30, 30 + bw, 30 + bh), bh / 2, fill=(255, 255, 255, 255), outline=(225, 225, 230, 255), width=2)
            txt = "Coming Soon"
            n = int(max(0, ct - 0.45) / 0.09)
            shown = txt[:n]
            d.text((30 + 40, 30 + bh / 2), shown, font=self.soon_f, fill=(30, 30, 34, 255), anchor="lm")
            cx = 30 + 40 + self.soon_f.getlength(shown) + 4
            if n < len(txt) or int(ct * 2.2) % 2 == 0:
                d.rectangle((cx, 30 + bh / 2 - 18, cx + 3, 30 + bh / 2 + 18), fill=(30, 30, 34, 255))
            # 전송 버튼
            done = n >= len(txt)
            bc = (20, 20, 24, 255) if done else (205, 205, 210, 255)
            ccx, ccy, r = 30 + bw - bh / 2, 30 + bh / 2, 22
            d.ellipse((ccx - r, ccy - r, ccx + r, ccy + r), fill=bc)
            d.polygon([(ccx, ccy - 10), (ccx - 8, ccy), (ccx + 8, ccy)], fill=(255, 255, 255, 255))
            d.rectangle((ccx - 2, ccy - 2, ccx + 2, ccy + 10), fill=(255, 255, 255, 255))
            fr.alpha_composite(with_alpha(box, a), (int(bx - 30), int(by - 30)))
        fade = eio((t - dur + 0.7) / 0.7)
        if fade > 0:
            fr.alpha_composite(Image.new("RGBA", (W, H), (0, 0, 0, int(255 * fade))))
        return fr

    def seg_frame(self, seg, t, text=True):
        kind, arg, s, e = seg
        d = e - s
        if kind == "intro": return self.intro_frame(t, d)
        if kind == "scene": return self.scene_frame(arg, t, d, text)
        return self.outro_frame(t, d)

    # -- 전환 합성 --
    def transition(self, kind, out_fr, in_fr, k):
        if kind == "circle":
            r = ex(k) * math.hypot(W, H) / 2 + 2
            m = mask_img((r - DIST_C) / 30)
            o = out_fr.copy(); o.paste(in_fr, (0, 0), m)
            # 링 하이라이트
            if k < 0.9:
                ring = mask_img(1 - np.abs(DIST_C - r) / 6).point(lambda v: int(v * 0.6 * (1 - k)))
                o.paste(Image.new("RGBA", (W, H), (255, 255, 255, 255)), (0, 0), ring)
            return o
        if kind in ("whip", "whipL"):
            sgn = 1 if kind == "whip" else -1
            kk = eio(k)
            off_o = int(-sgn * W * 0.35 * kk); off_i = int(sgn * W * 0.35 * (1 - kk))
            bo, bi = hblur(out_fr, 1 + 50 * kk), hblur(in_fr, 1 + 50 * (1 - kk))
            o = Image.new("RGBA", (W, H), (0, 0, 0, 255))
            o.alpha_composite(bo, (off_o, 0)) if off_o >= 0 else o.alpha_composite(bo.crop((-off_o, 0, W, H)), (0, 0))
            bi_al = with_alpha(bi, min(1, kk * 1.6))
            if off_i >= 0: o.alpha_composite(bi_al.crop((0, 0, W - off_i, H)), (off_i, 0))
            else: o.alpha_composite(bi_al.crop((-off_i, 0, W, H)), (0, 0))
            return o
        if kind == "zoom":
            kk = eio(k)
            so = 1 + 0.35 * kk
            o = out_fr.resize((int(W * so), int(H * so)), Image.BILINEAR)
            o = o.crop(((o.width - W) // 2, (o.height - H) // 2, (o.width - W) // 2 + W, (o.height - H) // 2 + H))
            o = o.filter(ImageFilter.GaussianBlur(12 * kk))
            si = 1.18 - 0.18 * kk
            i = in_fr.resize((int(W * si), int(H * si)), Image.BILINEAR)
            i = i.crop(((i.width - W) // 2, (i.height - H) // 2, (i.width - W) // 2 + W, (i.height - H) // 2 + H))
            if kk < 0.9: i = i.filter(ImageFilter.GaussianBlur(10 * (1 - kk)))
            return Image.blend(o, i, kk)
        if kind == "flash":
            wf = Image.new("RGBA", (W, H), (255, 250, 242, 255))
            if k < 0.45: return Image.blend(out_fr, wf, eio(k / 0.45))
            return Image.blend(wf, in_fr, eio((k - 0.45) / 0.55))
        if kind == "wipe":
            edge = ex(k) * 1.3 - 0.15
            m = mask_img((edge - DIAG) / 0.05)
            o = out_fr.copy(); o.paste(in_fr, (0, 0), m)
            line = mask_img(1 - np.abs(DIAG - edge) / 0.004).point(lambda v: int(v * 0.8))
            o.paste(Image.new("RGBA", (W, H), (255, 220, 150, 255)), (0, 0), line)
            return o
        if kind == "white":
            return Image.blend(out_fr, in_fr, eio(k))
        return in_fr

    def frame(self, tl, t):
        for idx, seg in enumerate(tl):
            kind, arg, s, e = seg
            if s <= t < e or (idx == len(tl) - 1 and t >= s):
                lt = t - s
                cur = self.seg_frame(seg, lt)
                if idx > 0 and lt < TR:
                    prev = tl[idx - 1]
                    out_fr = self.seg_frame(prev, prev[3] - prev[2] + lt, text=False) if prev[0] == "scene" else \
                        self.seg_frame(prev, prev[3] - prev[2] + lt)
                    tk = SCENES[arg]["tr"] if kind == "scene" else "white"
                    cur = self.transition(tk, out_fr, cur, lt / TR)
                return cur


# ------------------------------------------------------------------ 음악 (10초 샘플 스타일)
SR = 44100
NOTE = {n: i for i, n in enumerate(["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"])}
def mn(s): return 12 * (int(s[-1]) + 1) + NOTE[s[:-1]]
def mf(m): return 440 * 2 ** ((m - 69) / 12)


def filt(x, kind, fc, order=2):
    from scipy.signal import butter, sosfilt
    return sosfilt(butter(order, fc, btype=kind, fs=SR, output="sos"), x)


def env(n, a, d, s, r, hold):
    a, d, r = int(a * SR), int(d * SR), int(r * SR)
    sl = max(0, int(hold * SR) - a - d)
    e = np.concatenate([np.linspace(0, 1, a, False), np.linspace(1, s, d, False), np.full(sl, s), np.linspace(s, 0, r)])
    return e[:n] if len(e) >= n else np.pad(e, (0, n - len(e)))


def saw(f, n, det=(0,), seed=0):
    t = np.arange(n) / SR; rng = np.random.default_rng(seed); out = np.zeros(n)
    for c in det:
        out += 2 * ((t * f * 2 ** (c / 1200) + rng.random()) % 1) - 1
    return out / len(det)


def put(buf, x, t0, g=1.0):
    i = int(t0 * SR)
    if i >= len(buf) or i < 0: return
    e = min(len(buf), i + len(x)); buf[i:e] += x[:e - i] * g


def pad(notes, dur, amp, seed):
    n = int((dur + 0.6) * SR)
    x = sum(saw(mf(m), n, (-9, 0, 8), seed + m) for m in notes)
    return filt(x, "low", 2200) * env(n, 0.25, 0.3, 0.85, 0.6, dur) * amp


def brass(m, dur, amp):
    n = int((dur + 0.4) * SR); t = np.arange(n) / SR
    f = mf(m) * (1 + 0.004 * np.sin(2 * np.pi * 5.5 * t) * np.clip(t / 0.3, 0, 1))
    ph = 2 * np.pi * np.cumsum(f) / SR
    x = filt(sum(np.sin(ph * k) / k ** 1.1 for k in range(1, 12)), "low", 2600)
    return x * env(n, 0.06, 0.15, 0.8, 0.35, dur) * amp


def taiko(amp=1.0, f0=95, f1=48, dec=6, seed=0, sec=0.7):
    n = int(sec * SR); t = np.arange(n) / SR
    f = f1 + (f0 - f1) * np.exp(-t * 18)
    body = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * dec)
    skin = filt(np.random.default_rng(seed).standard_normal(n), "low", 1800) * np.exp(-t * 40) * 0.6
    return (body + skin) * amp


def impact(seed):
    n = int(2.2 * SR); t = np.arange(n) / SR; rng = np.random.default_rng(seed)
    sub = np.sin(2 * np.pi * np.cumsum(38 + 50 * np.exp(-t * 9)) / SR) * np.exp(-t * 2.2)
    crash = filt(rng.standard_normal(n), "high", 3000) * np.exp(-t * 2.8) * 0.35
    boom = filt(rng.standard_normal(n), "low", 400) * np.exp(-t * 5) * 0.8
    return sub * 1.3 + crash + boom


def riser(sec, seed=5):
    n = int(sec * SR); x = np.random.default_rng(seed).standard_normal(n); out = np.zeros(n); st = 40
    for k in range(st):
        a, b = k * n // st, (k + 1) * n // st
        out[a:b] = filt(x[a:b], "high", 300 + 6000 * (k / st) ** 2, 1)
    return out * np.linspace(0, 1, n) ** 2 * 0.5


def whoosh(sec, seed):
    n = int(sec * SR); x = np.random.default_rng(seed).standard_normal(n); out = np.zeros(n); st = 24
    for k in range(st):
        a, b = k * n // st, (k + 1) * n // st
        out[a:b] = filt(x[a:b], "band", (300 + 2500 * k / st, 900 + 7000 * k / st), 1)
    return out * np.sin(np.linspace(0, np.pi, n)) ** 2


def click(seed):
    n = int(0.04 * SR); t = np.arange(n) / SR
    return filt(np.random.default_rng(seed).standard_normal(n), "band", (1800, 6000)) * np.exp(-t * 160) * 0.5


def reverb(x, sec, wet, seed):
    from scipy.signal import fftconvolve
    n = int(sec * SR)
    ir = np.random.default_rng(seed).standard_normal(n) * np.exp(-np.arange(n) / SR * 3.2)
    ir = filt(ir, "low", 5000); ir /= np.sqrt((ir ** 2).sum())
    return x * (1 - wet) + fftconvolve(x, ir)[:len(x)] * wet * 1.2


CHORDS = [("D", 3), ("A#", 4), ("F", 4), ("C", 4)]
def triad(r, third, o): b = mn(r + str(o)); return [b, b + third, b + 7]


MELODY = [[("A4", 1), ("D5", .5), ("E5", .5), ("F5", 2)],
          [("F5", 1), ("D5", 1), ("A#4", 2)],
          [("A4", 1), ("C5", 1), ("F5", 1), ("E5", 1)],
          [("E5", 1), ("G5", 1), ("E5", .5), ("D5", .5), ("C5", 1)]]


def make_music(tl, total, path):
    N = int((total + 3) * SR)
    mus, drm = np.zeros(N), np.zeros(N)
    s0, out_t = tl[1][2], tl[-1][2]
    # 인트로: 흰 화면 — 저음 드론 + 상승
    put(mus, pad([mn("D2"), mn("A2"), mn("D3")], s0, 0.13, 1), 0)
    put(drm, riser(s0, 9), 0, 0.8)
    bar = 4 * BEAT
    nb = int(math.ceil((out_t - s0) / bar - 1e-6))
    for b in range(nb):
        t0 = s0 + b * bar
        bl = min(bar, out_t - t0)
        root, third = CHORDS[b % 4]
        sec = 0 if b < 6 else 1 if b < 12 else 2  # 레이싱 / 마을·육성(부드럽게) / 클라이맥스
        put(mus, pad(triad(root, third, 3) + [triad(root, third, 4)[0]], bl, 0.11 if sec != 1 else 0.13, b), t0)
        if sec == 2:
            put(mus, pad(triad(root, third, 4), bl, 0.06, 50 + b), t0)
        # 베이스 8분
        for k in range(int(bl / (BEAT / 2) + 1e-6)):
            n = int(0.24 * SR)
            x = filt(saw(mf(mn(root + "2")), n, (0, 5)), "low", 500) * env(n, 0.005, 0.1, 0.5, 0.08, 0.18)
            put(mus, x, t0 + k * BEAT / 2, 0.22 if sec != 1 else 0.12)
        # 16분 오스티나토
        if b >= 1:
            cn = triad(root, third, 4); pat = [cn[0], cn[1], cn[2], cn[0] + 12]
            for k in range(int(bl / (BEAT / 4) + 1e-6)):
                n = int(0.2 * SR)
                x = filt(saw(mf(pat[k % 4]), n, (-6, 6), k), "low", 3200) * env(n, 0.005, 0.12, 0, 0.05, 0.12)
                put(mus, x, t0 + k * BEAT / 4, 0.09 if sec != 1 else 0.05)
        # 타이코
        hits = [(0, 1.0), (3, 0.6), (4, 0.85), (6, 0.7), (7, 0.45)] if sec != 1 else [(0, 0.7), (4, 0.45)]
        if sec == 2: hits += [(5, 0.5), (7, 0.6)]
        for k, a in hits:
            if k * BEAT / 2 < bl - 1e-6:
                put(drm, taiko(a, seed=b * 10 + k), t0 + k * BEAT / 2, 0.55)
        # 금관 멜로디
        if b >= 2:
            tt = t0
            for note, beats in MELODY[b % 4]:
                if tt - t0 < bl - 1e-6:
                    d = min(beats * BEAT * 0.95, out_t - tt)
                    amp = 0.30 if sec != 1 else 0.20
                    put(mus, brass(mn(note), d, amp), tt)
                    put(mus, brass(mn(note) - 12, d, amp * 0.55), tt)
                    if sec == 2: put(mus, brass(mn(note) + 12, d, amp * 0.25), tt)
                tt += beats * BEAT
    # 전환 효과
    for idx, (kind, arg, s, e) in enumerate(tl[1:], 1):
        if kind == "scene":
            put(drm, whoosh(0.4, idx), s - 0.25, 0.3)
            put(drm, impact(idx * 7), s, 0.75 if idx in (1, 13) else 0.55)
            if SCENES[arg].get("shake"): put(drm, impact(77), s + 0.35, 0.9)
    # 클라이맥스 직전 스네어 롤 (아웃트로 진입)
    for k in range(16):
        put(drm, filt(np.random.default_rng(300 + k).standard_normal(int(0.12 * SR)), "band", (1500, 6000))
            * np.exp(-np.arange(int(0.12 * SR)) / SR * 30), out_t - 1.0 + k / 16, 0.05 + 0.25 * k / 16)
    # 아웃트로: 최종 화음 → 잔잔하게
    od = total - out_t
    final = triad("D", 3, 3) + triad("D", 3, 4) + [mn("D2")]
    put(mus, pad(final, od - 0.5, 0.14, 42), out_t)
    for m, a in (("D5", 0.34), ("A4", 0.24), ("D4", 0.24)):
        put(mus, brass(mn(m), 2.6, a), out_t + 0.0)
    put(drm, impact(500), out_t, 1.0)
    put(drm, taiko(1.5, 80, 40, 2.5, 7, 1.2), out_t)
    # Coming Soon 타이핑 소리
    for k in range(len("Coming Soon")):
        put(drm, click(900 + k), out_t + 2.4 + 0.45 + k * 0.09, 0.6)
    mix = reverb(mus, 2.4, 0.35, 1) + reverb(drm, 1.6, 0.18, 2)
    mix = mix[:int(total * SR)]
    fade = int(1.2 * SR); mix[-fade:] *= np.linspace(1, 0, fade)
    mix = np.tanh(mix / np.abs(mix).max() * 1.6) * 0.9
    st = np.stack([mix, np.roll(mix, 220) * 0.97], 1)
    with wave.open(path, "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((st * 32767).astype(np.int16).tobytes())


# ------------------------------------------------------------------ 메인
def main():
    tl, total = timeline()
    r = Renderer()
    if len(sys.argv) > 1 and sys.argv[1] == "preview":
        outd = sys.argv[2]
        times = [float(x) for x in sys.argv[3].split(",")]
        for t in times:
            random.seed(1)
            r.frame(tl, t).convert("RGB").resize((640, 360), Image.LANCZOS).save(os.path.join(outd, f"p_{t:05.2f}.png"))
        return
    mdir = os.path.join(HERE, "음악"); os.makedirs(mdir, exist_ok=True)
    wav = os.path.join(mdir, "BGM_본편_45초.wav")
    print("음악 합성...", flush=True)
    make_music(tl, total, wav)
    ff = imageio_ffmpeg.get_ffmpeg_exe()
    subprocess.run([ff, "-y", "-loglevel", "error", "-i", wav, "-b:a", "320k", wav[:-4] + ".mp3"], check=True)
    tmp = os.path.join(HERE, "_tmp45.mp4")
    p = subprocess.Popen([ff, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                          "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "slow", "-crf", "16",
                          "-pix_fmt", "yuv420p", tmp], stdin=subprocess.PIPE)
    nf = int(round(total * FPS))
    for fi in range(nf):
        p.stdin.write(r.frame(tl, fi / FPS).convert("RGB").tobytes())
        if fi % 60 == 0: print(f"  {fi}/{nf}", flush=True)
    p.stdin.close(); p.wait()
    final = os.path.join(HERE, "티저_본편_45초.mp4")
    subprocess.run([ff, "-y", "-loglevel", "error", "-i", tmp, "-i", wav, "-c:v", "copy", "-c:a", "aac", "-b:a", "256k",
                    "-shortest", "-movflags", "+faststart", final], check=True)
    os.remove(tmp)
    print("완료:", final)


if __name__ == "__main__":
    main()
