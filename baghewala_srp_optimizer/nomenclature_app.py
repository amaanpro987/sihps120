
import streamlit as st
from nomenclature_lookup import init, seed, connect, lookup as cli_lookup

init(); seed()

st.set_page_config(page_title="Baghewala SRP Nomenclature", layout="wide")
st.title("Baghewala SRP — Nomenclature Lookup")
st.write("Type a model, well, API standard, or equipment nomenclature.")

query = st.text_input("Nomenclature", placeholder="e.g. C-320D-246-86, BGW#4, API 11L, 7/8 sucker rod")

if query:
    con = connect()
    q = query.lower()
    rows = con.execute("""
        SELECT DISTINCT n.* FROM nomenclature n
        LEFT JOIN aliases a ON a.nomenclature_id=n.id
        WHERE lower(n.name) LIKE ? OR lower(n.category) LIKE ?
           OR lower(n.description) LIKE ? OR lower(a.alias) LIKE ?
    """, (f"%{q}%",)*4).fetchall()
    con.close()

    if not rows:
        st.warning("No documented match. Add the parameter to the editable database instead of guessing.")
    for r in rows:
        st.subheader(f"{r['name']} — {r['category']}")
        st.caption(f"Source: {r['source_type']} | {r['source_reference']}")
        st.write(r["description"] or "")
        con = connect()
        ps = con.execute(
            "SELECT parameter,value,unit,notes FROM parameters WHERE nomenclature_id=?",
            (r["id"],)
        ).fetchall()
        con.close()
        for p in ps:
            st.write(f"**{p['parameter']}**: {p['value']} {p['unit'] or ''}")
            if p["notes"]:
                st.caption(p["notes"])
        st.divider()

st.markdown("""
### What can be typed
- `C-320D-246-86` → Baghewala SRP surface-unit specifications
- `BGW#4` → documented Baghewala Well 4 downhole configuration
- `Baghewala` → field SRP design envelope
- `API 11E` → surface pumping-unit standard
- `API 11L` → SRP design-calculation inputs/outputs
- `API 11AX` → subsurface pump specification scope
- `API 11B` → sucker-rod specification scope

**Important:** API nomenclature identifies the standard/specification. It does not mean
that API contains OIL's actual field measurements.
""")
