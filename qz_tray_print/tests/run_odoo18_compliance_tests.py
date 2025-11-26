#!/usr/bin/env python3
"""
Test runner for Odoo 18 Compliance Fix Property Tests
Runs property-based tests for name uniqueness and non-emptiness
"""
import sys
import os
import subprocess

# Run tests using Odoo's test framework

def run_compliance_tests():
    """Run Odoo 18 compliance property tests using Odoo test framework"""
    print("="*70)
    print("Running Odoo 18 Compliance Fix Property Tests")
    print("="*70)
    
    odoo_bin = r"C:\Program Files\Odoo 18.0.20250111\server\odoo-bin"
    config_file = r"C:\Program Files\Odoo 18.0.20250111\server\odoo.conf"
    
    # Run Odoo tests for the specific test class
    cmd = [
        "python",
        odoo_bin,
        "-c", config_file,
        "-d", "odoo18",
        "--test-enable",
        "--test-tags", "qz_tray_print",
        "--stop-after-init",
        "--log-level=test"
    ]
    
    print(f"Running command: {' '.join(cmd)}")
    print("="*70)
    
    result = subprocess.run(cmd, capture_output=False)
    
    return result.returncode

if __name__ == '__main__':
    sys.exit(run_compliance_tests())
