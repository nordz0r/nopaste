"""
Remove background from generated logos and save transparent PNG assets.
"""

from PIL import Image
import os


def remove_white_bg(input_path, output_path, threshold=235):
    img = Image.open(input_path).convert("RGBA")
    datas = img.getdata()

    new_data = []
    for item in datas:
        r, g, b, a = item
        # If pixel is near white background
        if r >= threshold and g >= threshold and b >= threshold:
            new_data.append((255, 255, 255, 0))
        else:
            # Smooth anti-aliased transparency on edge pixels
            avg = (r + g + b) / 3
            if avg > 210:
                alpha = int(255 * (255 - avg) / (255 - 210))
                new_data.append((r, g, b, max(0, min(255, alpha))))
            else:
                new_data.append((r, g, b, 255))

    img.putdata(new_data)

    # Trim transparent padding
    bbox = img.getbbox()
    if bbox:
        pad = 20
        left = max(0, bbox[0] - pad)
        upper = max(0, bbox[1] - pad)
        right = min(img.width, bbox[2] + pad)
        lower = min(img.height, bbox[3] + pad)
        img = img.crop((left, upper, right, lower))

    img.save(output_path, "PNG")
    print(f"Saved transparent PNG: {output_path} ({img.width}x{img.height})")
    return img


def main():
    v1_path = "/mnt/c/Users/Legion/.gemini/antigravity/brain/fbbcfcd0-1ac0-411a-90c1-538dd9183086/nopaste_goldfinch_logo_v1_1786056744378.jpg"
    v2_path = "/mnt/c/Users/Legion/.gemini/antigravity/brain/fbbcfcd0-1ac0-411a-90c1-538dd9183086/nopaste_goldfinch_logo_v2_1786056756815.jpg"

    out_dir = "/mnt/c/Users/Legion/OneDrive/Projects/nopaste/src/static/images"

    # Process V1 as main logo
    img_v1 = remove_white_bg(v1_path, os.path.join(out_dir, "goldfinches_logo.png"))
    img_v1.save(os.path.join(out_dir, "logo-goldfinch.png"), "PNG")

    # Process V2 as secondary variant
    remove_white_bg(v2_path, os.path.join(out_dir, "logo-goldfinch-v2.png"))

    # Create Favicon (64x64 transparent)
    fav_size = (64, 64)
    fav = Image.new("RGBA", fav_size, (0, 0, 0, 0))
    aspect = img_v1.width / img_v1.height
    if aspect >= 1:
        nw = 56
        nh = int(56 / aspect)
    else:
        nh = 56
        nw = int(56 * aspect)

    resized_v1 = img_v1.resize((nw, nh), Image.Resampling.LANCZOS)
    fav.paste(resized_v1, ((64 - nw) // 2, (64 - nh) // 2), resized_v1)
    fav.save(os.path.join(out_dir, "favicon.png"), "PNG")
    print("Saved transparent favicon.png (64x64)")


if __name__ == "__main__":
    main()
