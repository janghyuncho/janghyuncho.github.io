"""Generate web-sized WebP thumbnails from the full-resolution assets.

The originals in assets/images are kept as the archival copies; only the
generated assets/thumbs versions are referenced by index.html.

Usage: python3 tools/build_thumbnails.py
"""

from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
SOURCE_DIR = ROOT / "assets" / "images"
OUT_DIR = ROOT / "assets" / "thumbs"

# Rendered at ~180px (publications) and ~190px (portrait); 2x for high-DPI screens.
MAX_WIDTH = 480

SOURCES = [
    "face.png",
    "perceptionlm.png",
    "perception_encoder.png",
    "vila2.png",
    "cubellm.png",
    "decola.png",
    "part_distillation.png",
    "nms.png",
    "ecm_loss.png",
    "picie.png",
    "distillation.png",
]


def flatten(image):
    """Composite transparency onto white so figures keep a clean paper background."""
    if image.mode in ("RGBA", "LA", "P"):
        image = image.convert("RGBA")
        canvas = Image.new("RGBA", image.size, (255, 255, 255, 255))
        return Image.alpha_composite(canvas, image).convert("RGB")
    return image.convert("RGB")


def scaled_size(size):
    width, height = size
    if width <= MAX_WIDTH:
        return size
    return MAX_WIDTH, max(1, round(height * MAX_WIDTH / width))


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    total_before = total_after = 0

    for filename in SOURCES:
        source = SOURCE_DIR / filename
        target = OUT_DIR / (Path(filename).stem + ".webp")
        with Image.open(source) as image:
            image = flatten(image)
            image.resize(scaled_size(image.size), Image.LANCZOS).save(
                target, "WEBP", quality=82, method=6
            )
        before, after = source.stat().st_size, target.stat().st_size
        total_before += before
        total_after += after
        print(f"{target.name:<26} {before / 1024:>9,.0f} KB -> {after / 1024:>6,.0f} KB")

    print(f"\ntotal {total_before / 1024 / 1024:.1f} MB -> {total_after / 1024:.0f} KB")


if __name__ == "__main__":
    main()
