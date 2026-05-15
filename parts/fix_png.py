from pathlib import Path
from PIL import Image
import sys

def clean_png(path: Path):
    try:
        with Image.open(path) as img:
            # Force clean RGBA/RGB conversion
            if img.mode in ("RGBA", "LA", "P"):
                img = img.convert("RGBA")
            else:
                img = img.convert("RGB")

            temp_path = path.with_suffix(".tmp.png")

            # Save clean stripped PNG
            img.save(
                temp_path,
                format="PNG",
                optimize=False,
                compress_level=6
            )

            temp_path.replace(path)

            print(f"[OK] {path}")

    except Exception as e:
        print(f"[FAIL] {path} -> {e}")


def main():
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")

    png_files = list(root.rglob("*.png"))

    print(f"Found {len(png_files)} PNG files")

    for png in png_files:
        clean_png(png)

    print("Done")


if __name__ == "__main__":
    main()