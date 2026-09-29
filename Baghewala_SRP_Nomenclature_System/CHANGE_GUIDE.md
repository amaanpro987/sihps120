
# How to change the nomenclature database

## Easiest method

Open `nomenclature_lookup.py`.

Find the `SEED = [` section.

Each record has:

```python
{
    "name": "C-320D-246-86",
    "category": "OIL Baghewala SRP surface unit",
    "description": "...",
    "source_type": "OIL",
    "source_reference": "...",
    "source_url": "...",
    "aliases": ["C320D24686", "320D-246-86"],
    "parameters": [
        ("Maximum stroke length", "86", "in", ""),
        ("SPM", "3", "SPM", "Only if documented for this exact equipment/well"),
    ],
}
```

### To add a new model

Copy one dictionary and change `name`, `category`, source and parameters.

Example:

```python
{
    "name": "MY-OIL-MODEL",
    "category": "SRP surface unit",
    "description": "Your documented unit",
    "source_type": "OIL",
    "source_reference": "Document name/page",
    "source_url": "official OIL URL",
    "aliases": ["MYMODEL", "model synonym"],
    "parameters": [
        ("Stroke", "72", "in", ""),
        ("SPM", "3", "SPM", ""),
        ("Reducer torque", "123000", "in-lb", ""),
    ],
}
```

Then delete `nomenclature.db` once if you want the seed data to rebuild from scratch,
and run:

```bash
python nomenclature_lookup.py MY-OIL-MODEL
```

## Better method for a production project

Do NOT edit the Python code every time.

Create a separate `nomenclature_data.json` or CSV and build an admin page where you can:

- Add nomenclature
- Edit a parameter
- Delete a parameter
- Add aliases
- Add source document
- Add source page
- Set `source_type = OIL / API / FIELD_MEASURED / VENDOR`
- Set `confidence = documented / measured / inferred`
- Set effective date

## Recommended source hierarchy

1. FIELD_MEASURED — actual VFD/dynamometer/production data
2. OIL_OFFICIAL — OIL tender, well file, completion record
3. VENDOR — actual equipment datasheet
4. API — standard/specification
5. ENGINEERING_ASSUMPTION — temporary value only

Never overwrite a measured value with an API nominal value.

## Recommended nomenclature fields

Every item should have:

- nomenclature
- aliases
- equipment type
- parameter
- value
- unit
- source type
- document
- page
- effective date
- well
- notes
- confidence

This makes the database auditable.
