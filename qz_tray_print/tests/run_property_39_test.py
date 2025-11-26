#!/usr/bin/env python3
"""
Test runner for Property 39: Retry Configuration Storage
Runs the property-based test and edge cases
"""
import sys
import os

# Add Odoo to path
odoo_path = r"C:\Program Files\Odoo 18.0.20250111\server"
if odoo_path not in sys.path:
    sys.path.insert(0, odoo_path)

# Set up Odoo environment
os.environ['ODOO_RC'] = r"C:\Program Files\Odoo 18.0.20250111\server\odoo.conf"

import odoo
from odoo.tests.common import TransactionCase
from odoo.tests import tagged

# Initialize Odoo
odoo.tools.config.parse_config([
    '-c', r'C:\Program Files\Odoo 18.0.20250111\server\odoo.conf',
    '-d', 'odoo18',
    '--addons-path', r'C:\Program Files\Odoo 18.0.20250111\server\custom_addons',
])

# Import the test class
from qz_tray_print.tests.test_qz_tray_config_properties import TestQZTrayConfigProperties

def run_property_39_tests():
    """Run Property 39 tests"""
    print("="*70)
    print("Running Property 39: Retry Configuration Storage Tests")
    print("="*70)
    
    # Create test suite
    import unittest
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add Property 39 tests
    suite.addTest(TestQZTrayConfigProperties('test_property_39_retry_configuration_storage'))
    suite.addTest(TestQZTrayConfigProperties('test_property_39_edge_case_retry_disabled'))
    suite.addTest(TestQZTrayConfigProperties('test_property_39_edge_case_zero_retry'))
    suite.addTest(TestQZTrayConfigProperties('test_property_39_edge_case_default_values'))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "="*70)
    print("Test Summary")
    print("="*70)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Skipped: {len(result.skipped)}")
    
    if result.wasSuccessful():
        print("\n✅ All Property 39 tests PASSED!")
        return 0
    else:
        print("\n❌ Some tests FAILED")
        if result.failures:
            print("\nFailures:")
            for test, traceback in result.failures:
                print(f"\n{test}:")
                print(traceback)
        if result.errors:
            print("\nErrors:")
            for test, traceback in result.errors:
                print(f"\n{test}:")
                print(traceback)
        return 1

if __name__ == '__main__':
    sys.exit(run_property_39_tests())
