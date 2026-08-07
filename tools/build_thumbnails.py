"""Generate web-sized WebP thumbnails from the full-resolution assets.

The originals in assets/images are kept as the archival copies; only the
generated assets/thumbs versions are referenced by index.html.

Usage: python3 tools/build_thumbnails.py
"""

from pathlib import Path

from PIL import Image, ImageSequence

ROOT = Path(__file__).resolve().parent.parent
ASSET_DIR = ROOT / "assets"
OUT_DIR = ASSET_DIR / "thumbs"

# Rendered at ~180px (publications) and ~190px (portrait); 2x for high-DPI screens.
MAX_WIDTH = 480

# The animated teaser is kept narrower and at a lower quality: it carries 447
# frames, so it dominates page weight at the width used for the still figures.
ANIMATED_MAX_WIDTH = 300
ANIMATED_QUALITY = 55

STILLS = [
    "images/face.png",
    "images/perceptionlm.png",
    "images/perception_encoder.png",
    "images/vila2.png",
    "images/decola.png",
    "images/part_distillation.png",
    "images/nms.png",
    "images/ecm_loss.png",
    "images/picie.png",
    "images/distillation.png",
]

ANIMATIONS = ["gifs/cubellm_teaser.gif"]


def flatten(image):
    """Composite transparency onto white so figures keep a clean paper background."""
    if image.mode in ("RGBA", "LA", "P"):
        image = image.convert("RGBA")
        canvas = Image.new("RGBA", image.size, (255, 255, 255, 255))
        return Image.alpha_composite(canvas, image).convert("RGB")
    return image.convert("RGB")


def scaled_size(size, max_width):
    width, height = size
    if width <= max_width:
        return size
    return max_width, max(1, round(height * max_width / width))


def build_still(relative_path, target):
    with Image.open(ASSET_DIR / relative_path) as image:
        image = flatten(image)
        image.resize(scaled_size(image.size, MAX_WIDTH), Image.LANCZOS).save(
            target, "WEBP", quality=82, method=6
        )


def build_animation(relative_path, target):
    with Image.open(ASSET_DIR / relative_path) as source:
        frames, durations = [], []
        for frame in ImageSequence.Iterator(source):
            frames.append(flatten(frame))
            durations.append(frame.info.get("duration", 100))
        size = scaled_size(frames[0].size, ANIMATED_MAX_WIDTH)
        frames = [frame.resize(size, Image.LANCZOS) for frame in frames]
        frames[0].save(
            target,
            "WEBP",
            save_all=True,
            append_images=frames[1:],
            duration=durations,
            loop=0,
            quality=ANIMATED_QUALITY,
            method=4,
        )


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    total_before = total_after = 0

    for relative_path in STILLS + ANIMATIONS:
        target = OUT_DIR / (Path(relative_path).stem + ".webp")
        builder = build_animation if relative_path in ANIMATIONS else build_still
        builder(relative_path, target)
        before = (ASSET_DIR / relative_path).stat().st_size
        after = target.stat().st_size
        total_before += before
        total_after += after
        print(f"{target.name:<26} {before / 1024:>9,.0f} KB -> {after / 1024:>6,.0f} KB")

    print(f"\ntotal {total_before / 1024 / 1024:.1f} MB -> {total_after / 1024:.0f} KB")


if __name__ == "__main__":
    main()
