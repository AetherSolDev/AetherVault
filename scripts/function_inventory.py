#!/usr/bin/env python3
# Created: 2026-07-05
# Path: scripts/function_inventory.py
# Last Edited: 2026-07-24 13:36 CT (America/Chicago)
# Purpose: Generate a tree view of all functions in the kissPWM_v6 codebase

import os
import re
import json
import ast
from pathlib import Path
from typing import Dict, List, Set, Optional
from dataclasses import dataclass, field
from datetime import datetime

@dataclass
class FunctionInfo:
    """Information about a function."""
    name: str
    file_path: str
    line_start: int
    line_end: int
    docstring: Optional[str] = None
    parameters: List[str] = field(default_factory=list)
    return_type: Optional[str] = None
    decorators: List[str] = field(default_factory=list)
    is_method: bool = False
    class_name: Optional[str] = None
    is_public: bool = True

@dataclass
class ClassInfo:
    """Information about a class."""
    name: str
    file_path: str
    line_start: int
    line_end: int
    methods: List[FunctionInfo] = field(default_factory=list)
    docstring: Optional[str] = None

class FunctionInventory:
    """Builds an inventory of all functions in the codebase."""
    
    def __init__(self, root_dir: str = "."):
        self.root_dir = Path(root_dir)
        self.functions: Dict[str, FunctionInfo] = {}
        self.classes: Dict[str, ClassInfo] = {}
        self.by_file: Dict[str, List[FunctionInfo]] = {}
        self.by_module: Dict[str, List[FunctionInfo]] = {}
        
    def scan(self, exclude_patterns: List[str] = None):
        """Scan all Python files in the project."""
        exclude_patterns = exclude_patterns or [
            "__pycache__", "venv", "kiss", ".git", "tests", "scripts",
            "*.pyc", "*.pyo", "migrations"
        ]
        
        python_files = []
        for py_file in self.root_dir.rglob("*.py"):
            should_exclude = False
            for pattern in exclude_patterns:
                if pattern in str(py_file):
                    should_exclude = True
                    break
            if not should_exclude:
                python_files.append(py_file)
        
        print(f"📁 Found {len(python_files)} Python files to scan...")
        
        for py_file in python_files:
            self._scan_file(py_file)
            
        print(f"✅ Found {len(self.functions)} functions across {len(self.by_file)} files")
        
    def _scan_file(self, file_path: Path):
        """Scan a single Python file using AST."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            tree = ast.parse(content)
            module_name = str(file_path.relative_to(self.root_dir))
            self.by_file[module_name] = []
            
            # Find all classes and functions
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    func_info = self._parse_function(node, module_name, file_path)
                    if func_info:
                        self.functions[func_info.name] = func_info
                        self.by_file[module_name].append(func_info)
                        
                        # Track by module
                        module_parts = module_name.split('/')
                        for i in range(len(module_parts)):
                            module_key = '/'.join(module_parts[:i+1])
                            if module_key not in self.by_module:
                                self.by_module[module_key] = []
                            self.by_module[module_key].append(func_info)
                
                elif isinstance(node, ast.ClassDef):
                    class_info = self._parse_class(node, module_name, file_path)
                    if class_info:
                        self.classes[class_info.name] = class_info
                        
        except Exception as e:
            print(f"⚠️ Error scanning {file_path}: {e}")
    
    def _parse_function(self, node: ast.FunctionDef, module: str, file_path: Path) -> Optional[FunctionInfo]:
        """Parse a function definition from AST."""
        # Skip private methods if needed
        if node.name.startswith('_') and not node.name.startswith('__'):
            is_public = False
        else:
            is_public = True
        
        # Get parameters
        params = []
        for arg in node.args.args:
            if arg.arg != 'self' and arg.arg != 'cls':
                params.append(arg.arg)
        
        # Get decorators
        decorators = []
        for dec in node.decorator_list:
            if isinstance(dec, ast.Name):
                decorators.append(dec.id)
            elif isinstance(dec, ast.Call):
                if isinstance(dec.func, ast.Name):
                    decorators.append(dec.func.id)
        
        # Get docstring
        docstring = ast.get_docstring(node)
        
        return FunctionInfo(
            name=node.name,
            file_path=str(file_path),
            line_start=node.lineno,
            line_end=node.end_lineno or node.lineno,
            docstring=docstring,
            parameters=params,
            decorators=decorators,
            is_method=module.count('/') > 0 and 'gui' not in module,
            is_public=is_public
        )
    
    def _parse_class(self, node: ast.ClassDef, module: str, file_path: Path) -> Optional[ClassInfo]:
        """Parse a class definition from AST."""
        methods = []
        for child in node.body:
            if isinstance(child, ast.FunctionDef):
                func_info = self._parse_function(child, module, file_path)
                if func_info:
                    func_info.class_name = node.name
                    func_info.is_method = True
                    methods.append(func_info)
        
        docstring = ast.get_docstring(node)
        
        return ClassInfo(
            name=node.name,
            file_path=str(file_path),
            line_start=node.lineno,
            line_end=node.end_lineno or node.lineno,
            methods=methods,
            docstring=docstring
        )
    
    def to_tree(self) -> str:
        """Generate a tree view of all functions."""
        lines = []
        lines.append("📂 kissPWM_v6 Function Inventory")
        lines.append("=" * 50)
        lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"Total Functions: {len(self.functions)}")
        lines.append(f"Total Classes: {len(self.classes)}")
        lines.append("")
        
        # Sort by module
        for module in sorted(self.by_module.keys()):
            if not self.by_module[module]:
                continue
            depth = module.count('/')
            indent = "  " * depth
            lines.append(f"{indent}📁 {module}/")
            
            # Get unique functions in this module
            func_names = set()
            for func in self.by_module[module]:
                if func.file_path not in func_names:
                    func_names.add(func.file_path)
            
            # Show functions
            funcs = [f for f in self.by_module[module] if f.is_public]
            for func in sorted(funcs, key=lambda x: x.name):
                prefix = "  "
                if func.is_method:
                    prefix = "    "
                lines.append(f"{indent}{prefix}🔹 {func.name}({', '.join(func.parameters)})")
                if func.docstring:
                    doc_preview = func.docstring[:50] + "..." if len(func.docstring) > 50 else func.docstring
                    lines.append(f"{indent}{prefix}    📝 {doc_preview}")
        
        return '\n'.join(lines)
    
    def to_json(self) -> str:
        """Export inventory to JSON."""
        data = {
            "timestamp": datetime.now().isoformat(),
            "total_functions": len(self.functions),
            "total_classes": len(self.classes),
            "functions": {},
            "classes": {}
        }
        
        for name, info in self.functions.items():
            data["functions"][name] = {
                "file": info.file_path,
                "line_start": info.line_start,
                "line_end": info.line_end,
                "parameters": info.parameters,
                "is_method": info.is_method,
                "class_name": info.class_name,
                "is_public": info.is_public,
                "docstring": info.docstring
            }
        
        return json.dumps(data, indent=2)

    def _parse_class(self, node: ast.ClassDef, module: str, file_path: Path) -> Optional[ClassInfo]:
        """Parse a class definition from AST."""
        methods = []
        for child in node.body:
            if isinstance(child, ast.FunctionDef):
                func_info = self._parse_function(child, module, file_path)
                if func_info:
                    func_info.class_name = node.name  # <-- This should already work
                    func_info.is_method = True
                    methods.append(func_info)
        
        # Store the class info for later reference
        class_info = ClassInfo(
            name=node.name,
            file_path=str(file_path),
            line_start=node.lineno,
            line_end=node.end_lineno or node.lineno,
            methods=methods,
            docstring=ast.get_docstring(node)
        )
        # Store in classes dict
        self.classes[node.name] = class_info
        return class_info

def main():
    """Generate function inventory."""
    inventory = FunctionInventory(".")
    inventory.scan()
    
    # Save tree view
    with open("docs/sys/function_inventory.txt", "w") as f:
        f.write(inventory.to_tree())
    print("✅ Saved docs/sys/function_inventory.txt")
    
    # Save JSON
    with open("docs/sys/function_inventory.json", "w") as f:
        f.write(inventory.to_json())
    print("✅ Saved docs/sys/function_inventory.json")
    
    # Print summary
    print("\n📊 Summary:")
    print(f"  Functions: {len(inventory.functions)}")
    print(f"  Classes: {len(inventory.classes)}")
    print(f"  Files: {len(inventory.by_file)}")

if __name__ == "__main__":
    main()
