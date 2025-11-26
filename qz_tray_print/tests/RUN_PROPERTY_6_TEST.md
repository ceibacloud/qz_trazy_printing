# Running Property 6 Test: Location Assignment Storage

## Overview

Property 6 tests that location and department assignments for printers are correctly stored in the database and used in location-based printer selection.

## Test File

`qz_tray_print/tests/test_qz_printer_properties.py`

## Test Method

`TestQZPrinterProperties.test_property_6_location_assignment_storage`

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

### Option 3: Run Only Property 6 Test

```bash
python odoo-bin -c odoo.conf --test-enable --test-tags=qz_tray_print.test_property_6
```

### Option 4: Run with Verbose Output

```bash
python odoo-bin -c odoo.conf --test-enable --log-level=test -i qz_tray_print
```

## Expected Output

### Successful Test Run

```
Running test_property_6_location_assignment_storage...
✓ Property 6: Location Assignment Storage - 100 examples passed
✓ Edge case: No location assignment
✓ Edge case: Location priority
✓ Edge case: Department filtering
✓ Edge case: Update location assignment

All tests passed!
```

### Test Failure

If the test fails, Hypothesis will provide a counterexample:

```
Falsifying example: test_property_6_location_assignment_storage(
    printer_name='HP LaserJet 123',
    printer_type='receipt',
    department='Sales'
)
```

This counterexample can be used to debug the issue.

## What the Test Validates

1. **Persistence**: Location and department assignments are stored correctly
2. **Retrieval**: Assigned values can be retrieved from the database
3. **Selection**: Location-based selection uses the assignments
4. **Filtering**: Location filtering prevents cross-location selection
5. **Updates**: Changes to assignments persist correctly

## Edge Cases Tested

1. **No Location Assignment**: Printers without location act as fallbacks
2. **Location Priority**: Location-specific printers are prioritized
3. **Department Filtering**: Department assignments filter correctly
4. **Update Assignment**: Location updates persist and affect selection

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

### No Companies Found

**Error**: Test fails because no companies exist

**Solution**: The test creates companies automatically, but ensure the test database is properly initialized

## Validation Script

Before running the Odoo test, you can validate the test structure:

```bash
python qz_tray_print/tests/validate_property_6.py
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

## Next Steps

After running the test:

1. If tests pass: Mark task as complete and update PBT status to "passed"
2. If tests fail: Analyze the counterexample and fix the issue
3. Document any issues found in the test summary

## Related Documentation

- [Property 6 Test Summary](PROPERTY_6_TEST_SUMMARY.md)
- [Requirements Document](../.kiro/specs/qz-tray-print-integration/requirements.md)
- [Design Document](../.kiro/specs/qz-tray-print-integration/design.md)
