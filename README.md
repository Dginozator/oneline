# Ozon Oneline Scraper

A set of tools for collecting product data and images from the [Ozon](https://www.ozon.ru) marketplace: a browser bookmarklet that builds a product grid in the page, and two Python scripts that process the saved page into a structured archive.

## How it works

1. The **bookmarklet** (`bookmarklets/ozon_oneline.js`) is added to the browser. When triggered on an Ozon search page, it replaces the page content with a custom product grid (SKU, name, price, rating, reviews, seller, and image thumbnails with `Last-Modified` dates) and lazily loads additional products as you scroll.
2. The page is then saved to disk as a complete webpage (`.htm` + a `_files/` folder with all assets).
3. Two Python scripts process the saved page:
   - `resizer.py` --- downscales images so their height is at most 1200 px (aspect ratio preserved), rewriting files in place.
   - `p_1200.py` --- parses the `.htm`, collects product metadata and images, and packs everything into a ZIP archive (`{name}_{DD_MM_YYYY_HH_MM}.zip`) containing `data.json` and the images organized into folders by SKU.

## Prerequisites

- Python 3
- Pillow: `pip install Pillow`
- BeautifulSoup4: `pip install beautifulsoup4`

## Step-by-step workflow

1. Add the bookmarklet `bookmarklets/ozon_oneline.js` to your browser.
2. Open the marketplace (ozon.ru).
3. Enter a search query.
4. Click the bookmarklet.
5. Gradually scroll to load the desired number of products. The recommended value is **1000**; loading 3500 products consumes roughly **8 GB of RAM** per tab.
6. In the browser's developer tools (Network tab), make sure all `GET` and `HEAD` requests complete in time --- if requests stall, slow down or pause scrolling.
7. Save everything as a webpage. **Make sure to wait until saving finishes --- do not close the tab early!**
8. Move the saved page (`.htm` + `_files/` folder) wherever you need it.
9. Run the resizer:
   ```bash
   python "python conversions/resizer.py" page.htm
   ```
10. Run the exporter:
    ```bash
    python "python conversions/p_1200.py" page.htm
    ```

`resizer.py` brings every image to a height of no more than 1200 px, preserving the aspect ratio. `p_1200.py` creates an archive with `data.json` and images arranged by SKU.

## Notes

- Save the page as a **complete webpage** ("Webpage, Complete") so the `_files/` folder with the images is created next to the `.htm`.
- `resizer.py` edits images in place --- keep a backup if you need the originals.
- `p_1200.py` also resizes images on the fly if any are still taller than 1200 px, so running it without `resizer.py` first will still work (but running both is faster for large sets).