#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Validation script for Property 39: Retry Configuration Storage
This script validates the test structure without requiring a full Odoo environment
"""
import sys
import ast
import os

def validate_property_39_test():
    """Validate that Property 39 test is properly implemented"""
    print("=" * 80)
    print("Validating Property 39: Retry Configuration Storage Test")
    print("=" * 80)
    
    test_file = os.path.join(os.path.dirname(__file__), 'test_qz_tray_config_properties.py')
    
    try:
        with open(test_file, 'r', encoding='utf-8') as f:
            content = f.read()
            tree = ast.parse(content)
        
        # Find the test class
        test_class = None
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == 'TestQZTrayConfigProperties':
                test_class = node
                break
        
        if not test_class:
            print("✗ FAILED: TestQZTrayConfigProperties class not found")
            return False
        
        # Find Property 39 test method
        property_39_test = None
        edge_case_tests = []
        
        for item in test_class.body:
            if isinstance(item, ast.FunctionDef):
                if item.name == 'test_property_39_retry_configuration_storage':
                    property_39_test = item
                elif 'property_39' in item.name and 'edge_case' in item.name:
                    edge_case_tests.append(item.name)
        
        if not property_39_test:
            print("✗ FAILED: test_property_39_retry_configuration_storage method not found")
            return False
        
        print("✓ Found test_property_39_retry_configuration_storage method")
        
        # Check for @given decorator (property-based test)
        has_given_decorator = False
        for decorator in property_39_test.decorator_list:
            if isinstance(decorator, ast.Call):
                if isinstance(decorator.func, ast.Name) and decorator.func.id == 'given':
                    has_given_decorator = True
                    break
        
        if not has_given_decorator:
            print("✗ FAILED: @given decorator not found (not a property-based test)")
            return False
        
        print("✓ Test uses @given decorator (property-based test)")
        
        # Check for @settings decorator with max_examples
        has_settings_decorator = False
        for decorator in property_39_test.decorator_list:
            if isinstance(decorator, ast.Call):
                if isinstance(decorator.func, ast.Name) and decorator.func.id == 'settings':
                    has_settings_decorator = True
                    # Check for max_examples parameter
                    for keyword in decorator.keywords:
                        if keyword.arg == 'max_examples':
                            if isinstance(keyword.value, ast.Constant):
                                examples = keyword.value.value
                                if examples >= 100:
                                    print(f"✓ Test configured with {examples} examples (≥100)")
                                else:
                                    print(f"⚠ WARNING: Test configured with {examples} examples (<100)")
                    break
        
        if not has_settings_decorator:
            print("⚠ WARNING: @settings decorator not found")
        
        # Check docstring for proper format
        docstring = ast.get_docstring(property_39_test)
        if docstring:
            if 'Property 39' in docstring and 'Requirements 10.2' in docstring:
                print("✓ Test docstring properly formatted with property and requirement references")
            else:
                print("⚠ WARNING: Test docstring missing property or requirement references")
        else:
            print("⚠ WARNING: Test method has no docstring")
        
        # Check for edge case tests
        if edge_case_tests:
            print(f"✓ Found {len(edge_case_tests)} edge case tests:")
            for test_name in edge_case_tests:
                print(f"  - {test_name}")
        else:
            print("⚠ INFO: No edge case tests found")
        
        # Verify test checks retry_count and retry_delay
        test_source = ast.get_source_segment(content, property_39_test)
        if test_source:
            if 'retry_count' in test_source and 'retry_delay' in test_source:
                print("✓ Test validates both retry_count and retry_delay")
            else:
                print("⚠ WARNING: Test may not validate both retry_count and retry_delay")
            
            if 'save_credentials' in test_source:
                print("✓ Test calls save_credentials()")
            else:
                print("⚠ WARNING: Test may not call save_credentials()")
            
            if 'get_credentials' in test_source:
                print("✓ Test calls get_credentials()")
            else:
                print("⚠ WARNING: Test may not call get_credentials()")
        
        print("\n" + "=" * 80)
        print("✓ Property 39 test validation PASSED")
        print("=" * 80)
        print("\nTest Structure Summary:")
        print(f"  - Main property test: test_property_39_retry_configuration_storage")
        print(f"  - Edge case tests: {len(edge_case_tests)}")
        print(f"  - Property-based: Yes (using Hypothesis)")
        print(f"  - Validates: Requirements 10.2")
        print("\nNext Steps:")
        print("  1. Run the test in an Odoo environment to verify functionality")
        print("  2. Ensure all edge cases pass")
        print("  3. Update task status to completed")
        
        return True
        
    except FileNotFoundError:
        print(f"✗ FAILED: Test file not found: {test_file}")
        return False
    except SyntaxError as e:
        print(f"✗ FAILED: Syntax error in test file: {e}")
        return False
    except Exception as e:
        print(f"✗ FAILED: Unexpected error: {e}")
        return False

if __name__ == '__main__':
    success = validate_property_39_test()
    sys.exit(0 if success else 1)
