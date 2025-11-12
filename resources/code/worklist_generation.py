# pip install pillow treepoem
import csv
import string
from pathlib import Path
from PIL import Image
import treepoem

# -------------------
# CONFIG
# -------------------
DATA = "https://bit.ly/43Z3r0z"

# Symbol geometry you want to print (change as needed)
SYMBOL_ROWS = 32   # e.g., 32 for 32x32
SYMBOL_COLS = 32

# Plate geometry (384 = 16x24, 1536 = 32x48)
PLATE_ROWS = 32    # 32 for 1536-well
PLATE_COLS = 48    # 48 for 1536-well

# Placement on the plate
# e.g., center horizontally, top aligned; tweak as you like.
ROW_OFFSET = 0                              # 0-based plate row where symbol's row 0 goes
COL_OFFSET = (PLATE_COLS - SYMBOL_COLS)//2  # center horizontally

# Worklist fields
SOURCE_PLATE = "color_plate"
DEST_PLATE   = "art_plate"
SOURCE_WELL  = "A1"
VOLUME_NL    = 500

OUT_PNG = Path("dm_symbol.png")
OUT_CSV = Path("worklist.csv")

# -------------------
# 1) Generate the symbol at exact rows×cols (ECC200)
#    Use DMRE only when requesting a DMRE size like 16x24, 32x48, etc.
# -------------------
options = {"rows": str(SYMBOL_ROWS), "columns": str(SYMBOL_COLS)}
# If you ever pick a DMRE size (e.g., 16x24, 32x48), uncomment:
# options["dmre"] = "y"

img = treepoem.generate_barcode(
    barcode_type="datamatrix",
    data=DATA,
    options=options
).convert("1")   # 1-bit is crisp and easy to analyze
img.save(OUT_PNG)

# -------------------
# 2) Extract the tight symbol box (exclude quiet zone)
# -------------------
bw = img.copy()  # mode "1"
w, h = bw.size
px = bw.load()

# Find bounds of any black pixel (0 in "1" mode)
top = None
left = None
right = None
bottom = None

for y in range(h):
    for x in range(w):
        if px[x, y] == 0:  # black
            if top is None:  top = y
            bottom = y
            if left is None or x < left:   left = x
            if right is None or x > right: right = x

if top is None:
    raise RuntimeError("No black pixels found; symbol generation failed?")

# Tight content box (no quiet zone). Add +1 to right/bottom for inclusive->exclusive.
box_x0, box_y0 = left, top
box_x1, box_y1 = right + 1, bottom + 1
box_w = box_x1 - box_x0
box_h = box_y1 - box_y0

# Sanity: box should be divisible (ish) by module count
cell_w = box_w / SYMBOL_COLS
cell_h = box_h / SYMBOL_ROWS

# -------------------
# 3) Sample each module at its cell center to build a boolean grid
# -------------------
modules = [[0]*SYMBOL_COLS for _ in range(SYMBOL_ROWS)]

for r in range(SYMBOL_ROWS):
    for c in range(SYMBOL_COLS):
        cx = int(box_x0 + (c + 0.5) * cell_w)
        cy = int(box_y0 + (r + 0.5) * cell_h)
        # Clamp defensively
        cx = max(0, min(w-1, cx))
        cy = max(0, min(h-1, cy))
        modules[r][c] = 1 if px[cx, cy] == 0 else 0  # 1 = black, 0 = white

# -------------------
# 4) Map module grid to plate wells & write CSV worklist
# -------------------
if SYMBOL_ROWS > PLATE_ROWS or SYMBOL_COLS > PLATE_COLS:
    raise ValueError("Symbol larger than plate grid; reduce rows/cols or pick a bigger plate.")

def well_name(row_idx, col_idx):
    # row_idx, col_idx are 0-based plate coordinates
    # For 32-row plates, after Z comes AA, AB... (A..AF).
    # Build Excel-like row labels:
    def row_label(n):
        # 0->A, 25->Z, 26->AA, 31->AF (for 32 rows)
        label = ""
        n0 = n
        while True:
            n, rem = divmod(n, 26)
            label = chr(65 + rem) + label
            if n == 0:
                break
            n -= 1
        return label

    row = row_label(row_idx)
    col = col_idx + 1
    return f"{row}{col}"

rows_out = []
for r in range(SYMBOL_ROWS):
    for c in range(SYMBOL_COLS):
        if modules[r][c] == 1:
            plate_r = r + ROW_OFFSET
            plate_c = c + COL_OFFSET
            if not (0 <= plate_r < PLATE_ROWS and 0 <= plate_c < PLATE_COLS):
                continue  # skip if it falls outside plate area due to offsets
            dest = well_name(plate_r, plate_c)
            rows_out.append([SOURCE_PLATE, DEST_PLATE, SOURCE_WELL, dest, VOLUME_NL])

with OUT_CSV.open("w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["source_plate", "destination_plate", "source_well", "destination_well", "volume_nL"])
    writer.writerows(rows_out)

print(f"Symbol image   : {OUT_PNG.resolve()}")
print(f"Worklist (CSV) : {OUT_CSV.resolve()}  | rows: {len(rows_out)}")
