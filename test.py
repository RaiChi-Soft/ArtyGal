#!/usr/bin/env python3
"""
TUI像素画绘制器 - 在终端中绘制彩色像素画

使用ANSI转义序列实现真彩色显示，支持从JSON文件加载自定义图案。
用法: python pixel_art.py [--file 文件路径]
"""

import sys
import argparse
import json
import os
from typing import List, Tuple

# 颜色类型定义为 (R, G, B) 三元组，每个分量0-255
Color = Tuple[int, int, int]


class PixelArt:
    """像素画类，存储并渲染彩色像素网格"""

    def __init__(self, pixels: List[List[Color]]):
        """
        初始化像素画
        :param pixels: 二维列表，每个元素是 (r,g,b) 颜色元组
        """
        if not pixels or not pixels[0]:
            raise ValueError("像素数据不能为空")
        self.pixels = pixels
        self.height = len(pixels)
        self.width = len(pixels[0])

    def render(self) -> None:
        """渲染像素画到终端（清屏后绘制）"""
        # 隐藏光标，获得更干净的显示效果
        sys.stdout.write('\033[?25l')
        # 将光标移动到左上角
        sys.stdout.write('\033[H')

        for row in self.pixels:
            for (r, g, b) in row:
                # 使用背景色 + 空格字符绘制像素点
                # 格式: \033[48;2;R;G;Bm   \033[0m
                sys.stdout.write(f'\033[48;2;{r};{g};{b}m \033[0m')
            sys.stdout.write('\n')

        sys.stdout.flush()
        # 恢复光标显示
        sys.stdout.write('\033[?25h')

    @classmethod
    def from_file(cls, filepath: str) -> 'PixelArt':
        """
        从JSON文件加载像素画
        文件格式：二维数组，每个元素是 [R, G, B] 整数列表
        示例: [[[255,0,0],[0,255,0]], [[0,0,255],[255,255,0]]]
        """
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)

        if not isinstance(data, list):
            raise ValueError("JSON根元素必须是数组")
        if not all(isinstance(row, list) for row in data):
            raise ValueError("每个像素行必须是数组")

        pixels = []
        for y, row in enumerate(data):
            pixel_row = []
            if not row:
                raise ValueError(f"第{y}行不能为空")
            for x, pixel in enumerate(row):
                if not (isinstance(pixel, list) and len(pixel) == 3):
                    raise ValueError(f"位置({x},{y})的颜色必须是[R,G,B]格式")
                if not all(0 <= c <= 255 for c in pixel):
                    raise ValueError(f"位置({x},{y})的颜色分量超出0-255范围")
                pixel_row.append(tuple(pixel))
            # 检查每行宽度是否一致
            if y > 0 and len(pixel_row) != len(pixels[0]):
                raise ValueError(f"第{y}行宽度({len(pixel_row)})与第一行({len(pixels[0])})不一致")
            pixels.append(pixel_row)

        return cls(pixels)


def sample_pixel_art() -> PixelArt:
    """生成一个20x20的示例像素画：蓝天、草地、太阳和花朵"""
    size = 20
    # 初始化为天蓝色背景
    pixels = [[(135, 206, 235) for _ in range(size)] for _ in range(size)]

    # 底部草地（深绿色）
    grass_start = size - 5
    for y in range(grass_start, size):
        for x in range(size):
            pixels[y][x] = (34, 139, 34)  # 森林绿

    # 右上角太阳（黄色圆形）
    sun_cx, sun_cy = 16, 4
    sun_radius = 2
    for y in range(sun_cy - sun_radius, sun_cy + sun_radius + 1):
        for x in range(sun_cx - sun_radius, sun_cx + sun_radius + 1):
            if (x - sun_cx) ** 2 + (y - sun_cy) ** 2 <= sun_radius ** 2:
                if 0 <= y < size and 0 <= x < size:
                    pixels[y][x] = (255, 255, 0)  # 黄色

    # 太阳上的表情（黑色眼睛和微笑）
    if 0 <= sun_cy < size and 0 <= sun_cx - 1 < size:
        pixels[sun_cy][sun_cx - 1] = (0, 0, 0)      # 左眼
    if 0 <= sun_cy < size and 0 <= sun_cx + 1 < size:
        pixels[sun_cy][sun_cx + 1] = (0, 0, 0)      # 右眼
    # 微笑（一条弧线）
    for dx in range(-1, 2):
        if 0 <= sun_cy + 1 < size and 0 <= sun_cx + dx < size:
            pixels[sun_cy + 1][sun_cx + dx] = (0, 0, 0)

    # 花朵（中心偏左）
    flower_cx, flower_cy = 7, 12
    # 花瓣（8个方向）
    petals = [(0, -2), (1, -1), (2, 0), (1, 1), (0, 2), (-1, 1), (-2, 0), (-1, -1)]
    for dx, dy in petals:
        nx, ny = flower_cx + dx, flower_cy + dy
        if 0 <= nx < size and 0 <= ny < size:
            pixels[ny][nx] = (255, 105, 180)  # 热粉色
    # 花蕊（金色）
    if 0 <= flower_cx < size and 0 <= flower_cy < size:
        pixels[flower_cy][flower_cx] = (255, 215, 0)  # 金色
    # 花茎（绿色向下延伸）
    for y in range(flower_cy, size):
        if 0 <= flower_cx < size:
            pixels[y][flower_cx] = (0, 128, 0)  # 深绿色

    return PixelArt(pixels)


def main() -> None:
    parser = argparse.ArgumentParser(description='在终端中绘制彩色像素画（TUI）')
    parser.add_argument('--file', '-f', help='JSON格式的像素画文件（二维[R,G,B]数组）')
    args = parser.parse_args()

    # 加载像素画数据
    if args.file:
        try:
            art = PixelArt.from_file(args.file)
            print(f"已加载文件: {args.file}", file=sys.stderr)
        except Exception as e:
            print(f"错误: 无法加载文件 - {e}", file=sys.stderr)
            sys.exit(1)
    else:
        art = sample_pixel_art()
        print("未提供文件，显示示例像素画。使用 --file 加载自己的图案。", file=sys.stderr)

    # 清屏并渲染
    os.system('clear' if os.name == 'posix' else 'cls')
    art.render()


if __name__ == '__main__':
    main()