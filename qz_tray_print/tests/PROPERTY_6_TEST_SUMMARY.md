# Property 6 Test Implementation Summary

## Test: Location Assignment Storage

**Property Statement**: For any printer and location/department assignment, storing the association should result in the printer being associated with that location in the database and used in location-based selection.

**Validates**: Requirements 2.4

## Implementation Details

### Main Property Test
- **Method**: `test_property_6_location_assignment_storage`
- **Framework**: Hypothesis (property-based testing)
- **Iterations**: 100 examples
- **Strategy**: Uses `printer_name_strategy()`, `printer_type_strategy()`, and text generation for department names

### Test Logic
1. Generate random printer name, type, and optional department
2. Get or create a company for location assignment
3. Create a printer with location and department assignment
4. Invalidate the recordset to force a database refresh
5. Retrieve the printer and verify location/department persisted
6. Test location-based selection finds the printer correctly
7. Verify location filtering works (different location doesn't find the printer)

### Fields Tested
- `location_id`: Company/location assignment (Many2one to res.company)
- `department`: Department assignment (Char field)

### Location-Based Selection Algorithm Tested
The test verifies that the `get_default_printer()` method correctly:
1. Filters printers by location_id when specified
2. Filters printers by department when specified
3. Returns the correct printer for matching location/department
4. Does not return location-specific printers for different locations

### Edge Cases Covered

#### 1. No Location Assignment (Fallback Behavior)
- **Test**: `test_property_6_edge_case_no_location_assignment`
- **Purpose**: Verify that printers without location assignment act as fallbacks
- **Validates**: Unassigned printers can be selected for any location

#### 2. Location Priority
- **Test**: `test_property_6_edge_case_location_priority`
- **Purpose**: Verify that location-specific printers are prioritized over fallbacks
- **Validates**: Location match takes precedence over higher priority fallback printers

#### 3. Department Filtering
- **Test**: `test_property_6_edge_case_department_filtering`
- **Purpose**: Verify that department filtering works correctly
- **Validates**: Printers are correctly filtered by department assignment

#### 4. Update Location Assignment
- **Test**: `test_property_6_edge_case_update_location_assignment`
- **Purpose**: Verify that updating location/department assignments persists correctly
- **Validates**: The `write()` method correctly updates location assignments and selection uses new values

## Test Strategy

This is a **round-trip property test with selection validation**:
```
Assignment → Save → Retrieve → Verify Persistence → Verify Selection
```

The test ensures:
1. Location and department assignments are correctly stored in the database
2. Retrieved values exactly match the saved assignments
3. Location-based selection algorithm uses the assignments correctly
4. Location filtering prevents cross-location printer selection
5. Department filtering works as expected
6. Updates to assignments persist and affect selection

## Why This Test Matters

Location assignment is critical for the QZ Tray Print Integration because:
1. **Multi-Location Support**: Organizations with multiple locations need location-specific printers
2. **Department Isolation**: Different departments may need different printers
3. **Automatic Selection**: The system must automatically select the correct printer based on user location
4. **Data Integrity**: Incorrect location assignments could route print jobs to wrong printers
5. **User Experience**: Users expect prints to go to nearby printers, not remote locations

## Selection Algorithm Validation

The test validates the printer selection algorithm defined in `qz.printer.get_default_printer()`:

**Selection Priority (from highest to lowest):**
1. Exact location and department match with `is_default=True`
2. Exact location and department match with highest priority
3. Location match with `is_default=True`
4. Location match with highest priority
5. Department match with `is_default=True`
6. Department match with highest priority
7. Any printer with `is_default=True`
8. Any printer with highest priority

The test verifies that:
- Location-specific printers are prioritized over unassigned printers
- Department filtering correctly isolates printers by department
- Fallback printers (no location) are available when no specific match exists

## Running the Test

The test is part of the Odoo test suite and should be run using Odoo's test framework:

```bash
# Run all printer property tests
python odoo-bin -c odoo.conf --test-enable --stop-after-init -i qz_tray_print

# Run specific test module
python odoo-bin -c odoo.conf --test-enable --test-tags=qz_tray_print

# Run only Property 6 test
python odoo-bin -c odoo.conf --test-enable --test-tags=qz_tray_print.test_property_6
```

## Test Status

✅ **Implemented**: Property test and 4 edge cases are fully implemented
✅ **Validated**: Test structure validated using automated validation script
✅ **Structure**: Follows Hypothesis property-based testing best practices
⏳ **Pending**: Awaiting execution in Odoo test environment

## Related Tests

- Property 3: Printer Name Uniqueness
- Property 4: Printer List Retrieval
- Property 5: Printer Configuration Persistence
- Property 7: Default Printer Selection (depends on location assignment)

## Code Coverage

The test covers:
- `qz.printer.create()` - Printer creation with location assignment
- `qz.printer.write()` - Updating location assignments
- `qz.printer.get_default_printer()` - Location-based printer selection
- `qz.printer._select_best_printer()` - Selection algorithm with location scoring

## Property-Based Testing Benefits

Using Hypothesis for this test provides:
1. **Comprehensive Coverage**: Tests 100 random combinations of printer names, types, and departments
2. **Edge Case Discovery**: Automatically finds edge cases we might not think of
3. **Regression Prevention**: Ensures the property holds across all valid inputs
4. **Documentation**: The property statement serves as executable documentation
