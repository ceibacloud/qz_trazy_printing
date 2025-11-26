# -*- coding: utf-8 -*-
"""
Property-Based Tests for QZ Printer Model
Using Hypothesis for property-based testing
"""
import logging
from hypothesis import given, strategies as st, settings, assume
from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError
from psycopg2 import IntegrityError

_logger = logging.getLogger(__name__)


# Custom strategies for generating test data
@st.composite
def printer_name_strategy(draw):
    """Generate valid printer names"""
    # Generate printer names that are realistic
    prefixes = ['HP', 'Epson', 'Canon', 'Brother', 'Zebra', 'Star', 'Printer']
    models = ['LaserJet', 'TM-T88', 'QL-820', 'ZD420', 'TSP143', 'MFC-L2750DW']
    
    prefix = draw(st.sampled_from(prefixes))
    model = draw(st.sampled_from(models))
    number = draw(st.integers(min_value=1, max_value=999))
    
    return f"{prefix} {model} {number}"


@st.composite
def printer_type_strategy(draw):
    """Generate valid printer types"""
    return draw(st.sampled_from(['receipt', 'label', 'document', 'other']))


@st.composite
def printer_config_strategy(draw):
    """Generate complete printer configuration"""
    return {
        'name': draw(printer_name_strategy()),
        'printer_type': draw(printer_type_strategy()),
        'system_name': draw(st.text(min_size=1, max_size=100)),
        'paper_size': draw(st.sampled_from(['a4', 'letter', '80mm', '58mm', '4x6', 'custom'])),
        'orientation': draw(st.sampled_from(['portrait', 'landscape'])),
        'print_quality': draw(st.sampled_from(['draft', 'normal', 'high'])),
        'priority': draw(st.integers(min_value=0, max_value=100)),
        'is_default': draw(st.booleans()),
        'active': draw(st.booleans()),
    }


