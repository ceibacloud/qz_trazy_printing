# Running Property 7 Test: Default Printer Selection

## Overview

Property 7 tests that when a printer is marked as default for a print type, it gets selected when no specific printer is requested. The test also validates priority-based selection when no default is configured.

## Test File

`qz_tray_print/tests/test_qz_printer_properties.py`

## Test Method

`TestQZPrinterProperties.test_property_7_default_printer_selection`

## Prerequisites

1. Odoo 18 installed and configured
2. QZ Tray Print Integration module installed
3. Hypothesis library installed: `pip install hypothesis`
4. Test database configured

## Running the Test

### Option 1: Run All Property Tests

```bash
python odoo-bin -c odoo.conf --test-enable --stop-after-init -i qz_tray_print
```

### Option 2: Run Specific Test Module

```bash
python odoo-bin -c odoo.conf --test-enable --test-tags=qz_tray_print
```

### Option 3: Run Only Property 7 Test

```bash
python odoo-bin -c odoo.conf --test-enable --test-tags=qz_tray_print.test_property_7
```

### Option 4: Run with Verbose Output

```bash
python odoo-bin -c odoo.conf --test-enable --log-level=test -i qz_tray_print
```

## Expected Output

### Successful Test Run

```
Running test_property_7_default_printer_selection...
✓ Property 7: Default Printer Selection - 100 examples passed
✓ Edge case: No default printer
✓ Edge case: Multiple default printers
✓ Edge case: Default overrides priority
✓ Edge case: Inactive default printer
✓ Edge case: Type filtering
✓ Edge case: No printers available

All tests passed!
```

### Test Failure

If the test fails, Hypothesis will provide a counterexample:

```
Falsifying example: test_property_7_default_printer_selection(
    printer_type='receipt',
    is_default=True,
    priority=50
)
```

This counterexample can be used to debug the issue.

## What the Test Validates

1. **Default Selection**: Printers marked as default are selected when no specific printer is requested
2. **Priority Fallback**: When no default is set, the highest priority printer is selected
3. **Type Filtering**: Selection respects the printer type filter
4. **Default Override**: The default flag overrides priority values
5. **Active Status**: Inactive printers are excluded from selection

## Edge Cases Tested

1. **No Default Printer**: When no printer is marked as default, select by priority
2. **Multiple Default Printers**: When multiple printers are marked as default, select by priority
3. **Default Overrides Priority**: Default flag should override higher priority values
4. **Inactive Default Printer**: Inactive printers should not be selected even if marked as default
5. **Type Filtering**: Selection should respect printer type boundaries
6. **No Printers Available**: Return False when no printers exist

## Troubleshooting

### Test Fails to Import

**Error**: `ModuleNotFoundError: No module named 'hypothesis'`

**Solution**: Install Hypothesis
```bash
pip install hypothesis
```

### Database Connection Error

**Error**: `psycopg2.OperationalError: could not connect to server`

**Solution**: Ensure PostgreSQL is running and odoo.conf has correct database settings

### Test Timeout

**Error**: `hypothesis.errors.DeadlineExceeded`

**Solution**: The test has `deadline=None` set, but if you see this error, check database performance

### Selection Algorithm Error

**Error**: Test fails because wrong printer is selected

**Solution**: Check the `_select_best_printer()` method scoring logic. The scoring should be:
- Default flag: +10,000 points
- Location match: +1,000 points
- Department match: +500 points
- Priority: +priority points

## Validation Script

Before running the Odoo test, you can validate the test structure:

```bash
python qz_tray_print/tests/validate_property_7.py
```

This checks:
- Test class exists
- Property test method exists
- Decorators are correct
- Docstring is present
- Edge cases are implemented

## Test Configuration

- **Framework**: Hypothesis (property-based testing)
- **Iterations**: 100 examples per test run
- **Deadline**: None (no timeout)
- **Database**: Uses Odoo TransactionCase (automatic rollback)

## Selection Algorithm

The test validates the following selection algorithm:

1. Filter by active status (only active printers)
2. Filter by printer type (if specified)
3. Filter by location (if specified)
4. Filter by department (if specified)
5. Score each printer:
   - Default flag: +10,000
   - Location match: +1,000
   - Department match: +500
   - No location (fallback): +100
   - No department (fallback): +50
   - Priority value: +priority
6. Select printer with highest score

## Test Scenarios

### Scenario 1: Default Printer Exists

**Setup**:
- Printer A: type=receipt, is_default=True, priority=10
- Printer B: type=receipt, is_default=False, priority=50

**Expected**: Printer A is selected (default flag overrides priority)

### Scenario 2: No Default Printer

**Setup**:
- Printer A: type=receipt, is_default=False, priority=10
- Printer B: type=receipt, is_default=False, priority=50

**Expected**: Printer B is selected (highest priority)

### Scenario 3: Multiple Default Printers

**Setup**:
- Printer A: type=receipt, is_default=True, priority=10
- Printer B: type=receipt, is_default=True, priority=50

**Expected**: Printer B is selected (both default, highest priority wins)

### Scenario 4: Inactive Default Printer

**Setup**:
- Printer A: type=receipt, is_default=True, priority=50, active=False
- Printer B: type=receipt, is_default=False, priority=10, active=True

**Expected**: Printer B is selected (inactive printers excluded)

### Scenario 5: Type Filtering

**Setup**:
- Printer A: type=receipt, is_default=True
- Printer B: type=label, is_default=True

**Request**: type=receipt

**Expected**: Printer A is selected (type filter applied)

## Next Steps

After running the test:

1. If tests pass: Mark task 3.8 as complete and update PBT status to "passed"
2. If tests fail: Analyze the counterexample and fix the issue
3. Document any issues found in the test summary
4. Proceed to task 4.1 (Implement print job model)

## Related Documentation

- [Property 7 Test Summary](PROPERTY_7_TEST_SUMMARY.md)
- [Requirements Document](../.kiro/specs/qz-tray-print-integration/requirements.md)
- [Design Document](../.kiro/specs/qz-tray-print-integration/design.md)
- [Tasks Document](../.kiro/specs/qz-tray-print-integration/tasks.md)

## Quick Reference

**Property**: Default Printer Selection  
**Validates**: Requirements 2.5  
**Test Method**: `test_property_7_default_printer_selection`  
**Iterations**: 100  
**Edge Cases**: 6  
**Status**: ✅ Implemented
