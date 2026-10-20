"""
Utility script to generate sample demonstration images using Pillow.
These are clearly labeled as synthetic demonstration assets.
"""

from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

BASE_DIR = Path(__file__).resolve().parent.parent
SAMPLE_IMG_DIR = BASE_DIR / "sample_images"
SAMPLE_IMG_DIR.mkdir(parents=True, exist_ok=True)


def create_annotated_image(
    filename: str,
    title: str,
    subtitle: str,
    bg_color: tuple,
    text_color: tuple = (255, 255, 255),
    accent_color: tuple = (255, 255, 255),
    width: int = 800,
    height: int = 500,
    overwrite: bool = False,
):
    """Generate a clean visual card with title, subtitle, and demo badge if not already existing."""
    out_path = SAMPLE_IMG_DIR / filename
    if out_path.exists() and not overwrite:
        return str(out_path)
    img = Image.new("RGB", (width, height), color=bg_color)
    draw = ImageDraw.Draw(img)

    # Draw stylish accent header bar
    draw.rectangle([(0, 0), (width, 16)], fill=accent_color)

    # Draw demo watermark banner
    draw.rectangle([(0, height - 40), (width, height)], fill=(30, 41, 59))
    draw.text((20, height - 28), "[ DEMO ASSET - FOR DEMONSTRATION PURPOSES ONLY ]", fill=(203, 213, 225))

    # Inner card frame
    draw.rounded_rectangle([(30, 40), (width - 30, height - 60)], radius=16, outline=accent_color, width=3)

    # Center text box
    draw.text((60, 90), title, fill=text_color)
    draw.text((60, 150), subtitle, fill=(226, 232, 240))
    draw.text((60, 220), "• Synthetic Demonstration Graphic", fill=(203, 213, 225))
    draw.text((60, 260), "• Simulates camera photograph for image validation", fill=(203, 213, 225))

    out_path = SAMPLE_IMG_DIR / filename
    img.save(out_path, format="PNG")
    return str(out_path)


def generate_all_sample_assets():
    """Create sample space photos and complaint evidence images."""
    # Coworking space photos
    spaces = [
        ("space_meeting_room_a.png", "Meeting Room A", "6 People | AV Projector | Navi Mumbai", (30, 58, 138), (59, 130, 246)),
        ("space_exec_cabin.png", "Executive Cabin 101", "2 People | Smart Lock Access | Mumbai BKC", (15, 118, 110), (20, 184, 166)),
        ("space_dedicated_desk.png", "Dedicated Quiet Desk #12", "1 Person | High-Speed LAN | Pune Baner", (67, 56, 202), (99, 102, 241)),
        ("space_media_studio.png", "Creative Media Studio B", "8 People | Acoustic 4K AV | Bengaluru", (147, 51, 234), (192, 132, 252)),
        ("space_day_pass.png", "Open Hot Desk Day Pass", "1 Person | Flexible Seating | Mumbai Andheri", (194, 65, 12), (249, 115, 22)),
    ]

    for filename, title, subtitle, bg, accent in spaces:
        create_annotated_image(filename, f"COWORKING SPACE: {title}", subtitle, bg, accent_color=accent)

    # Complaint evidence photos
    evidence = [
        ("projector_broken.png", "EVIDENCE: Projector in Meeting Room A", "Ceiling-mounted projector with no signal / power off", (51, 65, 85), (239, 68, 68)),
        ("router_wifi.png", "EVIDENCE: Wi-Fi Router Hardware", "TP-Link Dual-band Router on shelf with blinking green LED", (30, 41, 59), (59, 130, 246)),
        ("garbage_bin_mismatch.png", "EVIDENCE: Plastic Waste Bin & Trash", "Plastic garbage bin with discarded coffee cups in hallway", (69, 10, 10), (239, 68, 68)),
        ("damaged_chair.png", "EVIDENCE: Damaged Ergonomic Office Chair", "Office chair with torn armrest upholstery and cracked wheel", (88, 28, 135), (217, 70, 239)),
        ("locked_cabin_door.png", "EVIDENCE: Locked Cabin Door with Digital Keypad", "Digital keypad showing locked state and host access alert", (76, 29, 149), (236, 72, 153)),
    ]

    for filename, title, subtitle, bg, accent in evidence:
        create_annotated_image(filename, title, subtitle, bg, accent_color=accent)

    print("Sample visual assets created successfully in sample_images/ directory.")


if __name__ == "__main__":
    generate_all_sample_assets()