class TestQZPrinterProperties(TransactionCase):
    """
    Property-based tests for QZ Printer model
    """

    def setUp(self):
        super(TestQZPrinterProperties, self).setUp()
        self.QZPrinter = self.env['qz.printer']
        
    def tearDown(self):
        """Clean up test data after each test"""
        # Delete all test printers
        self.QZPrinter.search([]).unlink()
        super(TestQZPrinterProperties, self).tearDown()

    @given(
        name1=printer_name_strategy(),
        name2=printer_name_strategy(),
        printer_type=printer_type_strategy()
    )
    @settings(max_examples=100, deadline=None)
    def test_property_3_printer_name_uniqueness(self, name1, name2, printer_type):
        """
        **Feature: qz-tray-print-integration, Property 3: Printer Name Uniqueness**
        **Validates: Requirements 2.1**
        
        Property: For any printer creation attempt, if a printer with the same name
        already exists, the Print Service should reject the creation and return a
        validation error.
        """
        # Create first printer
        printer1 = self.QZPrinter.create({
            'name': name1,
            'printer_type': printer_type,
        })
        
        self.assertTrue(printer1, "First printer should be created successfully")
        
        # If names are different, second printer should be created successfully
        if name1 != name2:
            printer2 = self.QZPrinter.create({
                'name': name2,
                'printer_type': printer_type,
            })
            self.assertTrue(printer2, "Second printer with different name should be created")
        else:
            # If names are the same, creation should fail with IntegrityError
            with self.assertRaises(IntegrityError, msg="Duplicate printer name should raise IntegrityError"):
                self.QZPrinter.create({
                    'name': name2,
                    'printer_type': printer_type,
                })

    @given(printer_list=st.lists(printer_name_strategy(), min_size=1, max_size=10))
    @settings(max_examples=100, deadline=None)
    def test_property_4_printer_list_retrieval(self, printer_list):
        """
        **Feature: qz-tray-print-integration, Property 4: Printer List Retrieval**
        **Validates: Requirements 2.2**
        
        Property: For any successful QZ Tray connection, calling the printer retrieval
        method should return a list of available printers from the local system.
        """
        # Simulate QZ Tray returning a list of printers
        # First, ensure QZ Tray is configured
        QZConfig = self.env['qz.tray.config']
        
        # Create a minimal configuration
        config = QZConfig.create({
            'certificate': 'LS0tLS1CRUdJTiBDRVJUSUZJQ0FURS0tLS0tCnRlc3QKLS0tLS1FTkQgQ0VSVElGSUNBVEUtLS0tLQ==',
            'private_key': 'LS0tLS1CRUdJTiBQUklWQVRFIEtFWS0tLS0tCnRlc3QKLS0tLS1FTkQgUFJJVkFURSBLRVktLS0tLQ==',
            'connection_timeout': 30,
        })
        config.save_credentials()
        
        # Process the discovered printers
        result = self.QZPrinter.process_discovered_printers(printer_list)
        
        # Verify the result
        self.assertTrue(result.get('success'), "Processing should succeed")
        
        # Verify that printers were created
        created_count = result.get('created_count', 0)
        updated_count = result.get('updated_count', 0)
        
        # The total should match the unique printer names in the list
        unique_printers = set(printer_list)
        total_processed = created_count + updated_count
        
        self.assertEqual(total_processed, len(unique_printers),
                        f"Should process {len(unique_printers)} unique printers")
        
        # Verify printers exist in database
        for printer_name in unique_printers:
            printer = self.QZPrinter.search([('system_name', '=', printer_name)])
            self.assertTrue(printer, f"Printer {printer_name} should exist in database")

    def test_property_3_edge_case_empty_name(self):
        """
        Edge case: Empty printer name should fail validation
        """
        with self.assertRaises(ValidationError):
            self.QZPrinter.create({
                'name': '',
                'printer_type': 'receipt',
            })

    def test_property_3_edge_case_whitespace_name(self):
        """
        Edge case: Whitespace-only printer name should fail validation
        """
        with self.assertRaises(ValidationError):
            self.QZPrinter.create({
                'name': '   ',
                'printer_type': 'receipt',
            })

    def test_property_4_edge_case_empty_printer_list(self):
        """
        Edge case: Empty printer list should return appropriate message
        """
        result = self.QZPrinter.process_discovered_printers([])
        
        self.assertFalse(result.get('success'), "Empty list should not succeed")
        self.assertTrue(result.get('message'), "Should return a message")

    def test_property_4_edge_case_duplicate_printers_in_list(self):
        """
        Edge case: Duplicate printers in discovery list should be handled correctly
        """
        # Create a list with duplicates
        printer_list = ['HP LaserJet 1', 'HP LaserJet 1', 'Epson TM-T88']
        
        result = self.QZPrinter.process_discovered_printers(printer_list)
        
        self.assertTrue(result.get('success'), "Processing should succeed")
        
        # Should only create 2 unique printers
        unique_count = len(set(printer_list))
        total_processed = result.get('created_count', 0) + result.get('updated_count', 0)
        
        self.assertEqual(total_processed, unique_count,
                        "Should only process unique printers")

    def test_constraint_negative_priority(self):
        """Test that negative priority values are rejected"""
        with self.assertRaises(ValidationError):
            self.QZPrinter.create({
                'name': 'Test Printer',
                'printer_type': 'receipt',
                'priority': -1,
            })

    def test_printer_type_detection_receipt(self):
        """Test automatic detection of receipt printers"""
        printer_names = [
            'Epson TM-T88V',
            'Star TSP143',
            'Thermal Receipt Printer',
            'POS Printer 1'
        ]
        
        for name in printer_names:
            detected_type = self.QZPrinter._detect_printer_type(name)
            self.assertEqual(detected_type, 'receipt',
                           f"Should detect {name} as receipt printer")

    def test_printer_type_detection_label(self):
        """Test automatic detection of label printers"""
        printer_names = [
            'Zebra ZD420',
            'Brother QL-820NWB',
            'Label Printer Pro',
            'Barcode Printer'
        ]
        
        for name in printer_names:
            detected_type = self.QZPrinter._detect_printer_type(name)
            self.assertEqual(detected_type, 'label',
                           f"Should detect {name} as label printer")

    def test_printer_type_detection_document(self):
        """Test automatic detection of document printers"""
        printer_names = [
            'HP LaserJet Pro',
            'Canon PIXMA',
            'Brother MFC-L2750DW',
            'Office Inkjet Printer'
        ]
        
        for name in printer_names:
            detected_type = self.QZPrinter._detect_printer_type(name)
            self.assertEqual(detected_type, 'document',
                           f"Should detect {name} as document printer")

    @given(config=printer_config_strategy())
    @settings(max_examples=100, deadline=None)
    def test_property_5_printer_configuration_persistence(self, config):
        """
        **Feature: qz-tray-print-integration, Property 5: Printer Configuration Persistence**
        **Validates: Requirements 2.3**
        
        Property: For any valid printer configuration (paper size, orientation, print quality),
        saving the configuration should result in those values being retrievable from the
        printer record.
        
        This is a round-trip property: save configuration -> retrieve configuration -> 
        values should match.
        """
        # Create printer with the generated configuration
        printer = self.QZPrinter.create(config)
        
        # Verify the printer was created
        self.assertTrue(printer, "Printer should be created successfully")
        
        # Retrieve the printer from database (force refresh)
        printer.invalidate_recordset()
        retrieved_printer = self.QZPrinter.browse(printer.id)
        
        # Verify all configuration values match what was saved
        self.assertEqual(retrieved_printer.name, config['name'],
                        "Printer name should persist")
        self.assertEqual(retrieved_printer.printer_type, config['printer_type'],
                        "Printer type should persist")
        self.assertEqual(retrieved_printer.system_name, config['system_name'],
                        "System name should persist")
        self.assertEqual(retrieved_printer.paper_size, config['paper_size'],
                        "Paper size should persist")
        self.assertEqual(retrieved_printer.orientation, config['orientation'],
                        "Orientation should persist")
        self.assertEqual(retrieved_printer.print_quality, config['print_quality'],
                        "Print quality should persist")
        self.assertEqual(retrieved_printer.priority, config['priority'],
                        "Priority should persist")
        self.assertEqual(retrieved_printer.is_default, config['is_default'],
                        "Default flag should persist")
        self.assertEqual(retrieved_printer.active, config['active'],
                        "Active flag should persist")

    def test_property_5_edge_case_minimal_config(self):
        """
        Edge case: Minimal configuration with only required fields should persist
        """
        minimal_config = {
            'name': 'Minimal Test Printer',
            'printer_type': 'receipt',
        }
        
        printer = self.QZPrinter.create(minimal_config)
        self.assertTrue(printer, "Printer should be created with minimal config")
        
        # Retrieve and verify
        printer.invalidate_recordset()
        retrieved = self.QZPrinter.browse(printer.id)
        
        self.assertEqual(retrieved.name, minimal_config['name'])
        self.assertEqual(retrieved.printer_type, minimal_config['printer_type'])
        # Verify defaults are applied
        self.assertEqual(retrieved.paper_size, 'a4', "Default paper size should be a4")
        self.assertEqual(retrieved.orientation, 'portrait', "Default orientation should be portrait")
        self.assertEqual(retrieved.print_quality, 'normal', "Default print quality should be normal")

    def test_property_5_edge_case_update_configuration(self):
        """
        Edge case: Updating configuration should persist new values
        """
        # Create printer with initial config
        printer = self.QZPrinter.create({
            'name': 'Update Test Printer',
            'printer_type': 'receipt',
            'paper_size': 'a4',
            'orientation': 'portrait',
            'print_quality': 'normal',
        })
        
        # Update configuration
        new_config = {
            'paper_size': '80mm',
            'orientation': 'landscape',
            'print_quality': 'high',
            'priority': 50,
        }
        printer.write(new_config)
        
        # Retrieve and verify updates persisted
        printer.invalidate_recordset()
        retrieved = self.QZPrinter.browse(printer.id)
        
        self.assertEqual(retrieved.paper_size, new_config['paper_size'],
                        "Updated paper size should persist")
        self.assertEqual(retrieved.orientation, new_config['orientation'],
                        "Updated orientation should persist")
        self.assertEqual(retrieved.print_quality, new_config['print_quality'],
                        "Updated print quality should persist")
        self.assertEqual(retrieved.priority, new_config['priority'],
                        "Updated priority should persist")

    @given(
        printer_name=printer_name_strategy(),
        printer_type=printer_type_strategy(),
        department=st.one_of(st.none(), st.text(min_size=1, max_size=50))
    )
    @settings(max_examples=100, deadline=None)
    def test_property_6_location_assignment_storage(self, printer_name, printer_type, department):
        """
        **Feature: qz-tray-print-integration, Property 6: Location Assignment Storage**
        **Validates: Requirements 2.4**
        
        Property: For any printer and location/department assignment, storing the association
        should result in the printer being associated with that location in the database and
        used in location-based selection.
        
        This is a round-trip property: assign location/department -> retrieve printer ->
        verify assignment -> verify location-based selection uses the assignment.
        """
        # Get or create a company for location assignment
        Company = self.env['res.company']
        company = Company.search([], limit=1)
        
        if not company:
            company = Company.create({
                'name': 'Test Company',
            })
        
        # Create printer with location and department assignment
        printer_data = {
            'name': printer_name,
            'printer_type': printer_type,
            'location_id': company.id,
        }
        
        if department:
            printer_data['department'] = department
        
        printer = self.QZPrinter.create(printer_data)
        
        # Verify the printer was created
        self.assertTrue(printer, "Printer should be created successfully")
        
        # Retrieve the printer from database (force refresh)
        printer.invalidate_recordset()
        retrieved_printer = self.QZPrinter.browse(printer.id)
        
        # Verify location assignment persisted
        self.assertEqual(retrieved_printer.location_id.id, company.id,
                        "Location assignment should persist in database")
        
        # Verify department assignment persisted
        if department:
            self.assertEqual(retrieved_printer.department, department,
                            "Department assignment should persist in database")
        else:
            self.assertFalse(retrieved_printer.department,
                           "Empty department should persist as False")
        
        # Test location-based selection uses the assignment
        # Search for printer by location
        selected_printer = self.QZPrinter.get_default_printer(
            printer_type=printer_type,
            location_id=company.id,
            department=department
        )
        
        # Verify the printer is found and matches our created printer
        self.assertTrue(selected_printer, 
                       "Location-based selection should find the printer")
        self.assertEqual(selected_printer.id, printer.id,
                        "Location-based selection should return the assigned printer")
        
        # Verify location filtering works - search with different location should not find it
        # unless printer has no location (which would make it a fallback)
        other_company = Company.create({
            'name': 'Other Test Company',
        })
        
        other_location_printer = self.QZPrinter.get_default_printer(
            printer_type=printer_type,
            location_id=other_company.id,
            department=department
        )
        
        # If a printer is found, it should either be our printer (if it's a fallback)
        # or a different printer. Our printer should only be selected if it matches location
        if other_location_printer:
            if other_location_printer.id == printer.id:
                # This should only happen if our printer is a fallback (no specific location)
                # But we assigned a location, so this shouldn't happen
                self.fail("Printer with specific location should not be selected for different location")

    def test_property_6_edge_case_no_location_assignment(self):
        """
        Edge case: Printer without location assignment should act as fallback
        """
        # Create printer without location assignment
        printer = self.QZPrinter.create({
            'name': 'Fallback Printer',
            'printer_type': 'receipt',
            'priority': 5,
        })
        
        # Create a company
        Company = self.env['res.company']
        company = Company.search([], limit=1)
        if not company:
            company = Company.create({'name': 'Test Company'})
        
        # Search for printer with location - should find the fallback printer
        selected = self.QZPrinter.get_default_printer(
            printer_type='receipt',
            location_id=company.id
        )
        
        self.assertTrue(selected, "Should find fallback printer")
        self.assertEqual(selected.id, printer.id, "Should select unassigned printer as fallback")

    def test_property_6_edge_case_location_priority(self):
        """
        Edge case: Printer with matching location should be prioritized over fallback
        """
        Company = self.env['res.company']
        company = Company.search([], limit=1)
        if not company:
            company = Company.create({'name': 'Test Company'})
        
        # Create fallback printer (no location)
        fallback_printer = self.QZPrinter.create({
            'name': 'Fallback Printer',
            'printer_type': 'receipt',
            'priority': 10,
        })
        
        # Create location-specific printer with lower priority
        location_printer = self.QZPrinter.create({
            'name': 'Location Printer',
            'printer_type': 'receipt',
            'location_id': company.id,
            'priority': 5,
        })
        
        # Search for printer with location
        selected = self.QZPrinter.get_default_printer(
            printer_type='receipt',
            location_id=company.id
        )
        
        self.assertTrue(selected, "Should find a printer")
        # Location match should be prioritized over higher priority fallback
        self.assertEqual(selected.id, location_printer.id,
                        "Should prioritize location-specific printer over fallback")

    def test_property_6_edge_case_department_filtering(self):
        """
        Edge case: Department filtering should work correctly
        """
        Company = self.env['res.company']
        company = Company.search([], limit=1)
        if not company:
            company = Company.create({'name': 'Test Company'})
        
        # Create printer for Sales department
        sales_printer = self.QZPrinter.create({
            'name': 'Sales Printer',
            'printer_type': 'receipt',
            'location_id': company.id,
            'department': 'Sales',
            'priority': 10,
        })
        
        # Create printer for Warehouse department
        warehouse_printer = self.QZPrinter.create({
            'name': 'Warehouse Printer',
            'printer_type': 'receipt',
            'location_id': company.id,
            'department': 'Warehouse',
            'priority': 10,
        })
        
        # Search for Sales department printer
        selected_sales = self.QZPrinter.get_default_printer(
            printer_type='receipt',
            location_id=company.id,
            department='Sales'
        )
        
        self.assertTrue(selected_sales, "Should find Sales printer")
        self.assertEqual(selected_sales.id, sales_printer.id,
                        "Should select Sales department printer")
        
        # Search for Warehouse department printer
        selected_warehouse = self.QZPrinter.get_default_printer(
            printer_type='receipt',
            location_id=company.id,
            department='Warehouse'
        )
        
        self.assertTrue(selected_warehouse, "Should find Warehouse printer")
        self.assertEqual(selected_warehouse.id, warehouse_printer.id,
                        "Should select Warehouse department printer")

    def test_property_6_edge_case_update_location_assignment(self):
        """
        Edge case: Updating location assignment should persist new values
        """
        Company = self.env['res.company']
        company1 = Company.search([], limit=1)
        if not company1:
            company1 = Company.create({'name': 'Company 1'})
        
        company2 = Company.create({'name': 'Company 2'})
        
        # Create printer with initial location
        printer = self.QZPrinter.create({
            'name': 'Test Printer',
            'printer_type': 'receipt',
            'location_id': company1.id,
            'department': 'Sales',
        })
        
        # Verify initial assignment
        self.assertEqual(printer.location_id.id, company1.id)
        self.assertEqual(printer.department, 'Sales')
        
        # Update location and department
        printer.write({
            'location_id': company2.id,
            'department': 'Warehouse',
        })
        
        # Retrieve and verify updates persisted
        printer.invalidate_recordset()
        retrieved = self.QZPrinter.browse(printer.id)
        
        self.assertEqual(retrieved.location_id.id, company2.id,
                        "Updated location should persist")
        self.assertEqual(retrieved.department, 'Warehouse',
                        "Updated department should persist")
        
        # Verify selection uses new location
        selected = self.QZPrinter.get_default_printer(
            printer_type='receipt',
            location_id=company2.id,
            department='Warehouse'
        )
        
        self.assertTrue(selected, "Should find printer with new location")
        self.assertEqual(selected.id, printer.id,
                        "Should select printer with updated location")

    @given(
        printer_type=printer_type_strategy(),
        is_default=st.booleans(),
        priority=st.integers(min_value=0, max_value=100)
    )
    @settings(max_examples=100, deadline=None)
    def test_property_7_default_printer_selection(self, printer_type, is_default, priority):
        """
        **Feature: qz-tray-print-integration, Property 7: Default Printer Selection**
        **Validates: Requirements 2.5**
        
        Property: For any print type with a configured default printer, when no specific
        printer is requested, the Print Service should select the default printer for that type.
        
        This tests that:
        1. When a printer is marked as default (is_default=True) for a type, it gets selected
        2. When no printer is marked as default, the highest priority printer is selected
        3. The selection respects the printer type filter
        """
        # Create a default printer for the given type
        default_printer = self.QZPrinter.create({
            'name': f'Default {printer_type} Printer',
            'printer_type': printer_type,
            'is_default': is_default,
            'priority': priority,
            'active': True,
        })
        
        # Create a non-default printer with different priority
        # Use a priority that's different from the default printer
        other_priority = priority + 10 if priority < 90 else priority - 10
        
        other_printer = self.QZPrinter.create({
            'name': f'Other {printer_type} Printer',
            'printer_type': printer_type,
            'is_default': False,
            'priority': other_priority,
            'active': True,
        })
        
        # Get the default printer for this type (no specific printer requested)
        selected_printer = self.QZPrinter.get_default_printer(printer_type=printer_type)
        
        # Verify a printer was selected
        self.assertTrue(selected_printer, 
                       f"Should select a printer for type {printer_type}")
        
        # Verify the selection logic:
        # If default_printer has is_default=True, it should be selected regardless of priority
        # Otherwise, the printer with higher priority should be selected
        if is_default:
            self.assertEqual(selected_printer.id, default_printer.id,
                           "Should select the printer marked as default")
        else:
            # When neither is marked as default, highest priority wins
            if priority > other_priority:
                self.assertEqual(selected_printer.id, default_printer.id,
                               "Should select printer with higher priority")
            else:
                self.assertEqual(selected_printer.id, other_printer.id,
                               "Should select printer with higher priority")
        
        # Verify the selected printer matches the requested type
        self.assertEqual(selected_printer.printer_type, printer_type,
                        "Selected printer should match the requested type")

    def test_property_7_edge_case_no_default_printer(self):
        """
        Edge case: When no printer is marked as default, select by priority
        """
        # Create multiple printers of the same type, none marked as default
        printer1 = self.QZPrinter.create({
            'name': 'Receipt Printer 1',
            'printer_type': 'receipt',
            'is_default': False,
            'priority': 5,
            'active': True,
        })
        
        printer2 = self.QZPrinter.create({
            'name': 'Receipt Printer 2',
            'printer_type': 'receipt',
            'is_default': False,
            'priority': 15,
            'active': True,
        })
        
        printer3 = self.QZPrinter.create({
            'name': 'Receipt Printer 3',
            'printer_type': 'receipt',
            'is_default': False,
            'priority': 10,
            'active': True,
        })
        
        # Get default printer
        selected = self.QZPrinter.get_default_printer(printer_type='receipt')
        
        self.assertTrue(selected, "Should select a printer")
        # Should select printer2 as it has the highest priority (15)
        self.assertEqual(selected.id, printer2.id,
                        "Should select printer with highest priority")

    def test_property_7_edge_case_multiple_default_printers(self):
        """
        Edge case: When multiple printers are marked as default, select by priority
        """
        # Create multiple printers marked as default
        printer1 = self.QZPrinter.create({
            'name': 'Default Receipt Printer 1',
            'printer_type': 'receipt',
            'is_default': True,
            'priority': 5,
            'active': True,
        })
        
        printer2 = self.QZPrinter.create({
            'name': 'Default Receipt Printer 2',
            'printer_type': 'receipt',
            'is_default': True,
            'priority': 15,
            'active': True,
        })
        
        # Get default printer
        selected = self.QZPrinter.get_default_printer(printer_type='receipt')
        
        self.assertTrue(selected, "Should select a printer")
        # Should select printer2 as it has higher priority
        self.assertEqual(selected.id, printer2.id,
                        "Should select default printer with highest priority")

    def test_property_7_edge_case_default_overrides_priority(self):
        """
        Edge case: Default flag should override priority
        """
        # Create a non-default printer with very high priority
        high_priority_printer = self.QZPrinter.create({
            'name': 'High Priority Printer',
            'printer_type': 'label',
            'is_default': False,
            'priority': 100,
            'active': True,
        })
        
        # Create a default printer with low priority
        default_printer = self.QZPrinter.create({
            'name': 'Default Label Printer',
            'printer_type': 'label',
            'is_default': True,
            'priority': 1,
            'active': True,
        })
        
        # Get default printer
        selected = self.QZPrinter.get_default_printer(printer_type='label')
        
        self.assertTrue(selected, "Should select a printer")
        # Default flag should override priority
        self.assertEqual(selected.id, default_printer.id,
                        "Default flag should override higher priority")

    def test_property_7_edge_case_inactive_default_printer(self):
        """
        Edge case: Inactive default printer should not be selected
        """
        # Create an inactive default printer
        inactive_default = self.QZPrinter.create({
            'name': 'Inactive Default Printer',
            'printer_type': 'document',
            'is_default': True,
            'priority': 50,
            'active': False,
        })
        
        # Create an active non-default printer
        active_printer = self.QZPrinter.create({
            'name': 'Active Document Printer',
            'printer_type': 'document',
            'is_default': False,
            'priority': 10,
            'active': True,
        })
        
        # Get default printer
        selected = self.QZPrinter.get_default_printer(printer_type='document')
        
        self.assertTrue(selected, "Should select a printer")
        # Should select the active printer, not the inactive default
        self.assertEqual(selected.id, active_printer.id,
                        "Should not select inactive default printer")

    def test_property_7_edge_case_type_filtering(self):
        """
        Edge case: Default printer selection should respect type filtering
        """
        # Create default printers for different types
        receipt_default = self.QZPrinter.create({
            'name': 'Default Receipt Printer',
            'printer_type': 'receipt',
            'is_default': True,
            'priority': 50,
            'active': True,
        })
        
        label_default = self.QZPrinter.create({
            'name': 'Default Label Printer',
            'printer_type': 'label',
            'is_default': True,
            'priority': 50,
            'active': True,
        })
        
        # Get default printer for receipt type
        selected_receipt = self.QZPrinter.get_default_printer(printer_type='receipt')
        self.assertTrue(selected_receipt, "Should select a receipt printer")
        self.assertEqual(selected_receipt.id, receipt_default.id,
                        "Should select receipt default printer")
        self.assertEqual(selected_receipt.printer_type, 'receipt',
                        "Selected printer should be receipt type")
        
        # Get default printer for label type
        selected_label = self.QZPrinter.get_default_printer(printer_type='label')
        self.assertTrue(selected_label, "Should select a label printer")
        self.assertEqual(selected_label.id, label_default.id,
                        "Should select label default printer")
        self.assertEqual(selected_label.printer_type, 'label',
                        "Selected printer should be label type")

    def test_property_7_edge_case_no_printers_available(self):
        """
        Edge case: When no printers are available, return False
        """
        # Ensure no printers exist
        self.QZPrinter.search([]).unlink()
        
        # Try to get default printer
        selected = self.QZPrinter.get_default_printer(printer_type='receipt')
        
        self.assertFalse(selected, "Should return False when no printers available")
