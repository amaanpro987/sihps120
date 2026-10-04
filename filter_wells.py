import csv

input_file = 'd:/projects/SIH-26/SIH-26/Wells-export.csv'
output_file = 'd:/projects/SIH-26/SIH-26/Baghewala_Wells.csv'

lat_min, lat_max = 24.0, 30.0
lon_min, lon_max = 69.0, 75.0

matched_wells = []
with open(input_file, 'r', encoding='utf-8-sig') as f:
    reader = csv.DictReader(f)
    fieldnames = reader.fieldnames
    for row in reader:
        try:
            lat = float(row['Latitude'])
            lon = float(row['Longitude'])
            if lat_min <= lat <= lat_max and lon_min <= lon <= lon_max:
                matched_wells.append(row)
        except (ValueError, TypeError, KeyError):
            continue

if matched_wells:
    print(f"Found {len(matched_wells)} wells in Rajasthan bounding box.")
    for w in matched_wells[:10]:
        print(f"{w.get('Well Name', '')} - Lat: {w.get('Latitude', '')}, Lon: {w.get('Longitude', '')} - Operator: {w.get('Well Operator', '')}")
    
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(matched_wells)
else:
    print("No wells found in the bounding box.")
