import re
import os

# Configuration
INPUT_DIR = '/home/red-x/Documents/pythra-toolkit/src/pythra/pythra/project_template/render/loaders' # Put your original css files here
OUTPUT_DIR = '/home/red-x/Documents/pythra-toolkit/src/pythra/pythra/project_template/render/_loaders' # Where clean css goes

def normalize_css(content):
    # Split into blocks based on the class definition (e.g., .loader-bars-1 { ... })
    # This regex looks for the start of a loader block
    blocks = re.split(r'(?=\.loader-[a-z]+-[0-9]+)', content)
    
    normalized_content = ""
    
    for block in blocks:
        if not block.strip():
            continue
            
        # Find all unique variable names used in this block
        # Matches var(--loader-color-XX, ...) or var(--loader-color, ...)
        vars_found = []
        # Regex to find var calls
        var_matches = re.finditer(r'var\((--loader-color(?:-[0-9]+)?)(?:,\s*var\([^\)]+\))?(?:,\s*([^)]+))?\)', block)
        
        for match in var_matches:
            full_var = match.group(1) # e.g. --loader-color-34
            if full_var not in vars_found:
                vars_found.append(full_var)
        
        # Replace them with --c1, --c2, --c3 in order of appearance
        new_block = block
        for i, old_var in enumerate(vars_found):
            # We map to 1-based index: --c1, --c2
            new_var = f"--c{i+1}"
            # Replace variable usage, preserving fallback colors if you want, 
            # but usually we just want the variable: var(--c1, #originalColor)
            
            # Simple replacement of the variable name
            new_block = new_block.replace(old_var, new_var)
            
        normalized_content += new_block

    return normalized_content

# Ensure output directory exists
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Run for all CSS files
for filename in os.listdir(INPUT_DIR):
    if filename.endswith(".css"):
        with open(os.path.join(INPUT_DIR, filename), 'r') as f:
            raw = f.read()
        
        clean = normalize_css(raw)
        
        # Add a common header for defaults
        header = ":root { --c1: #000; --c2: #000; --c3: #000; }\n" 
        
        with open(os.path.join(OUTPUT_DIR, filename), 'w') as f:
            f.write(clean)
        print(f"Normalized {filename}")