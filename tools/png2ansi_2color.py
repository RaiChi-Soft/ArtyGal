import os
from PIL import Image

# 终端输出宽度（相当于像素宽度）
TARGET_WIDTH = 32 

def convert_image_to_monochrome_ansi(image_path, output_path, width=32):
    try:
        # 打开图片并强制转换为 RGBA 模式
        img = Image.open(image_path).convert("RGBA")
    except Exception as e:
        print(f"无法读取图片 {image_path}: {e}")
        return

    # 强制按照 9:16 的比例计算高度
    height = int(width * 16 / 9)
    if height % 2 != 0:
        height += 1

    # 高质量缩放图片
    img = img.resize((width, height), Image.Resampling.LANCZOS)
    pixels = img.load()

    ansi_lines = []
    
    # 每次步进 2 行
    for y in range(0, height, 2):
        line = ""
        for x in range(width):
            top_pixel = pixels[x, y]
            bottom_pixel = pixels[x, y+1]
            
            # 解析 RGBA
            tr, tg, tb, ta = top_pixel
            br, bg, bb, ba = bottom_pixel
            
            # 判断是否为白色背景
            top_is_white = (tr > 245 and tg > 245 and tb > 245)
            bottom_is_white = (br > 245 and bg > 245 and bb > 245)
            
            # 判断像素是否有效（非透明且非白色）
            top_visible = (ta > 128) and not top_is_white
            bottom_visible = (ba > 128) and not bottom_is_white
            
            # 【核心修改】纯粹依靠块状字符来绘制轮廓，没有任何颜色代码
            if not top_visible and not bottom_visible:
                line += " "  # 空格
            elif top_visible and not bottom_visible:
                line += "▀"  # 上半方块
            elif not top_visible and bottom_visible:
                line += "▄"  # 下半方块
            else:
                line += "█"  # 全方块
                
        # 行末换行
        line += "\n"
        ansi_lines.append(line)

    # 写入文件
    with open(output_path, "w", encoding="utf-8") as f:
        f.writelines(ansi_lines)
    print(f"[成功] {os.path.basename(image_path)} -> {os.path.basename(output_path)} (单色剪影)")

def main():
    input_dir = "role"
    output_dir = "resources"
    
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    for filename in os.listdir(input_dir):
        if filename.lower().endswith(".png"):
            input_path = os.path.join(input_dir, filename)
            # 输出文件名加上 _mono 后缀以区分
            output_name = filename.rsplit('.', 1)[0] + ".ans"
            output_path = os.path.join(output_dir, output_name)
            
            convert_image_to_monochrome_ansi(input_path, output_path, width=TARGET_WIDTH)

if __name__ == "__main__":
    main()
