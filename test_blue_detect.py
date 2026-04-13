from PIL import Image
import sys

def check_blue_pixels(image_path):
    try:
        img = Image.open(image_path).convert('RGB')
        width, height = img.size
        # Let's check a strip on the left side: x from 0 to 100, y from 100 to height-100
        blue_pixels = 0
        total_pixels = 0
        
        for x in range(30, 200):
            for y in range(100, height - 100):
                r, g, b = img.getpixel((x, y))
                # The blue dots are bright blue, e.g., (0, 100, 255) approx
                if b > 150 and r < 100 and g < 200 and b > r * 1.5 and b > g * 1.1:
                    blue_pixels += 1
                total_pixels += 1
        
        ratio = blue_pixels / total_pixels
        print(f"Blue pixels: {blue_pixels}")
        print(f"Total pixels: {total_pixels}")
        print(f"Ratio: {ratio:.4f}")
        return ratio > 0.005 # at least 0.5% of pixels are blue
    except Exception as e:
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    check_blue_pixels(sys.argv[1])
