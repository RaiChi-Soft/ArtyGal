from PIL import Image
import glob

for file in glob.glob("*.png"):
    with Image.open(file) as img:
        print(f"{file}: {img.size}")