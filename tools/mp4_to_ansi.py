import argparse
import os
from pathlib import Path

import imageio.v3 as iio
from PIL import Image


TARGET_WIDTH = 64
TARGET_FPS = 10
INPUT_VIDEO = Path("role") / "raichisoft.mp4"
OUTPUT_DIR = Path("resources") / "intro"


def image_to_ansi(img: Image.Image, width: int = TARGET_WIDTH) -> str:
    img = img.convert("RGBA")
    aspect = img.height / img.width if img.width else 9 / 16
    height = max(2, int(width * aspect))
    if height % 2:
        height += 1
    img = img.resize((width, height), Image.Resampling.LANCZOS)
    pixels = img.load()

    ansi_lines = []
    for y in range(0, height, 2):
        line = ""
        for x in range(width):
            tr, tg, tb, ta = pixels[x, y]
            br, bg, bb, ba = pixels[x, y + 1]
            top_visible = ta > 128
            bottom_visible = ba > 128

            if not top_visible and not bottom_visible:
                line += "\033[0m "
            elif top_visible and not bottom_visible:
                line += f"\033[0m\033[38;2;{tr};{tg};{tb}m▀"
            elif not top_visible and bottom_visible:
                line += f"\033[0m\033[38;2;{br};{bg};{bb}m▄"
            else:
                line += f"\033[48;2;{tr};{tg};{tb}m\033[38;2;{br};{bg};{bb}m▄"
        ansi_lines.append(line + "\033[0m\n")
    return "".join(ansi_lines)


def convert_video(input_path: Path, output_dir: Path, width: int, fps: int) -> None:
    if not input_path.exists():
        raise FileNotFoundError(input_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    for old in output_dir.glob("frame_*.ans"):
        old.unlink()

    meta = iio.immeta(input_path)
    source_fps = float(meta.get("fps") or fps)
    step = max(1, round(source_fps / fps))

    saved = 0
    for frame_index, frame in enumerate(iio.imiter(input_path)):
        if frame_index % step:
            continue
        img = Image.fromarray(frame)
        out_path = output_dir / f"frame_{saved:04d}.ans"
        out_path.write_text(image_to_ansi(img, width), encoding="utf-8")
        saved += 1

    manifest = output_dir / "manifest.txt"
    manifest.write_text(f"fps={fps}\nframes={saved}\nwidth={width}\n", encoding="utf-8")
    print(f"[成功] {input_path} -> {output_dir} ({saved} frames @ {fps}fps)")


def main() -> None:
    parser = argparse.ArgumentParser(description="Convert mp4 video to ANSI animation frames.")
    parser.add_argument("--input", type=Path, default=INPUT_VIDEO)
    parser.add_argument("--output", type=Path, default=OUTPUT_DIR)
    parser.add_argument("--width", type=int, default=TARGET_WIDTH)
    parser.add_argument("--fps", type=int, default=TARGET_FPS)
    args = parser.parse_args()
    convert_video(args.input, args.output, args.width, args.fps)


if __name__ == "__main__":
    main()
