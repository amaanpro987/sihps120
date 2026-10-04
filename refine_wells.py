import csv

input_file = 'd:/projects/SIH-26/SIH-26/Baghewala_Wells.csv'
output_file = 'd:/projects/SIH-26/SIH-26/Baghewala_Exact_Wells.csv'

baghewala_wells = []
with open(input_file, 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    fieldnames = reader.fieldnames
    for row in reader:
        operator = row.get('Well Operator', '').upper()
        name = row.get('Well Name', '').upper()
        # OIL is Oil India Limited. CAIRN is Cairn India (which operates Mangala/Bhagyam/Aishwariya).
        # Baghewala is operated by OIL.
        if 'OIL' in operator or 'BAGH' in name or 'BGL' in name or 'BGW' in name:
            baghewala_wells.append(row)

print(f"Found {len(baghewala_wells)} possible Baghewala/OIL wells.")
for w in baghewala_wells[:20]:
    print(f"{w['Well Name']} - Operator: {w['Well Operator']}")

with open(output_file, 'w', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(baghewala_wells)
