#!/usr/bin/env python3
"""
Simple test runner for Property 7 to verify implementation
This runs outside of Odoo to check basic logic
"""
import sys

def test_selection_algorithm():
    """Test the selection algorithm logic"""
    print("Testing Property 7: Default Printer Selection")
    print("=" * 60)
    
    # Simulate printer data
    printers = [
        {'name': 'Printer A', 'is_default': True, 'priority': 10, 'active': True, 'printer_type': 'receipt'},
        {'name': 'Printer B', 'is_default': False, 'priority': 50, 'active': True, 'printer_type': 'receipt'},
        {'name': 'Printer C', 'is_default': False, 'priority': 30, 'active': True, 'printer_type': 'receipt'},
    ]
    
    def score_printer(printer, location_id=None, department=None):
        """Score a printer based on selection criteria"""
        score = 0
        
        # Default flag scoring
        if printer.get('is_default'):
            score += 10000
        
        # Priority scoring
        score += printer.get('priority', 0)
        
        return score
    
    def select_best_printer(printers, printer_type=None):
        """Select the best printer from a list"""
        # Filter by active status
        active_printers = [p for p in printers if p.get('active', True)]
        
        # Filter by type if specified
        if printer_type:
            active_printers = [p for p in active_printers if p.get('printer_type') == printer_type]
        
        if not active_printers:
            return None
        
        # Score each printer
        scored = [(score_printer(p), p) for p in active_printers]
        scored.sort(key=lambda x: x[0], reverse=True)
        
        return scored[0][1]
    
    # Test 1: Default printer should be selected
    print("\nTest 1: Default printer selection")
    selected = select_best_printer(printers, 'receipt')
    assert selected['name'] == 'Printer A', f"Expected Printer A, got {selected['name']}"
    print(f"✅ Selected: {selected['name']} (default flag overrides priority)")
    
    # Test 2: Without default, highest priority wins
    print("\nTest 2: Priority-based selection (no default)")
    printers_no_default = [
        {'name': 'Printer X', 'is_default': False, 'priority': 10, 'active': True, 'printer_type': 'receipt'},
        {'name': 'Printer Y', 'is_default': False, 'priority': 50, 'active': True, 'printer_type': 'receipt'},
    ]
    selected = select_best_printer(printers_no_default, 'receipt')
    assert selected['name'] == 'Printer Y', f"Expected Printer Y, got {selected['name']}"
    print(f"✅ Selected: {selected['name']} (highest priority)")
    
    # Test 3: Inactive printers excluded
    print("\nTest 3: Inactive printer exclusion")
    printers_with_inactive = [
        {'name': 'Printer M', 'is_default': True, 'priority': 50, 'active': False, 'printer_type': 'receipt'},
        {'name': 'Printer N', 'is_default': False, 'priority': 10, 'active': True, 'printer_type': 'receipt'},
    ]
    selected = select_best_printer(printers_with_inactive, 'receipt')
    assert selected['name'] == 'Printer N', f"Expected Printer N, got {selected['name']}"
    print(f"✅ Selected: {selected['name']} (inactive default excluded)")
    
    # Test 4: Type filtering
    print("\nTest 4: Type filtering")
    mixed_printers = [
        {'name': 'Receipt Printer', 'is_default': True, 'priority': 50, 'active': True, 'printer_type': 'receipt'},
        {'name': 'Label Printer', 'is_default': True, 'priority': 50, 'active': True, 'printer_type': 'label'},
    ]
    selected = select_best_printer(mixed_printers, 'receipt')
    assert selected['name'] == 'Receipt Printer', f"Expected Receipt Printer, got {selected['name']}"
    print(f"✅ Selected: {selected['name']} (type filter applied)")
    
    selected = select_best_printer(mixed_printers, 'label')
    assert selected['name'] == 'Label Printer', f"Expected Label Printer, got {selected['name']}"
    print(f"✅ Selected: {selected['name']} (type filter applied)")
    
    # Test 5: No printers available
    print("\nTest 5: No printers available")
    selected = select_best_printer([], 'receipt')
    assert selected is None, f"Expected None, got {selected}"
    print(f"✅ Selected: None (no printers available)")
    
    print("\n" + "=" * 60)
    print("✅ All basic logic tests PASSED!")
    print("=" * 60)
    return True

if __name__ == '__main__':
    try:
        success = test_selection_algorithm()
        sys.exit(0 if success else 1)
    except AssertionError as e:
        print(f"\n❌ Test FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
