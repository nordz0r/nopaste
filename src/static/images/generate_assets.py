"""
Script to generate high-resolution PNG assets (goldfinches_logo.png and favicon.png)
matching the new Goldfinch logo design.
"""

from PIL import Image, ImageDraw


def draw_goldfinch_logo(size=512):
    # High resolution canvas for super-sampled anti-aliasing
    scale = 4
    w = size * scale
    h = size * scale

    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    _cx, _cy = w // 2, h // 2

    # Palette
    RED_MID = (229, 44, 44, 255)

    GOLD_MID = (255, 193, 7, 255)

    CHARCOAL_DARK = (15, 17, 19, 255)
    CHARCOAL_MID = (26, 29, 32, 255)

    CREAM_LIGHT = (255, 255, 255, 255)

    TAN_MID = (200, 155, 103, 255)

    BEAK_COLOR = (245, 235, 220, 255)

    # 1. Wooden Branch
    branch_pts = [
        (int(0.12 * w), int(0.83 * h)),
        (int(0.35 * w), int(0.81 * h)),
        (int(0.65 * w), int(0.84 * h)),
        (int(0.88 * w), int(0.88 * h)),
        (int(0.85 * w), int(0.89 * h)),
        (int(0.55 * w), int(0.85 * h)),
        (int(0.12 * w), int(0.84 * h)),
    ]
    draw.polygon(branch_pts, fill=(109, 76, 65, 220))

    # 2. Tail Feathers
    tail_pts = [
        (int(0.55 * w), int(0.70 * h)),
        (int(0.81 * w), int(0.88 * h)),
        (int(0.84 * w), int(0.84 * h)),
        (int(0.62 * w), int(0.64 * h)),
    ]
    draw.polygon(tail_pts, fill=CHARCOAL_DARK)

    # White tail accent line
    draw.line(
        [(int(0.64 * w), int(0.72 * h)), (int(0.80 * w), int(0.85 * h))],
        fill=(255, 255, 255, 200),
        width=int(8 * scale),
    )

    # 3. Body Back (Tan)
    body_bbox = [int(0.30 * w), int(0.31 * h), int(0.68 * w), int(0.74 * h)]
    draw.ellipse(body_bbox, fill=TAN_MID)

    # 4. Belly / Breast (Cream)
    breast_bbox = [int(0.33 * w), int(0.42 * h), int(0.58 * w), int(0.72 * h)]
    draw.ellipse(breast_bbox, fill=CREAM_LIGHT)

    # 5. Black Wing Structure
    wing_bbox = [int(0.42 * w), int(0.40 * h), int(0.75 * w), int(0.72 * h)]
    draw.ellipse(wing_bbox, fill=CHARCOAL_MID)

    # 6. Gold Wing Slash
    gold_pts = [
        (int(0.46 * w), int(0.44 * h)),
        (int(0.62 * w), int(0.48 * h)),
        (int(0.70 * w), int(0.59 * h)),
        (int(0.62 * w), int(0.59 * h)),
        (int(0.50 * w), int(0.50 * h)),
    ]
    draw.polygon(gold_pts, fill=GOLD_MID)

    # White wing spots
    for dot_pos in [(0.71, 0.65), (0.68, 0.68), (0.65, 0.70)]:
        dx, dy = int(dot_pos[0] * w), int(dot_pos[1] * h)
        dr = int(7 * scale)
        draw.ellipse([dx - dr, dy - dr, dx + dr, dy + dr], fill=(255, 255, 255, 255))

    # 7. White Collar Surround
    collar_bbox = [int(0.31 * w), int(0.28 * h), int(0.45 * w), int(0.42 * h)]
    draw.ellipse(collar_bbox, fill=CREAM_LIGHT)

    # 8. Black Hood Cap & Nape
    hood_bbox = [int(0.30 * w), int(0.20 * h), int(0.46 * w), int(0.32 * h)]
    draw.ellipse(hood_bbox, fill=CHARCOAL_DARK)

    # 9. Crimson Red Mask
    red_bbox = [int(0.20 * w), int(0.24 * h), int(0.34 * w), int(0.36 * h)]
    draw.ellipse(red_bbox, fill=RED_MID)

    # 10. Ivory Beak
    beak_pts = [
        (int(0.23 * w), int(0.29 * h)),
        (int(0.12 * w), int(0.31 * h)),
        (int(0.23 * w), int(0.35 * h)),
    ]
    draw.polygon(beak_pts, fill=BEAK_COLOR)
    draw.line(
        [(int(0.23 * w), int(0.29 * h)), (int(0.12 * w), int(0.31 * h))],
        fill=(210, 190, 170, 255),
        width=int(2 * scale),
    )

    # 11. Expressive Eye
    eye_x, eye_y = int(0.28 * w), int(0.29 * h)
    er = int(18 * scale)
    draw.ellipse([eye_x - er, eye_y - er, eye_x + er, eye_y + er], fill=CHARCOAL_DARK)
    ir = int(13 * scale)
    draw.ellipse(
        [eye_x - ir, eye_y - ir, eye_x + ir, eye_y + ir], fill=(15, 17, 19, 255)
    )
    hr = int(5 * scale)
    draw.ellipse(
        [
            eye_x - hr + int(2 * scale),
            eye_y - hr - int(2 * scale),
            eye_x + hr + int(2 * scale),
            eye_y + hr - int(2 * scale),
        ],
        fill=(255, 255, 255, 255),
    )

    # Downsample for crisp anti-aliased rendering
    out_img = img.resize((size, size), Image.Resampling.LANCZOS)
    return out_img


def main():
    print("Generating high-resolution PNG brand assets...")

    # 1. Main Brand Logo (512x512 PNG)
    logo = draw_goldfinch_logo(512)
    logo.save("goldfinches_logo.png", "PNG")
    print("Saved goldfinches_logo.png (512x512)")

    # 2. Favicon (64x64 PNG)
    favicon = draw_goldfinch_logo(64)
    favicon.save("favicon.png", "PNG")
    print("Saved favicon.png (64x64)")


if __name__ == "__main__":
    main()
