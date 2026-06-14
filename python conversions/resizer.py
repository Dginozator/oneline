#!/usr/bin/env python3
"""
Resize всех картинок в папке Ozon_files/ (рядом с указанным htm) до высоты 1200.
Перезаписывает файлы на месте. Картинки с height <= 1200 не трогает.

Usage: python ozon_resize.py "path/to/Ozon.htm"
       python ozon_resize.py "path/to/Ozon_files"   # можно указать папку напрямую
"""
import sys
from io import BytesIO
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    print("[err] нужен Pillow: pip install Pillow")
    sys.exit(1)

if len(sys.argv) < 2:
    print("Usage: python ozon_resize.py <path.htm | path/to/Ozon_files>")
    sys.exit(1)

arg = Path(sys.argv[1]).resolve()

if arg.is_file() and arg.suffix.lower() in ('.htm', '.html'):
    img_dir = arg.parent / f"{arg.stem}_files"
elif arg.is_dir():
    img_dir = arg
else:
    print(f"[err] не найдено: {arg}")
    sys.exit(1)

if not img_dir.is_dir():
    print(f"[err] папка с картинками не найдена: {img_dir}")
    sys.exit(1)

print(f"[*] dir: {img_dir}")

EXTS = {'.jpg', '.jpeg', '.png', '.webp', '.gif'}

files = [p for p in img_dir.rglob('*') if p.is_file() and p.suffix.lower() in EXTS]
total = len(files)
print(f"[*] files: {total}")

resized = 0
skipped = 0
failed = 0
saved_bytes = 0
err_samples = []

for idx, fp in enumerate(files, 1):
    try:
        orig_size = fp.stat().st_size
        with Image.open(fp) as img:
            if img.height <= 1200:
                skipped += 1
                continue
            new_w = max(1, round(img.width * 1200 / img.height))
            fmt = (img.format or '').upper()
            img_r = img.resize((new_w, 1200), Image.LANCZOS)

        buf = BytesIO()
        ext = fp.suffix.lower()
        if ext in ('.jpg', '.jpeg'):
            if img_r.mode in ('RGBA', 'P', 'LA'):
                img_r = img_r.convert('RGB')
            img_r.save(buf, 'JPEG', quality=90, optimize=True)
        elif ext == '.png':
            img_r.save(buf, 'PNG', optimize=True)
        elif ext == '.webp':
            img_r.save(buf, 'WEBP', quality=90)
        elif ext == '.gif':
            img_r.save(buf, 'GIF')
        else:
            img_r.save(buf, format=fmt or 'JPEG')

        new_data = buf.getvalue()
        fp.write_bytes(new_data)
        diff = orig_size - len(new_data)
        if diff > 0:
            saved_bytes += diff
        resized += 1
    except Exception as e:
        failed += 1
        if len(err_samples) < 5:
            err_samples.append(f"{fp.name}: {e}")

    if idx % 100 == 0 or idx == total:
        print(f"  {idx}/{total}  resized:{resized}  skip:{skipped}  err:{failed}")

print(f"[ok] resized:{resized}  skipped:{skipped}  failed:{failed}  saved:{saved_bytes/1048576:.1f} MB")
if err_samples:
    print("[err samples]")
    for s in err_samples:
        print(f"  {s}")