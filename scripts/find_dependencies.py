#!/usr/bin/env python3
# Created: 2026-07-05
# Path: scripts/find_dependencies.py
# Last Edited: 2026-07-24 13:36 CT (America/Chicago)
# Purpose: Function dependency analyzer using AST with file output

import json
import ast
from pathlib import Path
from collections import defaultdict
from datetime import datetime

def find_function_calls(file_path: str) -> dict:
    """Find all function calls in a Python file using AST."""
    calls = defaultdict(int)
    
    try:
        with open(file_path, 'r') as f:
            content = f.read()
        tree = ast.parse(content)
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    calls[node.func.id] += 1
                elif isinstance(node.func, ast.Attribute):
                    # Method calls like self.func() or obj.func()
                    calls[node.func.attr] += 1
    except Exception as e:
        pass  # Skip files with syntax errors
    
    return dict(calls)

def main():
    print("🔍 Analyzing function dependencies...")
    
    # Load inventory
    with open("function_inventory.json") as f:
        inventory = json.load(f)
    
    # Track calls
    all_calls = defaultdict(int)
    file_calls = {}
    
    # Analyze each file
    files_with_functions = set()
    for func_name, info in inventory["functions"].items():
        files_with_functions.add(Path(info["file"]))
    
    for file_path in files_with_functions:
        try:
            calls = find_function_calls(file_path)
            file_calls[str(file_path)] = calls
            for func_name, count in calls.items():
                all_calls[func_name] += count
        except Exception as e:
            print(f"⚠️ Could not parse {file_path}: {e}")
    
    # Find uncalled functions
    uncalled = []
    called = []
    for func_name, info in inventory["functions"].items():
        if func_name not in all_calls or all_calls[func_name] == 0:
            uncalled.append(func_name)
        else:
            called.append(func_name)
    
    # Sort by usage
    most_used = sorted(all_calls.items(), key=lambda x: x[1], reverse=True)
    
    # ===== Generate Report =====
    lines = []
    lines.append("=" * 70)
    lines.append("AetherLock Function Dependency Report")
    lines.append("=" * 70)
    lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"Total Functions: {len(inventory['functions'])}")
    lines.append(f"Functions with Calls: {len(called)}")
    lines.append(f"Uncalled Functions: {len(uncalled)}")
    lines.append("")
    
    # Most used functions
    lines.append("📊 TOP 25 MOST CALLED FUNCTIONS:")
    lines.append("-" * 50)
    for i, (func_name, count) in enumerate(most_used[:25], 1):
        info = inventory["functions"].get(func_name, {})
        file_name = Path(info.get("file", "")).name if info else "unknown"
        lines.append(f"  {i:2d}. {func_name}: {count} calls ({file_name})")
    
    # All functions with calls (for completeness)
    lines.append("")
    lines.append("📋 ALL FUNCTIONS WITH CALLS:")
    lines.append("-" * 50)
    for func_name, count in most_used:
        info = inventory["functions"].get(func_name, {})
        file_name = Path(info.get("file", "")).name if info else "unknown"
        lines.append(f"  • {func_name}: {count} calls ({file_name})")
    
    # Uncalled functions (potential dead code)
    lines.append("")
    lines.append("⚠️ UNUSED FUNCTIONS (Defined but never called):")
    lines.append("-" * 50)
    for func_name in sorted(uncalled):
        info = inventory["functions"].get(func_name, {})
        file_name = Path(info.get("file", "")).name if info else "unknown"
        line_num = info.get("line_start", 0) if info else 0
        lines.append(f"  • {func_name} ({file_name}:{line_num})")
    
    # Summary by module
    lines.append("")
    lines.append("📁 SUMMARY BY MODULE:")
    lines.append("-" * 50)
    module_stats = defaultdict(lambda: {"total": 0, "called": 0, "uncalled": 0})
    
    for func_name, info in inventory["functions"].items():
        file_path = info.get("file", "")
        # Extract module name (e.g., "database" from "src/shared/database.py")
        parts = Path(file_path).parts
        if len(parts) >= 3:
            module = parts[-3]  # src/modules/taskhelper -> taskhelper
            if module == "src":
                module = parts[-2] if len(parts) >= 2 else "root"
        else:
            module = "root"
        
        module_stats[module]["total"] += 1
        if func_name in called:
            module_stats[module]["called"] += 1
        else:
            module_stats[module]["uncalled"] += 1
    
    for module, stats in sorted(module_stats.items()):
        pct = (stats["called"] / stats["total"] * 100) if stats["total"] > 0 else 0
        lines.append(f"  📁 {module}: {stats['called']}/{stats['total']} called ({pct:.1f}%)")
    
    # ===== Save Reports =====
    report_text = '\n'.join(lines)
    
    # Print to console
    print(report_text)
    
    # Save to text file
    with open("docs/sys/dependency_report.txt", "w") as f:
        f.write(report_text)
    print("\n✅ Saved docs/sys/dependency_report.txt")
    
    # Save JSON for machine reading
    json_data = {
        "timestamp": datetime.now().isoformat(),
        "total_functions": len(inventory["functions"]),
        "called_count": len(called),
        "uncalled_count": len(uncalled),
        "most_used": most_used[:50],
        "uncalled_functions": sorted(uncalled),
        "called_functions": sorted(called),
        "all_usage": most_used
    }
    with open("docs/sys/dependency_report.json", "w") as f:
        json.dump(json_data, f, indent=2)
    print("✅ Saved docs/sys/dependency_report.json")

if __name__ == "__main__":
    main()
