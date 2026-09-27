import json
import sys
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont


ROOT = Path(__file__).parent
CONTENT_PATH = ROOT / "content" / "stories.json"
OUTPUT_DIR = ROOT / "output" / "stories"
FONT_DIR = ROOT / "fonts"

W, H = 1080, 1920
BG = "#0B0B0B"
GOLD = "#C9A45C"
TEXT = "#F2EDE4"
BODY = "#D6D0C6"
GRAY = "#9A948A"
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
        return ImageFont.load_default(size=size)


def font_cormorant(size, variation="Bold"):
    return load_font("CormorantGaramond.ttf", size, variation)


def font_inter(size, variation="Regular"):
    return load_font("Inter.ttf", size, variation)


def text_size(draw, text, font):
    box = draw.textbbox((0, 0), text, font=font)
    return box[2] - box[0], box[3] - box[1]


def wrap_to_width(draw, text, font, max_width):
    estimate = max(8, int(max_width / max(font.size * 0.43, 1)))
    lines = []
    for part in text.splitlines():
        lines.extend(textwrap.wrap(part, width=estimate) or [""])
    changed = True
    while changed:
        changed = False
        next_lines = []
        for line in lines:
            if text_size(draw, line, font)[0] <= max_width:
                next_lines.append(line)
            else:
                next_lines.extend(textwrap.wrap(line, width=max(8, len(line) - 4)))
                changed = True
        lines = next_lines
    return lines


def fit(draw, text, font_factory, max_size, min_size, max_width, max_height, variation="Bold", spacing=1.0):
    for size in range(max_size, min_size - 1, -2):
        font = font_factory(size, variation)
        lines = wrap_to_width(draw, text, font, max_width)
        line_h = int(size * spacing)
        total_h = line_h * len(lines)
        if total_h <= max_height:
            return font, lines, line_h, total_h
    font = font_factory(min_size, variation)
    lines = wrap_to_width(draw, text, font, max_width)
    return font, lines, int(min_size * spacing), int(min_size * spacing) * len(lines)


def draw_text(draw, xy, text, **kwargs):
    try:
        draw.text(xy, text, **kwargs)
    except KeyError:
        kwargs.pop("features", None)
        draw.text(xy, text, **kwargs)


def draw_lines(draw, lines, xy, font, fill, line_h, features=None):
    x, y = xy
    for line in lines:
        draw_text(draw, (x, y), line, font=font, fill=fill, features=features)
        y += line_h


def canvas(seed):
    img = Image.new("RGB", (W, H), BG)
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    positions = [(160, 360), (920, 480), (260, 1350), (880, 1460)]
    x, y = positions[seed % len(positions)]
    gd.ellipse((x - 280, y - 280, x + 280, y + 280), fill=(201, 164, 92, 88))
    glow = glow.filter(ImageFilter.GaussianBlur(180))
    img = Image.alpha_composite(img.convert("RGBA"), glow).convert("RGB")
    d = ImageDraw.Draw(img)
    d.rectangle((40, 40, W - 40, H - 40), outline=GOLD, width=2)
    return img


def generate_story(story, brand):
    img = canvas(story["id"])
    d = ImageDraw.Draw(img)
    d.text((MARGIN_X, 92), "ANDOLINI LABS", font=font_inter(30, "SemiBold"), fill=TEXT)
    d.text((W - MARGIN_X, 92), brand["handle"], font=font_inter(28), fill=GRAY, anchor="ra")
    d.line((MARGIN_X, 360, MARGIN_X + 128, 360), fill=GOLD, width=5)

    max_w = W - MARGIN_X * 2
    title_font, title_lines, title_h, title_total = fit(d, story["title"], font_cormorant, 104, 62, max_w, 610, "Bold", 1.0)
    body_font, body_lines, body_h, body_total = fit(d, story["body"], font_inter, 44, 32, max_w, 260, "Regular", 1.34)
    prompt_font, prompt_lines, prompt_h, prompt_total = fit(d, story["prompt"], font_inter, 34, 26, max_w, 150, "Medium", 1.28)

    block_h = title_total + 52 + body_total + 92 + prompt_total
    y = int((H - block_h) / 2) - 30
    draw_lines(d, title_lines, (MARGIN_X, y), title_font, TEXT, title_h, features=["lnum"])
    draw_lines(d, body_lines, (MARGIN_X, y + title_total + 52), body_font, BODY, body_h)

    prompt_y = y + title_total + 52 + body_total + 92
    d.rounded_rectangle((MARGIN_X, prompt_y - 26, W - MARGIN_X, prompt_y + prompt_total + 34), radius=28, outline=GOLD, width=2)
    draw_lines(d, prompt_lines, (MARGIN_X + 30, prompt_y), prompt_font, GOLD, prompt_h)
    d.text((MARGIN_X, H - 150), brand["site"], font=font_inter(28), fill=GRAY)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUTPUT_DIR / f"story_{story['id']:02d}.jpg"
    img.save(out, "JPEG", quality=92, optimize=True)
    return out


def selected_ids(argv):
    if not argv:
        return None
    return {int(arg) for arg in argv}


def main():
    data = json.loads(CONTENT_PATH.read_text(encoding="utf-8"))
    ids = selected_ids(sys.argv[1:])
    if OUTPUT_DIR.exists():
        if ids is None:
            old_files = OUTPUT_DIR.glob("story_*.jpg")
        else:
            old_files = (OUTPUT_DIR / f"story_{story_id:02d}.jpg" for story_id in ids)
        for old in old_files:
            if old.exists():
                old.unlink()
    stories = [s for s in data["stories"] if ids is None or s["id"] in ids]
    for story in stories:
        out = generate_story(story, data["brand"])
        print(f"Gerado {out}")


if __name__ == "__main__":
    main()
