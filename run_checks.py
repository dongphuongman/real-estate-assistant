#!/usr/bin/env python
"""
CLI Script to run Rule Engine checks on a file or directory.
"""
import argparse
import os
import sys

# Add project root to path
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from rules.engine import RuleEngine


def scan_file(file_path: str, engine: RuleEngine) -> int:
    """Returns number of violations."""
    try:
        violations = engine.validate_file(file_path)
        if violations:
            print(f"\n📄 {file_path}:")
            for v in violations:
                symbol = "❌" if v.severity == "error" else "⚠️"
                print(f"  {symbol} Line {v.line_number}: [{v.rule_id}] {v.message}")
            return len(violations)
        return 0
    except Exception as e:
        print(f"Error scanning {file_path}: {e}")
        return 0

def scan_directory(dir_path: str, engine: RuleEngine, recursive: bool = True) -> int:
    total_violations = 0
    for root, _, files in os.walk(dir_path):
        for file in files:
            if file.endswith(".py"):
                full_path = os.path.join(root, file)
                total_violations += scan_file(full_path, engine)
        if not recursive:
            break
    return total_violations

def main():
    parser = argparse.ArgumentParser(description="Run Trae Rule Engine checks.")
    parser.add_argument("path", help="File or directory to scan")
    parser.add_argument("--recursive", "-r", action="store_true", help="Scan directories recursively")
    
    args = parser.parse_args()
    
    engine = RuleEngine()
    
    print(f"🔍 Scanning {args.path}...")
    
    if os.path.isfile(args.path):
        count = scan_file(args.path, engine)
    elif os.path.isdir(args.path):
        count = scan_directory(args.path, engine, args.recursive)
    else:
        print(f"Error: {args.path} not found.")
        sys.exit(1)
        
    if count > 0:
        print(f"\nFound {count} violations.")
        sys.exit(1)
    else:
        print("\n✅ No violations found.")
        sys.exit(0)

if __name__ == "__main__":
    main()
