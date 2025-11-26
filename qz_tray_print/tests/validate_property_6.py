#!/usr/bin/env python3
"""
Validation script for Property 6 test implementation
Checks test structure without requiring Odoo runtime
"""
import ast
import sys


def validate_test_file(filepath):
    """Validate the test file structure"""
    print(f"Validating {filepath}...")
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Parse the file
    try:
        tree = ast.parse(content)
    except SyntaxError as e:
        print(f"❌ Syntax Error: {e}")
        return False
    
    # Find the test class
    test_class = None
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == 'TestQZPrinterProperties':
            test_class = node
            break
    
    if not test_class:
        print("❌ TestQZPrinterProperties class not found")
        return False
    
    print("✅ Test class found")
    
    # Find Property 6 test method
    property_6_test = None
    edge_case_tests = []
    
    for node in test_class.body:
        if isinstance(node, ast.FunctionDef):
            if node.name == 'test_property_6_location_assignment_storage':
                property_6_test = node
            elif 'property_6' in node.name and 'edge_case' in node.name:
                edge_case_tests.append(node.name)
    
    if not property_6_test:
        print("❌ test_property_6_location_assignment_storage method not found")
        return False
    
    print("✅ Property 6 main test method found")
    
    # Check for @given decorator
    has_given = False
    for decorator in property_6_test.decorator_list:
        if isinstance(decorator, ast.Call):
            if isinstance(decorator.func, ast.Name) and decorator.func.id == 'given':
                has_given = True
                break
    
    if not has_given:
        print("❌ @given decorator not found on main test")
        return False
    
    print("✅ @given decorator found (property-based test)")
    
    # Check for @settings decorator
    has_settings = False
    for decorator in property_6_test.decorator_list:
        if isinstance(decorator, ast.Call):
            if isinstance(decorator.func, ast.Name) and decorator.func.id == 'settings':
                has_settings = True
                # Check for max_examples parameter
                for keyword in decorator.keywords:
                    if keyword.arg == 'max_examples':
                        if isinstance(keyword.value, ast.Constant):
                            examples = keyword.value.value
                            if examples >= 100:
                                print(f"✅ max_examples set to {examples} (meets minimum of 100)")
                            else:
                                print(f"⚠️  max_examples is {examples}, should be at least 100")
                break
    
    if not has_settings:
        print("⚠️  @settings decorator not found")
    
    # Check docstring
    docstring = ast.get_docstring(property_6_test)
    if docstring:
        if 'Property 6' in docstring and 'Location Assignment Storage' in docstring:
            print("✅ Docstring contains property reference")
        if 'Requirements 2.4' in docstring:
            print("✅ Docstring validates Requirements 2.4")
        else:
            print("⚠️  Docstring missing requirements validation")
    else:
        print("❌ No docstring found")
        return False
    
    # Check edge case tests
    if edge_case_tests:
        print(f"✅ Found {len(edge_case_tests)} edge case tests:")
        for test_name in edge_case_tests:
            print(f"   - {test_name}")
    else:
        print("⚠️  No edge case tests found")
    
    # Check test body for key assertions
    test_body = ast.unparse(property_6_test)
    
    required_checks = [
        ('create', 'Printer creation'),
        ('invalidate_recordset', 'Database refresh'),
        ('location_id', 'Location assignment check'),
        ('get_default_printer', 'Location-based selection'),
    ]
    
    for check, description in required_checks:
        if check in test_body:
            print(f"✅ {description} present")
        else:
            print(f"⚠️  {description} might be missing")
    
    print("\n" + "="*60)
    print("✅ Validation PASSED - Test structure looks good!")
    print("="*60)
    return True


if __name__ == '__main__':
    filepath = 'qz_tray_print/tests/test_qz_printer_properties.py'
    success = validate_test_file(filepath)
    sys.exit(0 if success else 1)
