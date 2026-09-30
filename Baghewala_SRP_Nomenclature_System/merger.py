import os
import re

FILES_IN_ORDER = [
    "fluid_pvt.py",
    "srp_formulas.py",
    "ertmac_ui_components.py",
    "database.py",
    "reservoir_thermal_engine.py",
    "srp_wellbore_engine.py",
    "ai_engine.py",
    "css_optimizer.py",
    "digital_twin_orchestrator.py",
    "app.py"
]

local_modules = [f.replace('.py', '') for f in FILES_IN_ORDER]
all_imports = set()
merged_code = []

def is_local_import(line):
    for mod in local_modules:
        if re.match(rf"^\s*(from|import)\s+{mod}(\s|$|\.)", line):
            return True
    return False

# Regular expressions to catch multi-line imports
multi_import_start_re = re.compile(r"^\s*from\s+[\w\.]+\s+import\s*\(")

for filename in FILES_IN_ORDER:
    with open(filename, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    in_multiline_import = False
    is_local_multiline = False
    
    file_code = [f"\n# {'='*40}\n# Content from: {filename}\n# {'='*40}\n"]
    
    for line in lines:
        stripped = line.strip()
        
        # Handle multi-line imports
        if in_multiline_import:
            if not is_local_multiline:
                all_imports.add(line)
            if ")" in stripped:
                in_multiline_import = False
            continue
            
        if multi_import_start_re.match(line):
            in_multiline_import = True
            is_local_multiline = is_local_import(line)
            if not is_local_multiline:
                all_imports.add(line)
            continue

        # Handle single-line imports
        if stripped.startswith("import ") or stripped.startswith("from "):
            if not is_local_import(line):
                all_imports.add(line)
            continue
        
        # Avoid duplicate streamlit set_page_config if any? Only in app.py it exists.
        
        file_code.append(line)
        
    merged_code.append("".join(file_code))

with open("merged_app.py", "w", encoding='utf-8') as f:
    f.write("# --- IMPORT SECTION ---\n")
    # Sort imports so stdlib / third-party are organized
    for imp in sorted(list(all_imports)):
        f.write(imp if imp.endswith('\n') else imp + '\n')
    f.write("\n# --- CODE SECTION ---\n")
    f.write("".join(merged_code))

print("Successfully merged into merged_app.py")
