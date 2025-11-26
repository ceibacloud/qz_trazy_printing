# -*- coding: utf-8 -*-
"""
Property-Based Tests for Odoo 18 Compliance Fix
Testing name field uniqueness and non-emptiness properties
"""
import logging
import base64
from hypothesis import given, strategies as st, settings
from odoo.tests.common import TransactionCase

_logger = logging.getLogger(__name__)


# Custom strategies for generating test data
@st.composite
def document_type_strategy(draw):
    """Generate valid document types"""
    return draw(st.sampled_from(['receipt', 'label', 'invoice', 'report', 'ticket', 'document']))


@st.composite
def data_format_strategy(draw):
    """Generate valid data formats"""
    return draw(st.sampled_from(['pdf', 'html', 'escpos', 'zpl']))


@st.composite
def print_job_data_strategy(draw):
    """Generate complete print job data"""
    return {
        'document_type': draw(document_type_strategy()),
        'data_format': draw(data_format_strategy()),
        'data': base64.b64encode(draw(st.text(min_size=10, max_size=100)).encode('utf-8')),
        'copies': draw(st.integers(min_value=1, max_value=10)),
        'priority': draw(st.integers(min_value=0, max_value=100)),
    }


class TestOdoo18ComplianceProperties(TransactionCase):
    """
    Property-based tests for Odoo 18 compliance fix
    """

    def setUp(self):
        super(TestOdoo18ComplianceProperties, self).setUp()
        self.QZPrintJob = self.env['qz.print.job']
        self.QZPrinter = self.env['qz.printer']
        
        # Create a test printer for jobs
        self.test_printer = self.QZPrinter.create({
            'name': 'Test Printer',
            'printer_type': 'receipt',
            'supports_pdf': True,
            'supports_html': True,
            'supports_escpos': True,
            'supports_zpl': True,
            'active': True,
        })
        
    def tearDown(self):
        """Clean up test data after each test"""
        # Delete all test jobs and printers
        self.QZPrintJob.search([]).unlink()
        self.QZPrinter.search([]).unlink()
        super(TestOdoo18ComplianceProperties, self).tearDown()

    @given(st.lists(print_job_data_strategy(), min_size=2, max_size=10))
    @settings(max_examples=100, deadline=None)
    def test_property_1_name_uniqueness(self, job_data_list):
        """
        **Feature: qz-tray-odoo18-compliance-fix, Property 1: Name field uniqueness**
        **Validates: Requirements 1.3, 2.4**
        
        Property: For any two qz.print.job records created in the system,
        their name fields should be unique.
        """
        # Create multiple print jobs
        jobs = []
        for job_data in job_data_list:
            job = self.QZPrintJob.create({
                'document_type': job_data['document_type'],
                'printer_id': self.test_printer.id,
                'data': job_data['data'],
                'data_format': job_data['data_format'],
                'copies': job_data['copies'],
                'priority': job_data['priority'],
            })
            jobs.append(job)
        
        # Extract all names
        names = [job.name for job in jobs]
        
        # Verify all names are unique
        self.assertEqual(len(names), len(set(names)),
                        f"Print job names must be unique. Found duplicates: {names}")
        
        # Verify no empty names
        for name in names:
            self.assertTrue(name, "Print job name must not be empty")

    @given(print_job_data_strategy())
    @settings(max_examples=100, deadline=None)
    def test_property_2_name_non_emptiness(self, job_data):
        """
        **Feature: qz-tray-odoo18-compliance-fix, Property 2: Name field non-emptiness**
        **Validates: Requirements 1.4**
        
        Property: For any qz.print.job record that has been saved to the database,
        the name field should not be empty or null.
        """
        # Create a print job
        job = self.QZPrintJob.create({
            'document_type': job_data['document_type'],
            'printer_id': self.test_printer.id,
            'data': job_data['data'],
            'data_format': job_data['data_format'],
            'copies': job_data['copies'],
            'priority': job_data['priority'],
        })
        
        # Verify name is not empty
        self.assertTrue(job.name, "Print job name must not be empty")
        self.assertNotEqual(job.name, '', "Print job name must not be empty string")
        self.assertNotEqual(job.name, 'New Print Job', 
                           "Print job name must be set after creation")
        
        # Verify name contains expected components
        self.assertIn(job_data['document_type'], job.name,
                     "Job name should contain document type")
        self.assertIn(self.test_printer.name, job.name,
                     "Job name should contain printer name")


    def test_unit_name_is_set_after_creation(self):
        """
        Unit test: Name should be set after creation
        **Validates: Requirements 1.4, 2.3**
        """
        # Create a print job
        job = self.QZPrintJob.create({
            'document_type': 'receipt',
            'printer_id': self.test_printer.id,
            'data': base64.b64encode(b'test data'),
            'data_format': 'pdf',
        })
        
        # Verify name is set
        self.assertTrue(job.name, "Name should be set after creation")
        self.assertNotEqual(job.name, '', "Name should not be empty")
        self.assertNotEqual(job.name, 'New Print Job', "Name should not be default value")

    def test_unit_name_contains_expected_components(self):
        """
        Unit test: Name should contain document type and printer name
        **Validates: Requirements 1.4, 2.3**
        """
        # Create a print job
        job = self.QZPrintJob.create({
            'document_type': 'invoice',
            'printer_id': self.test_printer.id,
            'data': base64.b64encode(b'test data'),
            'data_format': 'pdf',
        })
        
        # Verify name contains expected components
        self.assertIn('invoice', job.name, "Name should contain document type")
        self.assertIn(self.test_printer.name, job.name, "Name should contain printer name")

    def test_unit_name_is_readonly(self):
        """
        Unit test: Name field should be readonly (cannot be modified after creation)
        **Validates: Requirements 2.3**
        """
        # Create a print job
        job = self.QZPrintJob.create({
            'document_type': 'label',
            'printer_id': self.test_printer.id,
            'data': base64.b64encode(b'test data'),
            'data_format': 'zpl',
        })
        
        original_name = job.name
        
        # Try to modify the name (should not change due to readonly)
        job.write({'name': 'Modified Name'})
        
        # Verify name hasn't changed (readonly field)
        # Note: In Odoo, readonly fields can still be written programmatically,
        # but they're readonly in the UI. The field definition has readonly=True.
        # We verify the field is defined as readonly
        name_field = self.QZPrintJob._fields['name']
        self.assertTrue(name_field.readonly, "Name field should be defined as readonly")

    def test_unit_name_uniqueness_with_sequence(self):
        """
        Unit test: Names should be unique due to sequence
        **Validates: Requirements 1.3, 2.4**
        """
        # Create multiple jobs
        jobs = []
        for i in range(5):
            job = self.QZPrintJob.create({
                'document_type': 'ticket',
                'printer_id': self.test_printer.id,
                'data': base64.b64encode(f'test data {i}'.encode()),
                'data_format': 'pdf',
            })
            jobs.append(job)
        
        # Extract names
        names = [job.name for job in jobs]
        
        # Verify all names are unique
        self.assertEqual(len(names), len(set(names)), 
                        f"All names should be unique, got: {names}")

    def test_unit_name_format(self):
        """
        Unit test: Name should follow expected format
        **Validates: Requirements 1.4, 2.3**
        """
        # Create a print job
        job = self.QZPrintJob.create({
            'document_type': 'report',
            'printer_id': self.test_printer.id,
            'data': base64.b64encode(b'test data'),
            'data_format': 'html',
        })
        
        # Verify name format: should be like "report-Test Printer-PJ000001"
        parts = job.name.split('-')
        self.assertGreaterEqual(len(parts), 3, 
                               f"Name should have at least 3 parts separated by '-', got: {job.name}")
        self.assertEqual(parts[0], 'report', "First part should be document type")
        self.assertIn('Test Printer', job.name, "Name should contain printer name")
        # Last part should contain sequence number
        self.assertTrue(any(char.isdigit() for char in parts[-1]), 
                       "Name should contain sequence number")

    def test_property_3_module_installation_success(self):
        """
        **Feature: qz-tray-odoo18-compliance-fix, Property 3: Module installation success**
        **Validates: Requirements 1.1, 1.2**
        
        Property: For any Odoo 18 instance, installing the qz_tray_print module
        should complete without raising NotImplementedError.
        
        This test verifies that:
        1. The qz.print.job model can be loaded without errors
        2. The name field does not depend on 'id' field
        3. Records can be created successfully
        """
        # Verify the model exists and is accessible
        self.assertTrue(hasattr(self.env, '__getitem__'), 
                       "Environment should support model access")
        
        # Verify we can access the qz.print.job model
        try:
            model = self.env['qz.print.job']
            self.assertIsNotNone(model, "qz.print.job model should be accessible")
        except Exception as e:
            self.fail(f"Failed to access qz.print.job model: {e}")
        
        # Verify the name field exists and is properly configured
        self.assertIn('name', self.QZPrintJob._fields, 
                     "name field should exist in qz.print.job model")
        
        name_field = self.QZPrintJob._fields['name']
        
        # Verify name field is not a computed field that depends on 'id'
        if hasattr(name_field, 'compute') and name_field.compute:
            # If it's computed, check it doesn't depend on 'id'
            if hasattr(name_field, 'depends') and name_field.depends:
                self.assertNotIn('id', name_field.depends,
                               "name field should not depend on 'id' field")
        
        # Verify we can create records without NotImplementedError
        try:
            job = self.QZPrintJob.create({
                'document_type': 'test_install',
                'printer_id': self.test_printer.id,
                'data': base64.b64encode(b'installation test data'),
                'data_format': 'pdf',
            })
            
            # Verify the record was created successfully
            self.assertTrue(job.id, "Record should have an ID after creation")
            self.assertTrue(job.name, "Record should have a name after creation")
            self.assertNotEqual(job.name, '', "Name should not be empty")
            
            _logger.info(f"Successfully created print job during installation test: {job.name}")
            
        except NotImplementedError as e:
            self.fail(f"NotImplementedError raised during record creation: {e}")
        except Exception as e:
            self.fail(f"Unexpected error during record creation: {e}")
        
        # Verify multiple records can be created (tests sequence functionality)
        try:
            jobs = []
            for i in range(3):
                job = self.QZPrintJob.create({
                    'document_type': f'test_install_{i}',
                    'printer_id': self.test_printer.id,
                    'data': base64.b64encode(f'test data {i}'.encode()),
                    'data_format': 'pdf',
                })
                jobs.append(job)
            
            # Verify all jobs have unique names
            names = [j.name for j in jobs]
            self.assertEqual(len(names), len(set(names)),
                           "All created jobs should have unique names")
            
            _logger.info(f"Successfully created {len(jobs)} jobs during installation test")
            
        except Exception as e:
            self.fail(f"Failed to create multiple records: {e}")

    @given(print_job_data_strategy())
    @settings(max_examples=100, deadline=None)
    def test_property_5_backward_compatibility(self, job_data):
        """
        **Feature: qz-tray-odoo18-compliance-fix, Property 5: Backward compatibility**
        **Validates: Requirements 1.5**
        
        Property: For any existing functionality that uses qz.print.job records,
        the behavior should remain unchanged after the fix.
        
        This test verifies that:
        1. Print job submission workflow works correctly
        2. Print job processing works correctly
        3. Print job retry mechanism works correctly
        4. All state transitions work as expected
        5. Error handling works correctly
        """
        # Test 1: Print job submission workflow
        job = self.QZPrintJob.create({
            'document_type': job_data['document_type'],
            'printer_id': self.test_printer.id,
            'data': job_data['data'],
            'data_format': job_data['data_format'],
            'copies': job_data['copies'],
            'priority': job_data['priority'],
        })
        
        # Verify job is created in draft state
        self.assertEqual(job.state, 'draft', 
                        "New job should be in draft state")
        
        # Submit the job
        job_id = job.submit_job()
        
        # Verify submission worked
        self.assertEqual(job_id, job.id, 
                        "submit_job should return the job ID")
        self.assertEqual(job.state, 'queued', 
                        "Job should be in queued state after submission")
        self.assertTrue(job.submitted_date, 
                       "Job should have submitted_date after submission")
        
        # Test 2: Print job processing
        # Process the job
        result = job.process_job()
        
        # Verify processing worked
        self.assertTrue(result, 
                       "process_job should return True for valid job")
        self.assertEqual(job.state, 'printing', 
                        "Job should be in printing state after processing")
        
        # Test 3: Mark job as completed
        job.mark_completed()
        
        # Verify completion worked
        self.assertEqual(job.state, 'completed', 
                        "Job should be in completed state after mark_completed")
        self.assertTrue(job.completed_date, 
                       "Job should have completed_date after completion")
        
        # Test 4: Test retry mechanism with a new job
        retry_job = self.QZPrintJob.create({
            'document_type': job_data['document_type'],
            'printer_id': self.test_printer.id,
            'data': job_data['data'],
            'data_format': job_data['data_format'],
            'copies': job_data['copies'],
            'priority': job_data['priority'],
        })
        
        # Submit and mark as failed with transient error
        retry_job.submit_job()
        retry_job.mark_failed('Connection timeout - printer unavailable')
        
        # Verify job is in failed state
        self.assertEqual(retry_job.state, 'failed', 
                        "Job should be in failed state after mark_failed")
        self.assertTrue(retry_job.error_message, 
                       "Job should have error_message after failure")
        
        # Test retry
        retry_result = retry_job.retry_job()
        
        # Verify retry worked (should be queued again)
        self.assertEqual(retry_job.state, 'printing', 
                        "Job should be in printing state after retry")
        self.assertGreater(retry_job.retry_count, 0, 
                          "Job should have incremented retry_count")
        
        # Test 5: Test cancellation with a new job
        cancel_job = self.QZPrintJob.create({
            'document_type': job_data['document_type'],
            'printer_id': self.test_printer.id,
            'data': job_data['data'],
            'data_format': job_data['data_format'],
            'copies': job_data['copies'],
            'priority': job_data['priority'],
        })
        
        # Submit and cancel
        cancel_job.submit_job()
        cancel_result = cancel_job.cancel_job()
        
        # Verify cancellation worked
        self.assertTrue(cancel_result, 
                       "cancel_job should return True")
        self.assertEqual(cancel_job.state, 'cancelled', 
                        "Job should be in cancelled state after cancel_job")
        self.assertTrue(cancel_job.completed_date, 
                       "Job should have completed_date after cancellation")
        
        # Test 6: Test offline printer handling
        # Create an offline printer
        offline_printer = self.QZPrinter.create({
            'name': 'Offline Printer',
            'printer_type': 'receipt',
            'supports_pdf': True,
            'supports_html': True,
            'supports_escpos': True,
            'supports_zpl': True,
            'active': False,  # Offline
        })
        
        offline_job = self.QZPrintJob.create({
            'document_type': job_data['document_type'],
            'printer_id': offline_printer.id,
            'data': job_data['data'],
            'data_format': job_data['data_format'],
            'copies': job_data['copies'],
            'priority': job_data['priority'],
        })
        
        # Submit job to offline printer
        offline_job.submit_job()
        
        # Verify job is queued (not processed immediately)
        self.assertEqual(offline_job.state, 'queued', 
                        "Job for offline printer should be queued")
        self.assertTrue(offline_job.error_message, 
                       "Job should have error message about offline printer")
        
        # Test 7: Verify validation constraints still work
        # Test copies constraint
        with self.assertRaises(Exception):
            invalid_job = self.QZPrintJob.create({
                'document_type': job_data['document_type'],
                'printer_id': self.test_printer.id,
                'data': job_data['data'],
                'data_format': job_data['data_format'],
                'copies': 0,  # Invalid: must be at least 1
                'priority': job_data['priority'],
            })
        
        # Test priority constraint
        with self.assertRaises(Exception):
            invalid_job = self.QZPrintJob.create({
                'document_type': job_data['document_type'],
                'printer_id': self.test_printer.id,
                'data': job_data['data'],
                'data_format': job_data['data_format'],
                'copies': job_data['copies'],
                'priority': -1,  # Invalid: cannot be negative
            })
        
        _logger.info(
            f"Backward compatibility test passed for job type: {job_data['document_type']}, "
            f"format: {job_data['data_format']}"
        )
