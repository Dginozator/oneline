#!/usr/bin/env python3
"""
Usage: python ozon_export.py "path/to/Ozon.htm"
Output: {basename}_{DD_MM_YYYY_HH_MM}.zip рядом с htm
"""
import sys, os, json, re, zipfile
from io import BytesIO
from datetime import datetime
from pathlib import Path
from urllib.parse import unquote

try:
    from bs4 import BeautifulSoup
except ImportError:
    print("[err] нужен bs4: pip install beautifulsoup4")
    sys.exit(1)

try:
    from PIL import Image
except ImportError:
    print("[err] нужен Pillow: pip install Pillow")
    sys.exit(1)

if len(sys.argv) < 2:
    print("Usage: python ozon_export.py <path.htm>")
    sys.exit(1)

htm_path = Path(sys.argv[1]).resolve()
if not htm_path.is_file():
    print(f"File not found: {htm_path}")
    sys.exit(1)

base_dir = htm_path.parent
html = htm_path.read_text(encoding='utf-8', errors='replace')
soup = BeautifulSoup(html, 'html.parser')

def txt(el):
    return el.get_text(strip=True) if el else ''

# --- парсинг товаров ---
products = []
rows = soup.select('.row')
print(f"[*] rows: {len(rows)}")

for row in rows:
    meta = row.select_one('.meta')
    if not meta:
        continue
    sku = txt(meta.select_one('.sku'))
    name_a = meta.select_one('a.name')
    if not sku:
        continue

    images = []
    for ph in row.select('.ph'):
        img = ph.select_one('img')
        if not img or not img.get('src'):
            continue
        date = txt(ph.select_one('.date'))
        images.append({
            'url': img.get('src'),
            'originalUrl': img.get('data-original-src', ''),
            'lastModifiedFmt': '' if date == '…' else date,
        })
    if not images:
        continue

    sub_rate = meta.select_one('.sub .rate')
    s_rate = meta.select_one('.shop .srate')

    products.append({
        'sku': sku,
        'name': txt(name_a),
        'href': name_a.get('href', '') if name_a else '',
        'price': txt(meta.select_one('.price')),
        'oldPrice': txt(meta.select_one('.old')),
        'discount': txt(meta.select_one('.disc')),
        'rating': re.sub(r'^★\s*', '', txt(sub_rate)),
        'reviews': txt(meta.select_one('.sub .rev')),
        'seller': txt(meta.select_one('.shop .seller')),
        'sellerRating': re.sub(r'^★\s*', '', txt(s_rate)),
        'sellerOrders': txt(meta.select_one('.shop .sord')),
        'images': images,
    })

if not products:
    print("[err] нет товаров")
    sys.exit(1)

print(f"[*] products: {len(products)}")

# --- утилиты ---
EXT_RE = re.compile(r'\.(jpe?g|png|webp|gif|avif)$', re.I)

def guess_ext_from_path(p):
    m = EXT_RE.search(p)
    if not m:
        return None
    e = m.group(1).lower()
    return 'jpg' if e == 'jpeg' else e

def guess_ext_from_bytes(data):
    if data[:3] == b'\xff\xd8\xff': return 'jpg'
    if data[:8] == b'\x89PNG\r\n\x1a\n': return 'png'
    if data[:4] == b'RIFF' and data[8:12] == b'WEBP': return 'webp'
    if data[:6] in (b'GIF87a', b'GIF89a'): return 'gif'
    if data[4:12] in (b'ftypavif', b'ftypavis'): return 'avif'
    return 'jpg'

def resolve_local(src):
    if not src or src.startswith(('data:', 'http://', 'https://')):
        return None
    rel = unquote(src)
    p = (base_dir / rel).resolve()
    return p if p.is_file() else None

def maybe_resize(data, ext):
    """Возвращает (data, resized_bool). Если высота > 1200 — уменьшает."""
    try:
        with Image.open(BytesIO(data)) as img:
            if img.height <= 1200:
                return data, False
            new_w = max(1, round(img.width * 1200 / img.height))
            img_r = img.resize((new_w, 1200), Image.LANCZOS)
            buf = BytesIO()
            e = ext.lower()
            if e in ('jpg', 'jpeg'):
                if img_r.mode in ('RGBA', 'P', 'LA'):
                    img_r = img_r.convert('RGB')
                img_r.save(buf, 'JPEG', quality=90, optimize=True)
            elif e == 'png':
                img_r.save(buf, 'PNG', optimize=True)
            elif e == 'webp':
                img_r.save(buf, 'WEBP', quality=90)
            elif e == 'gif':
                img_r.save(buf, 'GIF')
            else:
                img_r.save(buf, format=img.format or 'JPEG')
            return buf.getvalue(), True
    except Exception as e:
        raise

# --- сборка архива ---
mtime = datetime.fromtimestamp(htm_path.stat().st_mtime)
stamp = mtime.strftime('%d_%m_%Y_%H_%M')
zip_name = f"{htm_path.stem}_{stamp}.zip"
zip_path = base_dir / zip_name

print(f"[*] writing: {zip_path}")

failed = 0
resized = 0
err_samples = []
total_imgs = sum(len(p['images']) for p in products)
done = 0

with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
    for p in products:
        for i, im in enumerate(p['images'], 1):
            done += 1
            local = resolve_local(im['url'])
            if local is None:
                im['file'] = None
                failed += 1
                if len(err_samples) < 5:
                    err_samples.append(f"not found: {im['url'][:80]}")
                continue
            try:
                data = local.read_bytes()
                if not data:
                    raise ValueError('empty')
                ext = guess_ext_from_path(local.name) or guess_ext_from_bytes(data)
                try:
                    data, was_resized = maybe_resize(data, ext)
                    if was_resized:
                        resized += 1
                except Exception as re_err:
                    if len(err_samples) < 5:
                        err_samples.append(f"resize skip {local.name}: {re_err}")
                arc = f"images/{p['sku']}/{i}.{ext}"
                im['file'] = arc
                zf.writestr(arc, data)
            except Exception as e:
                im['file'] = None
                failed += 1
                if len(err_samples) < 5:
                    err_samples.append(f"{local.name}: {e}")
            if done % 100 == 0 or done == total_imgs:
                print(f"  {done}/{total_imgs}  resized:{resized}  err:{failed}")

    meta_obj = {
        'sourceHtml': htm_path.name,
        'sourceMtime': mtime.isoformat(),
        'scrapedAt': datetime.now().isoformat(),
        'count': len(products),
        'failed': failed,
        'resized': resized,
        'products': products,
    }
    zf.writestr('data.json', json.dumps(meta_obj, ensure_ascii=False, indent=2))

size_mb = zip_path.stat().st_size / 1048576
print(f"[ok] {zip_name}  {size_mb:.1f} MB  imgs:{total_imgs - failed}/{total_imgs}  resized:{resized}  err:{failed}")
if err_samples:
    print("[err samples]")
    for s in err_samples:
        print(f"  {s}")