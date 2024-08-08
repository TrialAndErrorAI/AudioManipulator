from PIL import Image
import math

def create_rotated_frames(image_path, num_frames):
    img = Image.open(image_path)
    for i in range(num_frames):
        angle = (i / num_frames) * 360
        rotated = img.rotate(-angle, resample=Image.BICUBIC, expand=False)
        rotated.save(f"vinyl_rotation_{i:03d}.png")

if __name__ == "__main__":
    create_rotated_frames("vinylDisc.png", 60)