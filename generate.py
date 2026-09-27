import json
import math
import sys
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont


ROOT = Path(__file__).parent
CONTENT_PATH = ROOT / "content" / "posts.json"
OUTPUT_DIR = ROOT / "output"
FONT_DIR = ROOT / "fonts"

W, H = 1080, 1350
BG = "#0B0B0B"
GOLD = "#C9A45C"
TEXT = "#F2EDE4"
BODY = "#D6D0C6"
GRAY = "#9A948A"
RED = "#A6423D"
GREEN = "#4F8A5B"
MARGIN_X = 96


def load_font(name, size, variation=None):
    path = FONT_DIR / name
    try:
        font = ImageFont.truetype(str(path), size)
        if variation and hasattr(font, "set_variation_by_name"):
            try:
                font.set_variation_by_name(variation)
            except Exception:
                pass
        return font
    except OSError:
        fallback = "arial.ttf" if name.lower().startswith("inter") else "times.ttf"
        try:
            return ImageFont.truetype(fallback, size)
        except OSError:
            return ImageFont.load_default(size=size)


def font_cormorant(size, variation="Bold"):
    return load_font("CormorantGaramond.ttf", size, variation)


def font_inter(size, variation="Regular"):
    return load_font("Inter.ttf", size, variation)


def text_bbox(draw, xy, text, font, **kwargs):
    return draw.textbbox(xy, text, font=font, **kwargs)


def text_size(draw, text, font, **kwargs):
    box = text_bbox(draw, (0, 0), text, font, **kwargs)
    return box[2] - box[0], box[3] - box[1]


def fit_lines(draw, text, font_name, max_size, min_size, max_width, max_height=None, variation="Regular", line_spacing=1.2):
    for size in range(max_size, min_size - 1, -2):
        font = font_name(size, variation)
        avg = max(8, int(max_width / max(size * 0.43, 1)))
        raw_lines = []
        for part in str(text).splitlines():
            raw_lines.extend(textwrap.wrap(part, width=avg) or [""])
        changed = True
        while changed:
            changed = False
            next_lines = []
            for line in raw_lines:
                if text_size(draw, line, font)[0] <= max_width:
                    next_lines.append(line)
                else:
                    cut = max(8, len(line) - 4)
                    next_lines.extend(textwrap.wrap(line, width=cut))
                    changed = True
            raw_lines = next_lines
        line_h = int(size * line_spacing)
        total_h = line_h * len(raw_lines)
        if (max_height is None or total_h <= max_height) and all(text_size(draw, line, font)[0] <= max_width for line in raw_lines):
            return font, raw_lines, line_h, total_h
    font = font_name(min_size, variation)
    return font, textwrap.wrap(str(text), width=24), int(min_size * line_spacing), int(min_size * line_spacing)


def draw_multiline(draw, lines, xy, font, fill, line_h, anchor="la", features=None):
    x, y = xy
    for line in lines:
        draw_text(draw, (x, y), line, font=font, fill=fill, anchor=anchor, features=features)
        y += line_h


def draw_text(draw, xy, text, **kwargs):
    try:
        draw.text(xy, text, **kwargs)
    except KeyError as exc:
        if "font features" not in str(exc):
            raise
        kwargs.pop("features", None)
        draw.text(xy, text, **kwargs)


def base_canvas(seed):
    img = Image.new("RGB", (W, H), BG)
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    positions = [(160, 260), (920, 330), (280, 1020), (880, 980), (540, 620)]
    x, y = positions[seed % len(positions)]
    gd.ellipse((x - 230, y - 230, x + 230, y + 230), fill=(201, 164, 92, 92))
    glow = glow.filter(ImageFilter.GaussianBlur(160))
    img = Image.alpha_composite(img.convert("RGBA"), glow).convert("RGB")
    d = ImageDraw.Draw(img)
    d.rectangle((40, 40, W - 40, H - 40), outline=GOLD, width=2)
    return img


def header(draw, brand):
    draw.text((MARGIN_X, 78), "ANDOLINI LABS", font=font_inter(28, "SemiBold"), fill=TEXT)
    handle = brand["handle"]
    tw, _ = text_size(draw, handle, font_inter(28, "Regular"))
    draw.text((W - MARGIN_X - tw, 78), handle, font=font_inter(28, "Regular"), fill=GRAY)


def footer(draw, idx, total, last=False):
    y = H - 104
    gap = 10
    total_w = 520
    seg_w = (total_w - gap * (total - 1)) / total
    x0 = MARGIN_X
    for i in range(total):
        fill = GOLD if i <= idx else "#2A2825"
        draw.rounded_rectangle((x0 + i * (seg_w + gap), y, x0 + i * (seg_w + gap) + seg_w, y + 8), radius=4, fill=fill)
    if not last:
        draw.text((W - MARGIN_X, y - 12), "arrasta ->", font=font_inter(24), fill=GRAY, anchor="ra")


def draw_cover(post, brand):
    img = base_canvas(post["id"])
    d = ImageDraw.Draw(img)
    header(d, brand)
    d.line((MARGIN_X, 360, MARGIN_X + 130, 360), fill=GOLD, width=5)
    max_w = W - MARGIN_X * 2
    title_font, title_lines, title_h, title_total = fit_lines(d, post["cover"]["title"], font_cormorant, 150, 80, max_w, 500, "Bold", 0.95)
    sub_font, sub_lines, sub_h, sub_total = fit_lines(d, post["cover"]["sub"], font_inter, 42, 30, max_w, 140, "Medium", 1.25)
    total = title_total + 28 + sub_total
    y = int((H - total) / 2) - 10
    draw_multiline(d, title_lines, (MARGIN_X, y), title_font, TEXT, title_h, features=["lnum"])
    draw_multiline(d, sub_lines, (MARGIN_X, y + title_total + 28), sub_font, GOLD, sub_h)
    return img


