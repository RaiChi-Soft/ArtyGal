#!/usr/bin/env python3
"""
PNG 转多分辨率 ICO 工具（直接指定路径版）
将任意 PNG 图片转换为包含多个尺寸的 .ico 文件。
"""

from pathlib import Path
from PIL import Image

# ==================== 在这里指定你的路径 ====================
INPUT_PNG = "D:/400HBI/490EPN/EX40AHE/2026052101_ArtyGal/role/artygal.png"   # 修改为你的 PNG 文件路径
OUTPUT_ICO = "D:/400HBI/490EPN/EX40AHE/2026052101_ArtyGal/artygal.ico"   # 修改为你想要的 ICO 输出路径
# ===========================================================

# 默认包含的图标尺寸（宽,高）
DEFAULT_SIZES = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]


def resize_with_padding(img: Image.Image, target_size: tuple) -> Image.Image:
    """缩放并居中填充透明背景"""
    target_w, target_h = target_size
    ratio = min(target_w / img.width, target_h / img.height)
    new_w = int(img.width * ratio)
    new_h = int(img.height * ratio)

    resized = img.resize((new_w, new_h), Image.Resampling.LANCZOS)

    new_img = Image.new("RGBA", (target_w, target_h), (0, 0, 0, 0))
    x = (target_w - new_w) // 2
    y = (target_h - new_h) // 2
    new_img.paste(resized, (x, y))
    return new_img


def png_to_ico(png_path: str, ico_path: str, sizes: list = None):
    png_path = Path(png_path)
    if not png_path.exists():
        raise FileNotFoundError(f"找不到文件: {png_path}")

    ico_path = Path(ico_path)
    if sizes is None:
        sizes = DEFAULT_SIZES

    img = Image.open(png_path).convert("RGBA")

    images = []
    for size in sizes:
        images.append(resize_with_padding(img, size))

    images[0].save(ico_path, format="ICO", append_images=images[1:])
    print(f"成功生成 ICO 文件: {ico_path}")
    print(f"包含尺寸: {', '.join(f'{w}x{h}' for w, h in sizes)}")


if __name__ == "__main__":
    png_to_ico(INPUT_PNG, OUTPUT_ICO)