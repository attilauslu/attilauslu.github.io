# Re-run the simulation (the previous Python state was reset).

from PIL import Image, ImageDraw, ImageFont
import numpy as np

DATA = "https://bit.ly/43Z3r0z"
ROWS, COLS = 32, 32      # Data Matrix module grid to simulate
DOT_RADIUS = 20          # radius of the "droplet" in pixels
WALL = 4               # grid wall thickness in pixels
CELL = 48                # total cell size for each well cell (including walls)
MARGIN_CELLS = 1         # quiet zone in cells

# Try to build a real matrix using treepoem if available
matrix = None
try:
    import treepoem
    img = treepoem.generate_barcode(
        barcode_type="datamatrix",
        data=DATA,
        options={"rows": str(ROWS), "columns": str(COLS)}
    ).convert("1")
    bw = img.copy()
    w, h = bw.size
    px = bw.load()

    # Find tight content box (exclude quiet zone around symbol)
    top = left = None
    right = bottom = None
    for y in range(h):
        for x in range(w):
            if px[x, y] == 0:
                if top is None: top = y
                bottom = y
                if left is None or x < left: left = x
                if right is None or x > right: right = x
    if top is None:
        raise RuntimeError("No black pixels found in generated barcode.")

    tight = bw.crop((left, top, right+1, bottom+1))
    tight_rs = tight.resize((COLS, ROWS), Image.NEAREST)
    arr = np.array(tight_rs)
    matrix = (arr == 0).astype(np.uint8)
except Exception:
    # Fallback synthetic matrix (for visualization only)
    matrix = np.zeros((ROWS, COLS), dtype=np.uint8)
    # Left & bottom solid finder; top/right alternating clock track
    matrix[:, 0] = 1
    matrix[-1, :] = 1
    matrix[0, 1:] = np.arange(COLS-1) % 2
    matrix[1:-1, -1] = np.arange(ROWS-2) % 2
    # Random inner data just to visualize
    rng = np.random.default_rng(7)
    matrix[1:-1, 1:-1] = rng.integers(0, 2, size=(ROWS-2, COLS-2))

# Build canvas (with quiet-zone margin)
out_w = (COLS + 2*MARGIN_CELLS) * CELL + WALL
out_h = (ROWS + 2*MARGIN_CELLS) * CELL + WALL
canvas = Image.new("RGB", (out_w, out_h), "white")
draw = ImageDraw.Draw(canvas)

def draw_well(cx, cy, radius, filled, gloss=True):
    # No rim outline — clean white background
    if filled:
        drop_r = int(radius * 0.8)
        draw.ellipse([cx - drop_r, cy - drop_r,
                      cx + drop_r, cy + drop_r], fill="black")
        if gloss:
            hl_r = int(drop_r * 0.35)
            draw.ellipse([cx - int(0.5 * drop_r), cy - int(0.5 * drop_r),
                          cx - int(0.5 * drop_r) + hl_r,
                          cy - int(0.5 * drop_r) + hl_r],
                         fill=(90, 90, 90))

# Draw walls (grid)
for r in range(ROWS + 2*MARGIN_CELLS + 1):
    y = r * CELL
    draw.rectangle([0, y, out_w, y + WALL], fill="white")
for c in range(COLS + 2*MARGIN_CELLS + 1):
    x = c * CELL
    draw.rectangle([x, 0, x + WALL, out_h], fill="white")

# Draw wells
for rr in range(ROWS):
    for cc in range(COLS):
        origin_x = (cc + MARGIN_CELLS) * CELL + WALL
        origin_y = (rr + MARGIN_CELLS) * CELL + WALL
        cx = origin_x + (CELL - WALL) // 2
        cy = origin_y + (CELL - WALL) // 2
        draw_well(cx, cy, DOT_RADIUS, filled=bool(matrix[rr, cc]))

# Label
try:
    font = ImageFont.load_default()
    draw.text((10, 10), f"Simulated wells for Data Matrix {ROWS}x{COLS}", fill=(0,0,0), font=font)
except Exception:
    pass

out_path = "datamatrix_well_simulation.png"
canvas.save(out_path)
out_path
