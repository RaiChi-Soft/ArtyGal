import os
from PIL import Image

# 终端输出宽度（相当于像素宽度）
TARGET_WIDTH = 32 

def convert_image_to_ansi(image_path, output_path, width=54):
    try:
        # 打开图片并强制转换为 RGBA 模式（保留透明度）
        img = Image.open(image_path).convert("RGBA")
    except Exception as e:
        print(f"无法读取图片 {image_path}: {e}")
        return

    # 强制按照 9:16 的比例计算高度
    height = int(width * 16 / 9)
    # 确保高度是偶数，因为我们每次要读取上下两个像素
    if height % 2 != 0:
        height += 1

    # 高质量缩放图片
    img = img.resize((width, height), Image.Resampling.LANCZOS)
    pixels = img.load()

    ansi_lines = []
    
    # 每次步进 2 行（上像素和下像素组合成一个字符）
    for y in range(0, height, 2):
        line = ""
        for x in range(width):
            top_pixel = pixels[x, y]
            bottom_pixel = pixels[x, y+1]
            
            # 解析 RGBA
            tr, tg, tb, ta = top_pixel
            br, bg, bb, ba = bottom_pixel
            
            # 【修改点】判断是否为白色 (RGB均大于 245 视作白色背景)
            top_is_white = (tr > 245 and tg > 245 and tb > 245)
            bottom_is_white = (br > 245 and bg > 245 and bb > 245)
            
            # 【修改点】处理可见度逻辑 (透明或纯白都视作不可见，输出空格)
            top_visible = (ta > 128) and not top_is_white
            bottom_visible = (ba > 128) and not bottom_is_white
            
            if not top_visible and not bottom_visible:
                # 上下都透明或白色，输出空格
                line += "\033[0m "
            elif top_visible and not bottom_visible:
                # 仅上半部分可见，使用上半方块字符 '▀'，设置前景色为上像素
                line += f"\033[0m\033[38;2;{tr};{tg};{tb}m▀"
            elif not top_visible and bottom_visible:
                # 仅下半部分可见，使用下半方块字符 '▄'，设置前景色为下像素
                line += f"\033[0m\033[38;2;{br};{bg};{bb}m▄"
            else:
                # 上下都可见，使用下半方块字符 '▄'
                # 背景色设为上像素 (Top)，前景色设为下像素 (Bottom)
                line += f"\033[48;2;{tr};{tg};{tb}m\033[38;2;{br};{bg};{bb}m▄"
                
        # 行末重置颜色并换行
        line += "\033[0m\n"
        ansi_lines.append(line)

    # 写入文件
    with open(output_path, "w", encoding="utf-8") as f:
        f.writelines(ansi_lines)
    print(f"[成功] {os.path.basename(image_path)} -> {os.path.basename(output_path)} (尺寸: {width}x{height} 像素, 终端占用 {width}列 x {height//2}行)")

def main():
    input_dir = "role"
    output_dir = "ansi_art"
    
    # 创建输出文件夹
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    # 遍历 role 文件夹中的 png 文件
    for filename in os.listdir(input_dir):
        if filename.lower().endswith(".png"):
            input_path = os.path.join(input_dir, filename)
            output_name = filename.rsplit('.', 1)[0] + ".ans"
            output_path = os.path.join(output_dir, output_name)
            
            convert_image_to_ansi(input_path, output_path, width=TARGET_WIDTH)

if __name__ == "__main__":
    main()