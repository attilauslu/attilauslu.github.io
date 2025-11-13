import treepoem

DATA = "https://bit.ly/43Z3r0z"  # fits easily in 32×32

img = treepoem.generate_barcode(
    barcode_type="datamatrix",          # ECC200 (default)
    data=DATA,
    options={"rows": "32", "columns": "32"}  # force 32×32 symbol
)
img.convert("1").save("datamatrix_bitly_32x32.png")
print("Saved datamatrix_bitly_32x32.png")
