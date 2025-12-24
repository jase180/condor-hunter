#!/usr/bin/env python3
"""Validate that all test files are properly structured and importable.

Run this script to verify test suite integrity without running the tests.
"""

import sys
from pathlib import Path
import importlib.util

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def validate_test_file(test_file: Path) -> bool:
    """Validate a single test file can be imported."""
    try:
        spec = importlib.util.spec_from_file_location("test_module", test_file)
        if spec and spec.loader:
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            print(f"✅ {test_file.name}: Valid")
            return True
        else:
            print(f"❌ {test_file.name}: Could not load spec")
            return False
    except Exception as e:
        print(f"❌ {test_file.name}: {e}")
        return False


def count_tests_in_file(test_file: Path) -> tuple[int, int]:
    """Count test classes and functions in a file."""
    content = test_file.read_text()

    # Count test classes (lines starting with "class Test")
    test_classes = sum(1 for line in content.split('\n') if line.strip().startswith('class Test'))

    # Count test functions (lines with "def test_")
    test_functions = sum(1 for line in content.split('\n') if 'def test_' in line)

    return test_classes, test_functions


def main():
    """Run validation on all test files."""
    print("Validating Test Suite")
    print("=" * 60)

    tests_dir = Path(__file__).parent.parent / "condor_screener" / "tests"

    if not tests_dir.exists():
        print(f"❌ Tests directory not found: {tests_dir}")
        sys.exit(1)

    # Get all test files
    test_files = sorted(tests_dir.glob("test_*.py"))

    if not test_files:
        print("❌ No test files found")
        sys.exit(1)

    print(f"\nFound {len(test_files)} test files:\n")

    # Validate each file
    results = {}
    for test_file in test_files:
        is_valid = validate_test_file(test_file)
        classes, functions = count_tests_in_file(test_file)
        results[test_file.name] = {
            'valid': is_valid,
            'classes': classes,
            'functions': functions,
            'lines': len(test_file.read_text().split('\n'))
        }

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    total_valid = sum(1 for r in results.values() if r['valid'])
    total_classes = sum(r['classes'] for r in results.values())
    total_functions = sum(r['functions'] for r in results.values())
    total_lines = sum(r['lines'] for r in results.values())

    print(f"\nTest Files:       {total_valid}/{len(test_files)} valid")
    print(f"Test Classes:     {total_classes}")
    print(f"Test Functions:   {total_functions}")
    print(f"Total Lines:      {total_lines:,}")

    print("\nBreakdown by file:")
    print(f"{'File':<25} {'Classes':<10} {'Functions':<12} {'Lines':<10}")
    print("-" * 60)

    for filename, stats in sorted(results.items()):
        status = "✅" if stats['valid'] else "❌"
        print(f"{status} {filename:<22} {stats['classes']:<10} {stats['functions']:<12} {stats['lines']:<10}")

    # Check for required files
    print("\n" + "=" * 60)
    print("REQUIRED FILES CHECK")
    print("=" * 60)

    required_files = [
        'test_models.py',
        'test_data.py',
        'test_builder.py',
        'test_analytics.py',
        'test_scoring.py',
        'test_integration.py',
        'test_e2e.py',
    ]

    all_present = True
    for required in required_files:
        if required in results:
            print(f"✅ {required}")
        else:
            print(f"❌ {required} - MISSING")
            all_present = False

    # Final verdict
    print("\n" + "=" * 60)
    if all_present and total_valid == len(test_files):
        print("✅ TEST SUITE VALIDATION PASSED")
        print("=" * 60)
        print("\nAll test files are valid and importable.")
        print("Ready to run: pytest")
        return 0
    else:
        print("❌ TEST SUITE VALIDATION FAILED")
        print("=" * 60)
        if not all_present:
            print("\n⚠️ Some required test files are missing")
        if total_valid < len(test_files):
            print(f"\n⚠️ {len(test_files) - total_valid} test file(s) failed validation")
        return 1


if __name__ == "__main__":
    sys.exit(main())
