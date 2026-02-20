import re
import cv2
from pathlib import Path

IMG_RE = re.compile(r"IMG(\d+)", re.IGNORECASE)
OFF_RE = re.compile(r"OFFSET([-+]?\d*\.?\d+(?:[eE][-+]?\d+)?)", re.IGNORECASE)

IMG_EXTS = {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff", ".webp"}

def parse_img_no(name: str):
    m = IMG_RE.search(name)
    return int(m.group(1)) if m else None

def parse_offset_value(name: str):
    m = OFF_RE.search(name)
    return m.group(1) if m else None

def put_overlay(img, text: str):
    # Pick font scale based on width so it looks reasonable across resolutions
    h, w = img.shape[:2]
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = max(0.6, min(1.6, w / 1000.0))
    thickness = max(1, int(round(font_scale * 2)))

    # Position near top-left with padding
    x, y = 20, int(30 * font_scale) + 10

    # Background box for readability
    (tw, th), baseline = cv2.getTextSize(text, font, font_scale, thickness)
    pad = int(10 * font_scale)
    x1, y1 = x - pad, y - th - pad
    x2, y2 = x + tw + pad, y + baseline + pad
    x1, y1 = max(0, x1), max(0, y1)
    x2, y2 = min(w - 1, x2), min(h - 1, y2)

    overlay = img.copy()
    cv2.rectangle(overlay, (x1, y1), (x2, y2), (0, 0, 0), -1)
    # Slight transparency
    cv2.addWeighted(overlay, 0.45, img, 0.55, 0, img)

    # White text
    cv2.putText(img, text, (x, y), font, font_scale, (255, 255, 255), thickness, cv2.LINE_AA)

def make_video(
    input_dir: str,
    output_path: str,
    fps: float = 1.0,          # 1 second per image
    resize_mode: str = "first" # "first" or "max"
):
    in_dir = Path(input_dir)
    out_path = Path(output_path)

    files = [p for p in in_dir.iterdir() if p.is_file() and p.suffix.lower() in IMG_EXTS]

    items = []
    for p in files:
        img_no = parse_img_no(p.name)
        if img_no is None:
            continue  # ignore files without IMG{NO}
        off = parse_offset_value(p.name)
        items.append((img_no, p, off))

    if not items:
        raise RuntimeError(f"No images with IMG{{NO}} found in: {in_dir}")

    # Sort by IMG number
    items.sort(key=lambda t: t[0])

    # Read images once to determine sizing strategy
    frames = []
    max_w = max_h = 0
    first_size = None

    for img_no, p, off in items:
        img = cv2.imread(str(p), cv2.IMREAD_COLOR)
        if img is None:
            print(f"[WARN] Could not read: {p}")
            continue
        h, w = img.shape[:2]
        if first_size is None:
            first_size = (w, h)
        max_w, max_h = max(max_w, w), max(max_h, h)
        frames.append((img_no, img, off, p.name))

    if not frames:
        raise RuntimeError("All candidate images failed to load.")

    if resize_mode.lower() == "max":
        target_w, target_h = max_w, max_h
    else:
        target_w, target_h = first_size

    # Video writer
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(out_path), fourcc, fps, (target_w, target_h))

    if not writer.isOpened():
        raise RuntimeError(
            "Failed to open VideoWriter. Try output as .avi or install proper codecs."
        )

    # Write frames
    for img_no, img, off, fname in frames:
        if (img.shape[1], img.shape[0]) != (target_w, target_h):
            img = cv2.resize(img, (target_w, target_h), interpolation=cv2.INTER_AREA)

        off_text = off if off is not None else "N/A"
        text = f"OFFSET {off_text}"
        put_overlay(img, text)
        writer.write(img)

    writer.release()
    print(f"[OK] Wrote video: {out_path}")
    print(f"[OK] Frames: {len(frames)}  FPS: {fps}  Size: {target_w}x{target_h}")

if __name__ == "__main__":
    # Example usage:
    #   python make_video.py /path/to/images out.mp4
    import sys
    if len(sys.argv) < 3:
        print("Usage: python make_video.py <input_folder> <output.mp4> [fps]")
        sys.exit(1)

    input_folder = sys.argv[1]
    output_file = sys.argv[2]
    fps = float(sys.argv[3]) if len(sys.argv) >= 4 else 1.0

    make_video(input_folder, output_file, fps=fps, resize_mode="first")

