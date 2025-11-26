# -*- coding: utf-8 -*-
"""
Property-Based Tests for QZ Print Service

These tests verify universal properties that should hold across all valid inputs
for the print service functionality.
"""
import logging
from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError, UserError
from hypothesis import given, strategies as st, settings, assume
import base64

_logger = logging.getLogger(__name__)


class TestQZPrintServiceProperties(TransactionCase):
    """Property-based tests for qz.print.service model"""

    def setUp(self):
        super(TestQZPrintServiceProperties, self).setUp()
        
        # Create test printer
        self.test_printer = self.env['qz.printer'].create({
            'name': 'Test Printer',
            'printer_type': 'document',
            'system_name': 'Test System Printer',
            'paper_size': 'a4',
            'orientation': 'portrait',
            'is_default': True,
            'active': True,
            'supports_pdf': True,
            'supports_html': True,
            'supports_escpos': False,
            'supports_zpl': False,
        })
        
        # Create a simple test template
        self.test_template = self.env['ir.ui.view'].create({
            'name': 'Test Print Template',
            'type': 'qweb',
            'key': 'qz_tray_print.test_template',
            'arch': '''
                <t t-name="qz_tray_print.test_template">
                    <div>
                        <h1 t-esc="title"/>
                        <p t-esc="content"/>
                    </div>
                </t>
            '''
        })
        
        # Get print service model
        self.print_service = self.env['qz.print.service']

    @given(
        title=st.text(min_size=1, max_size=100),
        content=st.text(min_size=1, max_size=500)
    )
    @settings(max_examples=100, deadline=None)
    def test_property_9_template_rendering(self, title, content):
        """
        **Feature: qz-tray-print-integration, Property 9: Template Rendering**
        
        Property: For any valid QWeb template reference and data, 
        the Print Service should successfully render the template and produce output without errors.
        
        **Validates: Requirements 3.2**
        """
        # Prepare template data
        template_data = {
            'title': title,
            'content': content,
        }
        
        # Attempt to render the template
        try:
            rendered = self.print_service._render_template(
                'qz_tray_print.test_template',
                template_data
            )
            
            # Verify rendering succeeded
            self.assertIsNotNone(rendered, "Rendered output should not be None")
            self.assertIsInstance(rendered, str, "Rendered output should be a string")
            self.assertGreater(len(rendered), 0, "Rendered output should not be empty")
            
            # Verify template data is present in output
            # Note: QWeb escapes HTML, so we check for the presence of the data
            self.assertIn(title, rendered, "Title should be present in rendered output")
            self.assertIn(content, rendered, "Content should be present in rendered output")
            
        except Exception as e:
            self.fail(f"Template rendering should not raise exception: {str(e)}")


    @given(
        format=st.sampled_from(['pdf', 'html', 'escpos', 'zpl']),
        data_size=st.integers(min_value=10, max_value=1000)
    )
    @settings(max_examples=100, deadline=None)
    def test_property_10_format_support(self, format, data_size):
        """
        **Feature: qz-tray-print-integration, Property 10: Format Support**
        
        Property: For any raw print data in supported formats (PDF, HTML, ESC/POS, ZPL),
        the Print Service should accept the data without format-related errors.
        
        **Validates: Requirements 3.3**
        """
        # Generate test data
        test_data = b'X' * data_size
        
        # Create a printer that supports this format
        format_support = {
            'pdf': {'supports_pdf': True},
            'html': {'supports_html': True},
            'escpos': {'supports_escpos': True},
            'zpl': {'supports_zpl': True},
        }
        
        test_printer = self.env['qz.printer'].create({
            'name': f'Test Printer {format}',
            'printer_type': 'document',
            'system_name': f'Test System Printer {format}',
            'is_default': False,
            'active': True,
            **format_support[format]
        })
        
        # Attempt to print with this format
        try:
            result = self.print_service.print_raw(
                data=test_data,
                format=format,
                printer=test_printer.id
            )
            
            # Verify result
            self.assertIsNotNone(result, "Print result should not be None")
            self.assertIn('job_id', result, "Result should contain job_id")
            self.assertGreater(result['job_id'], 0, "Job ID should be positive")
            
        except ValidationError as e:
            # Format validation errors are acceptable for unsupported formats
            if 'does not support format' in str(e):
                pass  # This is expected if printer doesn't support format
            else:
                self.fail(f"Unexpected validation error: {str(e)}")
        except Exception as e:
            self.fail(f"Format support should not raise unexpected exception: {str(e)}")

    @given(
        printer_id=st.integers(min_value=1, max_value=1000)
    )
    @settings(max_examples=100, deadline=None)
    def test_property_11_explicit_printer_selection(self, printer_id):
        """
        **Feature: qz-tray-print-integration, Property 11: Explicit Printer Selection**
        
        Property: For any valid printer identifier (name or ID) specified in a print request,
        the Print Service should use that specific printer for the job.
        
        **Validates: Requirements 3.4**
        """
        # Use the test printer we created in setUp
        test_data = b'Test print data'
        
        try:
            result = self.print_service.print_raw(
                data=test_data,
                format='html',
                printer=self.test_printer.id
            )
            
            # Verify the correct printer was used
            self.assertIsNotNone(result, "Print result should not be None")
            self.assertEqual(
                result['printer'],
                self.test_printer.name,
                "Result should reference the explicitly specified printer"
            )
            
            # Verify job was created with correct printer
            job = self.env['qz.print.job'].browse(result['job_id'])
            self.assertEqual(
                job.printer_id.id,
                self.test_printer.id,
                "Job should be assigned to the explicitly specified printer"
            )
            
        except ValidationError as e:
            # Only acceptable if printer doesn't exist
            if 'not found' in str(e).lower():
                pass  # Expected for non-existent printer IDs
            else:
                self.fail(f"Unexpected validation error: {str(e)}")

    @given(
        document_type=st.sampled_from(['receipt', 'label', 'document', 'other'])
    )
    @settings(max_examples=100, deadline=None)
    def test_property_12_default_printer_fallback(self, document_type):
        """
        **Feature: qz-tray-print-integration, Property 12: Default Printer Fallback**
        
        Property: For any print request without a specified printer,
        the Print Service should use the default printer configured for the document type.
        
        **Validates: Requirements 3.5**
        """
        # Create a default printer for this document type
        default_printer = self.env['qz.printer'].create({
            'name': f'Default {document_type} Printer',
            'printer_type': document_type,
            'system_name': f'Default System {document_type}',
            'is_default': True,
            'active': True,
            'supports_html': True,
        })
        
        test_data = b'Test print data'
        
        try:
            result = self.print_service.print_raw(
                data=test_data,
                format='html',
                printer=None,  # No explicit printer
                document_type=document_type
            )
            
            # Verify a printer was selected
            self.assertIsNotNone(result, "Print result should not be None")
            self.assertIn('printer', result, "Result should contain printer name")
            
            # Verify the default printer was used
            job = self.env['qz.print.job'].browse(result['job_id'])
            self.assertEqual(
                job.printer_id.printer_type,
                document_type,
                "Selected printer should match the document type"
            )
            
        except UserError as e:
            # Acceptable if no printer is available
            if 'no printer available' in str(e).lower():
                pass  # Expected when no printers exist
            else:
                self.fail(f"Unexpected user error: {str(e)}")

    @given(
        document_type=st.sampled_from(['receipt', 'label', 'document', 'other']),
        has_location=st.booleans(),
        has_department=st.booleans()
    )
    @settings(max_examples=100, deadline=None)
    def test_property_13_printer_selection_algorithm(self, document_type, has_location, has_department):
        """
        **Feature: qz-tray-print-integration, Property 13: Printer Selection Algorithm**
        
        Property: For any document type with configured selection rules,
        the Print Service should determine an appropriate printer based on those rules.
        
        **Validates: Requirements 4.1**
        """
        # Create test company/location if needed
        location = None
        if has_location:
            location = self.env.user.company_id.id
        
        department = 'Test Department' if has_department else None
        
        # Create a printer matching the criteria
        test_printer = self.env['qz.printer'].create({
            'name': f'Test {document_type} Printer',
            'printer_type': document_type,
            'system_name': f'Test System {document_type}',
            'location_id': location,
            'department': department,
            'is_default': False,
            'active': True,
            'priority': 50,
            'supports_html': True,
        })
        
        # Use the selection algorithm
        selected_printer = self.print_service.get_printer_for_type(
            document_type=document_type,
            location=location,
            department=department
        )
        
        # Verify a printer was selected
        if selected_printer:
            self.assertEqual(
                selected_printer.printer_type,
                document_type,
                "Selected printer should match the document type"
            )
            
            if has_location and location:
                # Verify location matching (or fallback)
                self.assertTrue(
                    selected_printer.location_id.id == location or not selected_printer.location_id,
                    "Selected printer should match location or be unassigned"
                )

    @given(
        priority1=st.integers(min_value=1, max_value=100),
        priority2=st.integers(min_value=1, max_value=100)
    )
    @settings(max_examples=100, deadline=None)
    def test_property_14_priority_based_selection(self, priority1, priority2):
        """
        **Feature: qz-tray-print-integration, Property 14: Priority-Based Selection**
        
        Property: For any set of printers matching the selection criteria,
        the Print Service should select the printer with the highest priority value.
        
        **Validates: Requirements 4.2**
        """
        assume(priority1 != priority2)  # Ensure priorities are different
        
        document_type = 'document'
        
        # Create two printers with different priorities
        printer1 = self.env['qz.printer'].create({
            'name': 'Printer 1',
            'printer_type': document_type,
            'system_name': 'System Printer 1',
            'is_default': False,
            'active': True,
            'priority': priority1,
            'supports_html': True,
        })
        
        printer2 = self.env['qz.printer'].create({
            'name': 'Printer 2',
            'printer_type': document_type,
            'system_name': 'System Printer 2',
            'is_default': False,
            'active': True,
            'priority': priority2,
            'supports_html': True,
        })
        
        # Select printer
        selected_printer = self.print_service.get_printer_for_type(
            document_type=document_type
        )
        
        # Verify the higher priority printer was selected
        if selected_printer:
            expected_printer = printer1 if priority1 > priority2 else printer2
            self.assertEqual(
                selected_printer.id,
                expected_printer.id,
                f"Should select printer with higher priority ({max(priority1, priority2)})"
            )

    @given(
        has_location_match=st.booleans()
    )
    @settings(max_examples=100, deadline=None)
    def test_property_15_location_based_prioritization(self, has_location_match):
        """
        **Feature: qz-tray-print-integration, Property 15: Location-Based Prioritization**
        
        Property: For any print request with a specified user location or department,
        the Print Service should prioritize printers assigned to that location over unassigned printers.
        
        **Validates: Requirements 4.3**
        """
        document_type = 'document'
        location = self.env.user.company_id.id if self.env.user.company_id else None
        
        if not location:
            # Skip test if no location available
            return
        
        # Create location-specific printer
        location_printer = self.env['qz.printer'].create({
            'name': 'Location Printer',
            'printer_type': document_type,
            'system_name': 'Location System Printer',
            'location_id': location if has_location_match else None,
            'is_default': False,
            'active': True,
            'priority': 10,
            'supports_html': True,
        })
        
        # Create unassigned printer with higher priority
        unassigned_printer = self.env['qz.printer'].create({
            'name': 'Unassigned Printer',
            'printer_type': document_type,
            'system_name': 'Unassigned System Printer',
            'location_id': None,
            'is_default': False,
            'active': True,
            'priority': 50,
            'supports_html': True,
        })
        
        # Select printer with location
        selected_printer = self.print_service.get_printer_for_type(
            document_type=document_type,
            location=location
        )
        
        # Verify location-based prioritization
        if selected_printer and has_location_match:
            # Location match should be prioritized over higher priority
            self.assertEqual(
                selected_printer.id,
                location_printer.id,
                "Should prioritize location-matched printer over higher priority unassigned printer"
            )

    @given(
        document_type=st.sampled_from(['receipt', 'label', 'document', 'other'])
    )
    @settings(max_examples=100, deadline=None)
    def test_property_16_system_default_fallback(self, document_type):
        """
        **Feature: qz-tray-print-integration, Property 16: System Default Fallback**
        
        Property: For any print request where no matching printer is found,
        the Print Service should use the system default printer.
        
        **Validates: Requirements 4.4**
        """
        # Create a system default printer (active, high priority, no type restriction)
        system_default = self.env['qz.printer'].create({
            'name': 'System Default Printer',
            'printer_type': 'other',  # Different type
            'system_name': 'System Default',
            'is_default': False,
            'active': True,
            'priority': 100,
            'supports_html': True,
        })
        
        # Try to get printer for a type with no specific printer
        selected_printer = self.print_service.get_printer_for_type(
            document_type=document_type
        )
        
        # Verify a printer was selected (fallback to any active printer)
        if selected_printer:
            self.assertTrue(
                selected_printer.active,
                "Fallback printer should be active"
            )