def normalized_body(body):
    if "✓" in body:
        items = [line.strip() for line in body.replace("\\n", "\n").splitlines() if line.strip()]
        return items
    return [body]


def draw_content(post, slide, brand, idx, total):
    img = base_canvas(post["id"] + idx)
    d = ImageDraw.Draw(img)
    header(d, brand)
    title = slide["t"]
    tag = None
    if title.startswith("❌"):
        tag, title = ("ANTES", RED), title[1:].strip()
    elif title.startswith("✅"):
        tag, title = ("DEPOIS", GREEN), title[1:].strip()
    draw_text(d, (MARGIN_X, 250), f"{idx:02d}", font=font_cormorant(150, "Light"), fill=GOLD, features=["lnum"])
    if tag:
        label, color = tag
        tag_font = font_inter(24, "Bold")
        tw, th = text_size(d, label, tag_font)
        d.rounded_rectangle((MARGIN_X, 395, MARGIN_X + tw + 34, 435), radius=20, fill=color)
        d.text((MARGIN_X + 17, 402), label, font=tag_font, fill=TEXT)
        title_y = 462
    else:
        title_y = 430
    max_w = W - MARGIN_X * 2
    title_font, title_lines, title_h, title_total = fit_lines(d, title, font_cormorant, 96, 58, max_w, 260, "Bold", 1.0)
    body_font, body_lines, body_h, body_total = fit_lines(d, "\n".join(normalized_body(slide["b"])), font_inter, 54, 34, max_w, 420, "Regular", 1.42)
    block_h = title_total + 36 + body_total
    y = max(title_y, int((H - block_h) / 2) + 70)
    draw_multiline(d, title_lines, (MARGIN_X, y), title_font, TEXT, title_h, features=["lnum"])
    draw_multiline(d, body_lines, (MARGIN_X, y + title_total + 36), body_font, BODY, body_h)
    footer(d, idx, total)
    return img


def draw_cta(post, brand, total):
    img = base_canvas(post["id"] + total + 9)
    d = ImageDraw.Draw(img)
    header(d, brand)
    draw_text(d, (MARGIN_X, 320), "E agora?", font=font_cormorant(108, "Bold"), fill=TEXT, features=["lnum"])
    cta = post["cta"].replace("Comenta ", "Comenta\n", 1)
    cta_font, cta_lines, cta_h, cta_total = fit_lines(d, cta, font_cormorant, 92, 56, W - MARGIN_X * 2, 330, "Bold", 1.0)
    draw_multiline(d, cta_lines, (MARGIN_X, 470), cta_font, GOLD, cta_h, features=["lnum"])
    bullets = [f"Salva pra revisar depois", "Manda pra quem tem negocio", f"Segue {brand['handle']}"]
    y = 840
    for bullet in bullets:
        d.text((MARGIN_X, y), f"✓ {bullet}", font=font_inter(38, "Medium"), fill=BODY)
        y += 68
    d.text((MARGIN_X, H - 174), brand["site"], font=font_inter(28, "Regular"), fill=GRAY)
    footer(d, total - 1, total, last=True)
    return img


def save_jpg(img, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path, "JPEG", quality=92, optimize=True)


def generate_post(post, brand):
    post_dir = OUTPUT_DIR / f"post_{post['id']:02d}"
    if post_dir.exists():
        for old_slide in post_dir.glob("slide_*.jpg"):
            old_slide.unlink()
    total = len(post["slides"]) + 2
    images = [draw_cover(post, brand)]
    for i, slide in enumerate(post["slides"], start=1):
        images.append(draw_content(post, slide, brand, i, total))
    images.append(draw_cta(post, brand, total))
    for i, img in enumerate(images, start=1):
        save_jpg(img, post_dir / f"slide_{i:02d}.jpg")
    return post_dir


def contact_sheet(posts):
    covers = []
    for post in posts:
        cover = OUTPUT_DIR / f"post_{post['id']:02d}" / "slide_01.jpg"
        if cover.exists():
            img = Image.open(cover).resize((216, 270))
            covers.append((post["id"], img.copy()))
    cols = 5
    rows = math.ceil(len(covers) / cols)
    sheet = Image.new("RGB", (cols * 216, rows * 306), "#111111")
    d = ImageDraw.Draw(sheet)
    for n, (pid, img) in enumerate(covers):
        x = (n % cols) * 216
        y = (n // cols) * 306
        sheet.paste(img, (x, y))
        d.text((x + 10, y + 276), f"post {pid:02d}", font=font_inter(20, "Medium"), fill=TEXT)
    save_jpg(sheet, OUTPUT_DIR / "contact_sheet_covers.jpg")


def selected_ids(argv):
    if not argv:
        return None
    return {int(arg) for arg in argv}


def main():
    data = json.loads(CONTENT_PATH.read_text(encoding="utf-8"))
    ids = selected_ids(sys.argv[1:])
    posts = [p for p in data["posts"] if ids is None or p["id"] in ids]
    if not posts:
        raise SystemExit("Nenhum post encontrado para os ids informados.")
    for post in posts:
        generate_post(post, data["brand"])
        print(f"Gerado post_{post['id']:02d}")
    contact_sheet(posts if ids else data["posts"])
    print(f"Folha de contato: {OUTPUT_DIR / 'contact_sheet_covers.jpg'}")


if __name__ == "__main__":
    main()
