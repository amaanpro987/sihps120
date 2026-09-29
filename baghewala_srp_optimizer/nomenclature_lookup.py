
"""
Baghewala SRP nomenclature lookup database.

Usage:
    python nomenclature_lookup.py C-320D-246-86
    python nomenclature_lookup.py BGW#4
    python nomenclature_lookup.py "API 11L"
    python nomenclature_lookup.py "7/8 sucker rod"
    python nomenclature_lookup.py --list
    python nomenclature_lookup.py --add my_name "My description" "field=value;field=value"

The database is deliberately source-aware:
- OIL documents = Baghewala/well/equipment-specific information.
- API = standard/specification scope, not a Baghewala operating measurement.
"""

import sqlite3
import sys
from pathlib import Path

DB = Path(__file__).with_name("nomenclature.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS nomenclature (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    category TEXT NOT NULL,
    description TEXT,
    source_type TEXT NOT NULL,
    source_reference TEXT,
    source_url TEXT
);

CREATE TABLE IF NOT EXISTS parameters (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nomenclature_id INTEGER NOT NULL,
    parameter TEXT NOT NULL,
    value TEXT,
    unit TEXT,
    notes TEXT,
    FOREIGN KEY(nomenclature_id) REFERENCES nomenclature(id)
);

CREATE TABLE IF NOT EXISTS aliases (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nomenclature_id INTEGER NOT NULL,
    alias TEXT UNIQUE NOT NULL,
    FOREIGN KEY(nomenclature_id) REFERENCES nomenclature(id)
);
"""

SEED = [
    {
        "name": "C-320D-246-86",
        "category": "OIL Baghewala SRP surface unit",
        "description": "Conventional SRP surface unit specified by OIL for wells of Baghewala field.",
        "source_type": "OIL",
        "source_reference": "OIL Tender SJI6697P22",
        "source_url": "https://www.oil-india.com/files/oldtender/national/NIT_SJI6697P22.pdf",
        "aliases": ["C320D24686", "C-320-D-246-86", "320D-246-86"],
        "parameters": [
            ("Model", "C-320D-246-86", "", ""),
            ("API surface-unit specification", "API 11E", "", "OIL tender says API 11E."),
            ("Balance", "Beam Balance", "", ""),
            ("Product", "Standard Rocking Horse", "", ""),
            ("Reducer rating", "320", "10^3 in-lb", ""),
            ("Structural capacity", "246", "10^2 lb", "OIL tender formatting gives 246 × 10^2 lb = 24,600 lb."),
            ("Maximum stroke length", "86", "in", ""),
            ("Available stroke lengths", "86; 74; 61", "in", ""),
            ("Polish rod capacity", "24,600", "lb", ""),
            ("Well lifting capacity", "60-120", "bbl/day", ""),
            ("Electrical supply", "380/220", "V", ""),
            ("Walking beam", "W24 x 117", "", ""),
            ("Unit weight", "16-20", "ton", ""),
        ],
    },
    {
        "name": "C-912D-365-168",
        "category": "OIL SRP surface-unit fact sheet",
        "description": "Conventional SRP surface unit listed in an OIL production fact sheet.",
        "source_type": "OIL",
        "source_reference": "OIL Sucker Rod Pump Product Fact Sheet",
        "source_url": "https://www.oil-india.com/files/2024-01/SUCKER_ROD_PUMP_Fact_Sheet.pdf",
        "aliases": ["C912D365168", "C-912-D-365-168"],
        "parameters": [
            ("Designation", "C-912D-365-168", "", ""),
            ("Manufacturing standard", "API 11E", "", ""),
            ("Gear reducer torque rating", "912,000", "in-lb", ""),
            ("Structural capacity", "36,500", "lb", ""),
            ("Stroke lengths", "168; 144; 124", "in", ""),
            ("Strokes per minute", "5; 7; 9", "SPM", ""),
            ("Gear reducer operating speed", "Manufacturer designed", "", ""),
        ],
    },
    {
        "name": "BGW#4",
        "category": "Baghewala well / downhole SRP configuration",
        "description": "Documented OIL well-engineering configuration for Baghewala Well No. 4.",
        "source_type": "OIL",
        "source_reference": "OIL Annexure-I, Tender CJI5659P15",
        "source_url": "https://www.oil-india.com/files/oldtender/national/CJI5659P15.pdf",
        "aliases": ["BGW4", "Baghewala Well 4", "Baghewala well no. 4", "Baghewala-4"],
        "parameters": [
            ("Total depth (driller)", "1150.0", "m", ""),
            ("Total depth (logger)", "1151.9", "m", ""),
            ("7 in casing shoe", "1147.0", "mbdf", ""),
            ("7 in FC", "1123.92", "mbdf", ""),
            ("Current perforation range", "1089.5-1095.5", "mbdf", ""),
            ("2-7/8 in tubing shoe", "1116.47", "mbdf", "EUE N-80 tubing"),
            ("Subsurface pump barrel depth", "1017.00", "mbdf", ""),
            ("Tubing", "2-7/8 in EUE N-80", "", ""),
            ("Plunger rod", "2.25", "in; 1 No.", ""),
            ("Sinker bars", "1.5", "in; 10 Nos.", ""),
            ("Sucker rods", "7/8", "in; 85 Nos.", ""),
            ("Sucker rods", "1", "in; 44 Nos.", ""),
            ("Pony rods", "1.5", "in; 2 Nos.", ""),
            ("Polish rod", "1.5", "in; 1 No.", ""),
        ],
    },
    {
        "name": "Baghewala SRP design envelope",
        "category": "Baghewala field",
        "description": "OIL tender parameters used for SRP unit design in Baghewala field.",
        "source_type": "OIL",
        "source_reference": "OIL Tender SJI6697P22",
        "source_url": "https://www.oil-india.com/files/oldtender/national/NIT_SJI6697P22.pdf",
        "aliases": ["Baghewala", "BGW", "Baghewala field", "Baghewala SRP"],
        "parameters": [
            ("Casing sizes", "5.5 and 7", "in", "OIL tender"),
            ("Wellhead", "5000", "psi", "X-mas tree"),
            ("Bottom-hole temperature", "45-55", "deg C", ""),
            ("Perforation depth", "1150-1200", "m", "Approximate"),
            ("Well depth", "1200-1300", "m", "Approximate"),
            ("Tubing OD", "2-7/8", "in", ""),
            ("Tubing grade", "13% Cr, L80", "", ""),
            ("Tubing weight", "9.52-9.67", "kg/m", "6.4-6.5 ppf"),
            ("Steam temperature", "340", "deg C", "CSS design condition in this tender"),
            ("Steam pressure", "2400", "psi", "CSS design condition in this tender"),
            ("Target reduced speed", "3", "SPM", "Tender asks gear configuration to reduce SPM to 3 because oil viscosity is very high."),
        ],
    },
    {
        "name": "API 11E",
        "category": "API standard",
        "description": "API Specification for pumping units.",
        "source_type": "API",
        "source_reference": "API Spec 11E",
        "source_url": "https://www.api.org/products-and-services/standards/digital-catalog",
        "aliases": ["11E", "API-11E", "pumping unit"],
        "parameters": [
            ("Scope", "Pumping units", "", "Surface pumping-unit specification."),
        ],
    },
    {
        "name": "API TR 11L",
        "category": "API standard",
        "description": "Design calculations for conventional sucker-rod pumping systems.",
        "source_type": "API",
        "source_reference": "API TR 11L, Fifth Edition",
        "source_url": "https://www.api.org/~/media/files/publications/2020_catalog/exploration_and_production.pdf",
        "aliases": ["11L", "API 11L", "API RP 11L"],
        "parameters": [
            ("Minimum design inputs", "fluid level; pump depth; pumping speed; surface stroke; plunger diameter; fluid specific gravity; tubing diameter/support; sucker-rod size/design", "", ""),
            ("Calculated outputs", "plunger stroke; pump displacement; PPRL; MPRL; peak crank torque; PRHP; counterbalance", "", ""),
            ("Caution", "Average/normal pumping wells; unusual conditions can deviate", "", ""),
        ],
    },
    {
        "name": "API 11AX",
        "category": "API standard",
        "description": "Subsurface sucker rod pump assemblies, components and fittings.",
        "source_type": "API",
        "source_reference": "API Spec 11AX",
        "source_url": "https://www.api.org/products-and-services/standards/digital-catalog",
        "aliases": ["11AX", "API-11AX", "subsurface pump"],
        "parameters": [
            ("Scope", "Subsurface sucker rod pump assemblies, components and fittings", "", ""),
            ("Important distinction", "Specifies pump/component requirements; it does not provide Baghewala well operating values.", "", ""),
        ],
    },
    {
        "name": "API 11B",
        "category": "API standard",
        "description": "Sucker rods and rod-related products.",
        "source_type": "API",
        "source_reference": "API Spec 11B",
        "source_url": "https://www.api.org/products-and-services/standards/digital-catalog",
        "aliases": ["11B", "API-11B", "sucker rod"],
        "parameters": [
            ("Scope", "Sucker rods and rod-related products", "", ""),
        ],
    },
]

def connect():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys=ON")
    return con

def init():
    con = connect()
    con.executescript(SCHEMA)
    con.commit()
    con.close()

def seed():
    init()
    con = connect()
    for item in SEED:
        row = con.execute("SELECT id FROM nomenclature WHERE name=?", (item["name"],)).fetchone()
        if row:
            continue
        cur = con.execute("""
            INSERT INTO nomenclature(name,category,description,source_type,source_reference,source_url)
            VALUES(?,?,?,?,?,?)
        """, (item["name"], item["category"], item["description"],
              item["source_type"], item["source_reference"], item["source_url"]))
        nid = cur.lastrowid
        for p, v, u, n in item["parameters"]:
            con.execute("""
                INSERT INTO parameters(nomenclature_id,parameter,value,unit,notes)
                VALUES(?,?,?,?,?)
            """, (nid,p,v,u,n))
        for a in item["aliases"]:
            con.execute("INSERT OR IGNORE INTO aliases(nomenclature_id,alias) VALUES(?,?)", (nid,a))
    con.commit()
    con.close()

def normalize(s):
    return "".join(ch.lower() for ch in s if ch.isalnum())

def lookup(query):
    q = normalize(query)
    con = connect()
    rows = con.execute("""
        SELECT DISTINCT n.* FROM nomenclature n
        LEFT JOIN aliases a ON a.nomenclature_id=n.id
        WHERE lower(n.name) LIKE ? OR lower(n.category) LIKE ?
           OR lower(n.description) LIKE ? OR lower(a.alias) LIKE ?
    """, (f"%{query.lower()}%",)*4).fetchall()

    # normalized exact/contains match for model nomenclature
    if not rows:
        allrows = con.execute("""
            SELECT DISTINCT n.* FROM nomenclature n
            LEFT JOIN aliases a ON a.nomenclature_id=n.id
        """).fetchall()
        rows = [
            r for r in allrows
            if q in normalize(r["name"]) or q in normalize(r["category"])
            or q in normalize(r["description"] or "")
            or any(q in normalize(x["alias"]) for x in con.execute(
                "SELECT alias FROM aliases WHERE nomenclature_id=?", (r["id"],)
            ))
        ]

    for r in rows:
        print("\n" + "="*72)
        print(f"{r['name']}  |  {r['category']}")
        print(f"Source: {r['source_type']} | {r['source_reference']}")
        print(f"URL: {r['source_url']}")
        print(r["description"] or "")
        print("-"*72)
        params = con.execute(
            "SELECT parameter,value,unit,notes FROM parameters WHERE nomenclature_id=? ORDER BY id",
            (r["id"],)
        ).fetchall()
        for p in params:
            suffix = f" {p['unit']}" if p["unit"] else ""
            note = f"  [{p['notes']}]" if p["notes"] else ""
            print(f"{p['parameter']}: {p['value']}{suffix}{note}")
    con.close()
    return len(rows)

def list_all():
    con = connect()
    for r in con.execute("SELECT name,category,source_type FROM nomenclature ORDER BY category,name"):
        print(f"{r['name']:35} | {r['source_type']:4} | {r['category']}")
    con.close()

def add_record(name, category, description, source_type, source_reference, source_url):
    con = connect()
    con.execute("""
        INSERT INTO nomenclature(name,category,description,source_type,source_reference,source_url)
        VALUES(?,?,?,?,?,?)
    """, (name,category,description,source_type,source_reference,source_url))
    con.commit()
    con.close()
    print("Added:", name)

if __name__ == "__main__":
    seed()
    args = sys.argv[1:]
    if not args:
        print("Enter a nomenclature/model/well/API name. Example: C-320D-246-86")
        sys.exit(0)
    if args[0] == "--list":
        list_all()
    elif args[0] == "--add":
        if len(args) < 7:
            print('Usage: --add "name" "category" "description" "source_type" "reference" "url"')
            sys.exit(1)
        add_record(*args[1:7])
    else:
        n = lookup(" ".join(args))
        if n == 0:
            print("No documented match found. Add it to the database rather than inventing a value.")
