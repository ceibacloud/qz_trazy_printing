#!/usr/bin/env python3
"""
Test runner for Property 36: Offline Printer Notification
Runs the property-based test for offline printer notification
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
from qz_tray_print.tests.test_notification_properties import TestNotificationProperties

def run_property_36_tests():
    """Run Property 36 tests"""
    print("="*70)
    print("Running Property 36: Offline Printer Notification Tests")
    print("="*70)
    
    # Create test suite
    import unittest
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add Property 36 test
    suite.addTest(TestNotificationProperties('test_property_36_offline_printer_notification'))
    
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
        print("\n✅ Property 36 test PASSED!")
        return 0
    else:
        print("\n❌ Property 36 test FAILED")
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
    sys.exit(run_property_36_tests())
