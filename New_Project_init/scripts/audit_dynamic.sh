#!/bin/bash
# audit_dynamic.sh: Find potential dynamic call patterns in src/

echo "--- Searching for dynamic call patterns ---"

# Search for getattr() usage
echo "[INFO] Searching for 'getattr' (Dynamic method access)..."
grep -rni "getattr" src/

# Search for signal connections (often involve dynamic method lookups)
echo "[INFO] Searching for '.connect(' (Signal/Slot connections)..."
grep -rni "\.connect(" src/

# Search for eval/exec (Dangerous/Dynamic)
echo "[INFO] Searching for 'eval(' or 'exec('..."
grep -rniE "(eval|exec)\(" src/

# Search for dynamic method naming patterns (e.g., self.handle_something)
# This finds where you might be building method names from strings
echo "[INFO] Searching for variable-based method calling patterns..."
grep -rniE "self\.[a-zA-Z0-9_]+\(" src/ | grep -v "def "
