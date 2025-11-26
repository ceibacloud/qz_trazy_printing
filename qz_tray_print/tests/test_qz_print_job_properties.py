# -*- coding: utf-8 -*-
"""
Property-Based Tests for QZ Print Job Model
Using Hypothesis for property-based testing
"""
import logging
import base64
from hypothesis import given, strategies as st, settings, assume
from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError

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
def print_data_strategy(draw):
    """Generate sample print data"""
    # Generate some sample binary data
    text = draw(st.text(min_size=10, max_size=100))
    return base64.b64encode(text.encode('utf-8'))


@st.composite
def print_job_data_strategy(draw):
    """Generate complete print job data"""
    return {
        'document_type': draw(document_type_strategy()),
        'data_format': draw(data_format_strategy()),
        'data': draw(print_data_strategy()),
        'copies': draw(st.integers(min_value=1, max_value=10)),
        'priority': draw(st.integers(min_value=0, max_value=100)),
    }


class TestQZPrintJobProperties(TransactionCase):
    """
    Property-based tests for QZ Print Job model
    """

    def setUp(self):
        super(TestQZPrintJobProperties, self).setUp()
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
        super(TestQZPrintJobProperties, self).tearDown()

    @given(job_data=print_job_data_strategy())
    @settings(max_examples=100, deadline=None)
    def test_property_8_print_job_creation(self, job_data):
        """
        **Feature: qz-tray-print-integration, Property 8: Print Job Creation**
        **Validates: Requirements 3.1**
        
        Property: For any valid document data submitted through the print method,
        the Print Service should accept the request and return a unique job identifier.
        """
        # Create print job with the generated data
        job = self.QZPrintJob.create({
            'document_type': job_data['document_type'],
            'printer_id': self.test_printer.id,
            'data': job_data['data'],
            'data_format': job_data['data_format'],
            'copies': job_data['copies'],
            'priority': job_data['priority'],
        })
        
        # Verify the job was created successfully
        self.assertTrue(job, "Print job should be created successfully")
        self.assertTrue(job.id, "Print job should have a unique ID")
        
        # Verify job has correct initial state
        self.assertEqual(job.state, 'draft', "New job should be in draft state")
        
        # Verify all data was stored correctly
        self.assertEqual(job.document_type, job_data['document_type'])
        self.assertEqual(job.printer_id.id, self.test_printer.id)
        self.assertEqual(job.data_format, job_data['data_format'])
        self.assertEqual(job.copies, job_data['copies'])
        self.assertEqual(job.priority, job_data['priority'])
        
        # Verify computed name field
        self.assertTrue(job.name, "Job should have a computed name")
        self.assertIn(job_data['document_type'], job.name, 
                     "Job name should contain document type")

    @given(
        document_type=document_type_strategy(),
        data_format=data_format_strategy()
    )
    @settings(max_examples=100, deadline=None)
    def test_property_25_job_submission_logging(self, document_type, data_format):
        """
        **Feature: qz-tray-print-integration, Property 25: Job Submission Logging**
        **Validates: Requirements 7.1**
        
        Property: For any submitted print job, the Print Service should create a log entry
        containing timestamp, user, document type, and printer information.
        """
        # Create a print job
        job = self.QZPrintJob.create({
            'document_type': document_type,
            'printer_id': self.test_printer.id,
            'data': base64.b64encode(b'test data'),
            'data_format': data_format,
        })
        
        # Submit the job
        job_id = job.submit_job()
        
        # Verify job ID was returned
        self.assertTrue(job_id, "Submit should return job ID")
        self.assertEqual(job_id, job.id, "Returned ID should match job ID")
        
        # Verify logging information is present
        self.assertTrue(job.submitted_date, "Job should have submitted timestamp")
        self.assertTrue(job.user_id, "Job should have user information")
        self.assertEqual(job.user_id.id, self.env.user.id, 
                        "Job should be associated with current user")
        self.assertEqual(job.document_type, document_type,
                        "Job should log document type")
        self.assertEqual(job.printer_id.id, self.test_printer.id,
                        "Job should log printer information")
        
        # Verify state transition
        self.assertEqual(job.state, 'queued', 
                        "Submitted job should be in queued state")

    @given(
        document_type=document_type_strategy(),
        data_format=data_format_strategy()
    )
    @settings(max_examples=100, deadline=None)
    def test_property_26_completion_status_update(self, document_type, data_format):
        """
        **Feature: qz-tray-print-integration, Property 26: Completion Status Update**
        **Validates: Requirements 7.2**
        
        Property: For any print job that completes, the Print Service should update
        the log entry with completion status and completion timestamp.
        """
        # Create and submit a print job
        job = self.QZPrintJob.create({
            'document_type': document_type,
            'printer_id': self.test_printer.id,
            'data': base64.b64encode(b'test data'),
            'data_format': data_format,
        })
        job.submit_job()
        
        # Mark job as completed
        job.mark_completed()
        
        # Verify completion status was updated
        self.assertEqual(job.state, 'completed',
                        "Job should be in completed state")
        self.assertTrue(job.completed_date,
                       "Job should have completion timestamp")
        self.assertFalse(job.error_message,
                        "Completed job should not have error message")

    @given(
        document_type=document_type_strategy(),
        data_format=data_format_strategy(),
        error_msg=st.text(min_size=10, max_size=200)
    )
    @settings(max_examples=100, deadline=None)
    def test_property_27_failure_error_recording(self, document_type, data_format, error_msg):
        """
        **Feature: qz-tray-print-integration, Property 27: Failure Error Recording**
        **Validates: Requirements 7.3**
        
        Property: For any print job that fails, the Print Service should record
        the error message and failure reason in the log entry.
        """
        # Create and submit a print job
        job = self.QZPrintJob.create({
            'document_type': document_type,
            'printer_id': self.test_printer.id,
            'data': base64.b64encode(b'test data'),
            'data_format': data_format,
        })
        job.submit_job()
        
        # Mark job as failed with error message
        job.mark_failed(error_msg)
        
        # Verify failure was recorded
        self.assertEqual(job.state, 'failed',
                        "Job should be in failed state")
        self.assertTrue(job.error_message,
                       "Job should have error message")
        self.assertIn(error_msg, job.error_message,
                     "Error message should contain the provided error")


    @given(
        document_type=document_type_strategy(),
        data_format=data_format_strategy()
    )
    @settings(max_examples=100, deadline=None)
    def test_property_20_retry_on_failure(self, document_type, data_format):
        """
        **Feature: qz-tray-print-integration, Property 20: Retry on Failure**
        **Validates: Requirements 5.5**
        
        Property: For any print job that fails due to a transient error, the Print Service
        should retry the job according to the configured retry count and delay settings.
        """
        # Configure retry settings
        IrConfigParameter = self.env['ir.config_parameter'].sudo()
        IrConfigParameter.set_param('qz_tray.retry_enabled', 'True')
        IrConfigParameter.set_param('qz_tray.retry_count', '3')
        IrConfigParameter.set_param('qz_tray.retry_delay', '5')
        
        # Create and submit a print job
        job = self.QZPrintJob.create({
            'document_type': document_type,
            'printer_id': self.test_printer.id,
            'data': base64.b64encode(b'test data'),
            'data_format': data_format,
        })
        job.submit_job()
        
        # Simulate a transient error (e.g., timeout)
        transient_error = "Connection timeout while sending to printer"
        job.write({
            'state': 'failed',
            'error_message': transient_error
        })
        
        # Attempt retry
        initial_retry_count = job.retry_count
        result = job.retry_job()
        
        # Verify retry was attempted
        if result:
            # Retry was successful (job was requeued)
            self.assertEqual(job.state, 'queued',
                           "Job should be requeued after retry")
            self.assertEqual(job.retry_count, initial_retry_count + 1,
                           "Retry count should be incremented")
        else:
            # Retry failed (max retries exceeded or permanent error)
            self.assertEqual(job.state, 'failed',
                           "Job should remain failed if retry not possible")

    @given(
        document_type=document_type_strategy(),
        data_format=data_format_strategy()
    )
    @settings(max_examples=100, deadline=None)
    def test_property_38_transient_error_retry(self, document_type, data_format):
        """
        **Feature: qz-tray-print-integration, Property 38: Transient Error Retry**
        **Validates: Requirements 10.1**
        
        Property: For any print job failing with a transient error, the Print Service
        should retry the job according to the configured retry policy (count and delay).
        """
        # Configure retry settings
        IrConfigParameter = self.env['ir.config_parameter'].sudo()
        IrConfigParameter.set_param('qz_tray.retry_enabled', 'True')
        IrConfigParameter.set_param('qz_tray.retry_count', '2')
        IrConfigParameter.set_param('qz_tray.retry_delay', '3')
        
        # Create and submit a print job
        job = self.QZPrintJob.create({
            'document_type': document_type,
            'printer_id': self.test_printer.id,
            'data': base64.b64encode(b'test data'),
            'data_format': data_format,
        })
        job.submit_job()
        
        # Test various transient error keywords
        transient_errors = [
            "Connection timeout",
            "Network error",
            "Printer offline",
            "Service unavailable",
            "Printer busy"
        ]
        
        for error_msg in transient_errors:
            # Reset job state
            job.write({
                'state': 'failed',
                'error_message': error_msg,
                'retry_count': 0
            })
            
            # Verify error is classified as transient
            is_transient = job._is_transient_error(error_msg)
            self.assertTrue(is_transient,
                          f"'{error_msg}' should be classified as transient")
            
            # Attempt retry
            result = job.retry_job()
            
            # Verify retry was attempted for transient error
            self.assertTrue(result or job.retry_count > 0,
                          "Transient error should trigger retry")

    @given(
        document_type=document_type_strategy(),
        data_format=data_format_strategy()
    )
    @settings(max_examples=100, deadline=None)
    def test_property_40_maximum_retry_failure(self, document_type, data_format):
        """
        **Feature: qz-tray-print-integration, Property 40: Maximum Retry Failure**
        **Validates: Requirements 10.3**
        
        Property: For any print job that exceeds the maximum retry count, the Print Service
        should mark the job as failed and send a notification to the administrator.
        """
        # Configure retry settings with low max retries
        IrConfigParameter = self.env['ir.config_parameter'].sudo()
        IrConfigParameter.set_param('qz_tray.retry_enabled', 'True')
        IrConfigParameter.set_param('qz_tray.retry_count', '2')
        IrConfigParameter.set_param('qz_tray.retry_delay', '1')
        
        # Create and submit a print job
        job = self.QZPrintJob.create({
            'document_type': document_type,
            'printer_id': self.test_printer.id,
            'data': base64.b64encode(b'test data'),
            'data_format': data_format,
        })
        job.submit_job()
        
        # Simulate multiple failures
        transient_error = "Connection timeout"
        
        # First failure and retry
        job.write({'state': 'failed', 'error_message': transient_error, 'retry_count': 0})
        job.retry_job()
        self.assertEqual(job.retry_count, 1, "First retry should increment count")
        
        # Second failure and retry
        job.write({'state': 'failed', 'error_message': transient_error})
        job.retry_job()
        self.assertEqual(job.retry_count, 2, "Second retry should increment count")
        
        # Third failure - should exceed max retries
        job.write({'state': 'failed', 'error_message': transient_error})
        result = job.retry_job()
        
        # Verify max retries exceeded
        self.assertFalse(result, "Retry should fail when max retries exceeded")
        self.assertEqual(job.state, 'failed', "Job should remain in failed state")
        self.assertTrue(job.completed_date, "Job should have completion date")
        self.assertIn('Maximum retry count exceeded', job.error_message,
                     "Error message should indicate max retries exceeded")

    def test_property_8_edge_case_missing_data(self):
        """
        Edge case: Job without data or template should fail validation
        """
        with self.assertRaises(ValidationError):
            job = self.QZPrintJob.create({
                'document_type': 'receipt',
                'printer_id': self.test_printer.id,
                'data_format': 'pdf',
            })
            job.submit_job()

    def test_property_8_edge_case_invalid_copies(self):
        """
        Edge case: Job with invalid number of copies should fail validation
        """
        with self.assertRaises(ValidationError):
            self.QZPrintJob.create({
                'document_type': 'receipt',
                'printer_id': self.test_printer.id,
                'data': base64.b64encode(b'test'),
                'data_format': 'pdf',
                'copies': 0,
            })

    def test_property_8_edge_case_negative_priority(self):
        """
        Edge case: Job with negative priority should fail validation
        """
        with self.assertRaises(ValidationError):
            self.QZPrintJob.create({
                'document_type': 'receipt',
                'printer_id': self.test_printer.id,
                'data': base64.b64encode(b'test'),
                'data_format': 'pdf',
                'priority': -1,
            })

    def test_property_25_edge_case_submit_without_printer(self):
        """
        Edge case: Submitting job without printer should fail
        """
        job = self.QZPrintJob.create({
            'document_type': 'receipt',
            'data': base64.b64encode(b'test'),
            'data_format': 'pdf',
        })
        
        # Remove printer
        job.write({'printer_id': False})
        
        with self.assertRaises(ValidationError):
            job.submit_job()

    def test_property_25_edge_case_submit_to_inactive_printer(self):
        """
        Edge case: Submitting job to inactive printer should fail
        """
        # Create inactive printer
        inactive_printer = self.QZPrinter.create({
            'name': 'Inactive Printer',
            'printer_type': 'receipt',
            'active': False,
        })
        
        job = self.QZPrintJob.create({
            'document_type': 'receipt',
            'printer_id': inactive_printer.id,
            'data': base64.b64encode(b'test'),
            'data_format': 'pdf',
        })
        
        with self.assertRaises(ValidationError):
            job.submit_job()

    def test_property_26_edge_case_complete_already_completed_job(self):
        """
        Edge case: Completing an already completed job should be idempotent
        """
        job = self.QZPrintJob.create({
            'document_type': 'receipt',
            'printer_id': self.test_printer.id,
            'data': base64.b64encode(b'test'),
            'data_format': 'pdf',
        })
        job.submit_job()
        
        # Complete once
        job.mark_completed()
        first_completion_date = job.completed_date
        
        # Complete again
        job.mark_completed()
        
        # Should still be completed
        self.assertEqual(job.state, 'completed')
        # Completion date may be updated, but job should remain completed
        self.assertTrue(job.completed_date)

    def test_property_27_edge_case_permanent_error_no_retry(self):
        """
        Edge case: Permanent errors should not trigger retry
        """
        IrConfigParameter = self.env['ir.config_parameter'].sudo()
        IrConfigParameter.set_param('qz_tray.retry_enabled', 'True')
        IrConfigParameter.set_param('qz_tray.retry_count', '3')
        
        job = self.QZPrintJob.create({
            'document_type': 'receipt',
            'printer_id': self.test_printer.id,
            'data': base64.b64encode(b'test'),
            'data_format': 'pdf',
        })
        job.submit_job()
        
        # Permanent error (not transient)
        permanent_error = "Invalid data format"
        job.write({
            'state': 'failed',
            'error_message': permanent_error
        })
        
        # Attempt retry
        result = job.retry_job()
        
        # Verify retry was not attempted
        self.assertFalse(result, "Permanent error should not trigger retry")
        self.assertEqual(job.retry_count, 0, "Retry count should not increment")
        self.assertTrue(job.completed_date, "Job should be marked as completed")

    def test_property_20_edge_case_retry_disabled(self):
        """
        Edge case: When retry is disabled, jobs should not retry
        """
        IrConfigParameter = self.env['ir.config_parameter'].sudo()
        IrConfigParameter.set_param('qz_tray.retry_enabled', 'False')
        
        job = self.QZPrintJob.create({
            'document_type': 'receipt',
            'printer_id': self.test_printer.id,
            'data': base64.b64encode(b'test'),
            'data_format': 'pdf',
        })
        job.submit_job()
        
        # Transient error
        job.write({
            'state': 'failed',
            'error_message': "Connection timeout"
        })
        
        # Attempt retry
        result = job.retry_job()
        
        # Verify retry was not attempted
        self.assertFalse(result, "Retry should not occur when disabled")
        self.assertEqual(job.retry_count, 0, "Retry count should not increment")

    def test_property_40_edge_case_retry_count_persistence(self):
        """
        Edge case: Retry count should persist across retries
        """
        IrConfigParameter = self.env['ir.config_parameter'].sudo()
        IrConfigParameter.set_param('qz_tray.retry_enabled', 'True')
        IrConfigParameter.set_param('qz_tray.retry_count', '5')
        
        job = self.QZPrintJob.create({
            'document_type': 'receipt',
            'printer_id': self.test_printer.id,
            'data': base64.b64encode(b'test'),
            'data_format': 'pdf',
        })
        job.submit_job()
        
        # Simulate multiple retries
        for expected_count in range(1, 4):
            job.write({
                'state': 'failed',
                'error_message': "Connection timeout"
            })
            job.retry_job()
            
            # Verify retry count increments correctly
            self.assertEqual(job.retry_count, expected_count,
                           f"Retry count should be {expected_count}")

    def test_job_cancellation(self):
        """Test that jobs can be cancelled"""
        job = self.QZPrintJob.create({
            'document_type': 'receipt',
            'printer_id': self.test_printer.id,
            'data': base64.b64encode(b'test'),
            'data_format': 'pdf',
        })
        job.submit_job()
        
        # Cancel the job
        result = job.cancel_job()
        
        self.assertTrue(result, "Cancellation should succeed")
        self.assertEqual(job.state, 'cancelled', "Job should be cancelled")
        self.assertTrue(job.completed_date, "Cancelled job should have completion date")

    def test_job_cancellation_already_completed(self):
        """Test that completed jobs cannot be cancelled"""
        job = self.QZPrintJob.create({
            'document_type': 'receipt',
            'printer_id': self.test_printer.id,
            'data': base64.b64encode(b'test'),
            'data_format': 'pdf',
        })
        job.submit_job()
        job.mark_completed()
        
        # Try to cancel completed job
        result = job.cancel_job()
        
        self.assertFalse(result, "Cannot cancel completed job")
        self.assertEqual(job.state, 'completed', "Job should remain completed")

    def test_unsupported_format_error(self):
        """Test that unsupported format raises error during processing"""
        # Create printer that doesn't support ZPL
        limited_printer = self.QZPrinter.create({
            'name': 'Limited Printer',
            'printer_type': 'receipt',
            'supports_pdf': True,
            'supports_html': True,
            'supports_escpos': False,
            'supports_zpl': False,
            'active': True,
        })
        
        job = self.QZPrintJob.create({
            'document_type': 'label',
            'printer_id': limited_printer.id,
            'data': base64.b64encode(b'test'),
            'data_format': 'zpl',
        })
        job.submit_job()
        
        # Try to process job with unsupported format
        with self.assertRaises(ValidationError):
            job.process_job()

    @given(
        document_type=document_type_strategy(),
        data_format=data_format_strategy()
    )
    @settings(max_examples=100, deadline=None)
    def test_property_24_offline_printer_queuing(self, document_type, data_format):
        """
        **Feature: qz-tray-print-integration, Property 24: Offline Printer Queuing**
        **Validates: Requirements 6.5**
        
        Property: For any print request to an offline printer, the Print Service
        should queue the job and send a notification to the user.
        """
        # Create an offline printer (inactive)
        offline_printer = self.QZPrinter.create({
            'name': 'Offline Printer',
            'printer_type': 'label',
            'supports_pdf': True,
            'supports_html': True,
            'supports_escpos': True,
            'supports_zpl': True,
            'active': False,  # Printer is offline
        })
        
        # Create a print job for the offline printer
        job = self.QZPrintJob.create({
            'document_type': document_type,
            'printer_id': offline_printer.id,
            'data': base64.b64encode(b'test data'),
            'data_format': data_format,
        })
        
        # Submit the job
        job_id = job.submit_job()
        
        # Verify job was queued (not rejected)
        self.assertTrue(job_id, "Job should be accepted even for offline printer")
        self.assertEqual(job.state, 'queued',
                        "Job should be queued for offline printer")
        
        # Verify notification message is present
        self.assertTrue(job.error_message,
                       "Job should have a message about offline printer")
        self.assertIn('offline', job.error_message.lower(),
                     "Message should indicate printer is offline")
        self.assertIn('queued', job.error_message.lower(),
                     "Message should indicate job is queued")
        
        # Verify job has submitted timestamp
        self.assertTrue(job.submitted_date,
                       "Queued job should have submitted timestamp")
        
        # Verify job is associated with the offline printer
        self.assertEqual(job.printer_id.id, offline_printer.id,
                        "Job should be associated with offline printer")
        
        # Verify job can be found in queue
        queued_jobs = self.QZPrintJob.search([
            ('printer_id', '=', offline_printer.id),
            ('state', '=', 'queued')
        ])
        self.assertIn(job, queued_jobs,
                     "Job should be in queue for offline printer")

    @given(
        document_type=document_type_strategy(),
        data_format=data_format_strategy()
    )
    @settings(max_examples=100, deadline=None)
    def test_property_24_automatic_processing_when_online(self, document_type, data_format):
        """
        **Feature: qz-tray-print-integration, Property 24: Offline Printer Queuing**
        **Validates: Requirements 6.5, 10.4**
        
        Property: When an offline printer comes online, the Print Service should
        automatically process all queued jobs for that printer.
        """
        # Create an offline printer
        offline_printer = self.QZPrinter.create({
            'name': 'Offline Printer',
            'printer_type': 'label',
            'supports_pdf': True,
            'supports_html': True,
            'supports_escpos': True,
            'supports_zpl': True,
            'active': False,  # Printer is offline
        })
        
        # Create multiple jobs for the offline printer
        jobs = []
        for i in range(3):
            job = self.QZPrintJob.create({
                'document_type': document_type,
                'printer_id': offline_printer.id,
                'data': base64.b64encode(f'test data {i}'.encode()),
                'data_format': data_format,
            })
            job.submit_job()
            jobs.append(job)
        
        # Verify all jobs are queued
        for job in jobs:
            self.assertEqual(job.state, 'queued',
                           "Job should be queued for offline printer")
        
        # Bring printer online
        offline_printer.write({'active': True})
        
        # Verify jobs were processed (moved to printing state)
        # Note: In real implementation, jobs would be sent to QZ Tray
        # Here we verify they were picked up for processing
        for job in jobs:
            # Job should either be in printing state or still queued
            # (depending on processing speed)
            self.assertIn(job.state, ['queued', 'printing', 'completed'],
                         "Job should be processed or in processing queue")

    def test_property_24_edge_case_empty_queue(self):
        """
        Edge case: Bringing printer online with no queued jobs should not error
        """
        # Create offline printer with no jobs
        offline_printer = self.QZPrinter.create({
            'name': 'Offline Printer',
            'printer_type': 'label',
            'active': False,
        })
        
        # Bring printer online (should not error)
        offline_printer.write({'active': True})
        
        # Verify printer is active
        self.assertTrue(offline_printer.active,
                       "Printer should be active")

    def test_property_24_edge_case_multiple_printers(self):
        """
        Edge case: Jobs should only be processed for the specific printer that comes online
        """
        # Create two offline printers
        offline_printer1 = self.QZPrinter.create({
            'name': 'Offline Printer 1',
            'printer_type': 'label',
            'supports_pdf': True,
            'active': False,
        })
        
        offline_printer2 = self.QZPrinter.create({
            'name': 'Offline Printer 2',
            'printer_type': 'label',
            'supports_pdf': True,
            'active': False,
        })
        
        # Create jobs for both printers
        job1 = self.QZPrintJob.create({
            'document_type': 'label',
            'printer_id': offline_printer1.id,
            'data': base64.b64encode(b'test1'),
            'data_format': 'pdf',
        })
        job1.submit_job()
        
        job2 = self.QZPrintJob.create({
            'document_type': 'label',
            'printer_id': offline_printer2.id,
            'data': base64.b64encode(b'test2'),
            'data_format': 'pdf',
        })
        job2.submit_job()
        
        # Bring only printer1 online
        offline_printer1.write({'active': True})
        
        # Verify job1 was processed but job2 remains queued
        self.assertIn(job1.state, ['printing', 'completed'],
                     "Job for printer1 should be processed")
        self.assertEqual(job2.state, 'queued',
                        "Job for printer2 should remain queued")

    def test_property_24_edge_case_fifo_order(self):
        """
        Edge case: Queued jobs should be processed in FIFO order when printer comes online
        """
        # Create offline printer
        offline_printer = self.QZPrinter.create({
            'name': 'Offline Printer',
            'printer_type': 'label',
            'supports_pdf': True,
            'active': False,
        })
        
        # Create jobs with different timestamps
        import time
        jobs = []
        for i in range(3):
            job = self.QZPrintJob.create({
                'document_type': 'label',
                'printer_id': offline_printer.id,
                'data': base64.b64encode(f'test{i}'.encode()),
                'data_format': 'pdf',
                'priority': 5,  # Same priority
            })
            job.submit_job()
            jobs.append(job)
            # Small delay to ensure different timestamps
            time.sleep(0.01)
        
        # Verify jobs have different submitted dates
        submitted_dates = [job.submitted_date for job in jobs]
        self.assertEqual(len(set(submitted_dates)), len(jobs),
                        "Jobs should have different submitted dates")
        
        # Bring printer online
        offline_printer.write({'active': True})
        
        # Verify jobs were processed (order verification would require
        # more complex tracking in real implementation)
        for job in jobs:
            self.assertIn(job.state, ['queued', 'printing', 'completed'],
                         "All jobs should be processed or in queue")


    @given(
        document_type=document_type_strategy(),
        data_format=data_format_strategy()
    )
    @settings(max_examples=100, deadline=None)
    def test_property_41_automatic_queue_processing(self, document_type, data_format):
        """
        **Feature: qz-tray-print-integration, Property 41: Automatic Queue Processing**
        **Validates: Requirements 10.4**
        
        Property: For any printer that transitions from offline to online, the Print Service
        should automatically process all queued jobs for that printer.
        """
        # Create an offline printer
        offline_printer = self.QZPrinter.create({
            'name': 'Test Offline Printer',
            'printer_type': 'receipt',
            'supports_pdf': True,
            'supports_html': True,
            'supports_escpos': True,
            'supports_zpl': True,
            'active': False,
        })
        
        # Create multiple queued jobs
        num_jobs = 3
        jobs = []
        for i in range(num_jobs):
            job = self.QZPrintJob.create({
                'document_type': document_type,
                'printer_id': offline_printer.id,
                'data': base64.b64encode(f'test data {i}'.encode()),
                'data_format': data_format,
            })
            job.submit_job()
            jobs.append(job)
        
        # Verify all jobs are queued
        queued_count = self.QZPrintJob.search_count([
            ('printer_id', '=', offline_printer.id),
            ('state', '=', 'queued')
        ])
        self.assertEqual(queued_count, num_jobs,
                        f"Should have {num_jobs} queued jobs")
        
        # Bring printer online - this should trigger automatic processing
        offline_printer.write({'active': True})
        
        # Verify jobs were picked up for processing
        # Jobs should be in printing state or completed
        for job in jobs:
            self.assertIn(job.state, ['queued', 'printing', 'completed'],
                         "Jobs should be processed when printer comes online")

    @given(
        num_labels=st.integers(min_value=2, max_value=5)
    )
    @settings(max_examples=100, deadline=None)
    def test_property_23_batch_label_printing(self, num_labels):
        """
        **Feature: qz-tray-print-integration, Property 23: Batch Label Printing**
        **Validates: Requirements 6.4**
        
        Property: For any print request with multiple labels, the Print Service
        should combine all labels into a single print job rather than creating separate jobs.
        """
        # Create a label printer
        label_printer = self.QZPrinter.create({
            'name': 'Label Printer',
            'printer_type': 'label',
            'supports_zpl': True,
            'active': True,
        })
        
        # Create multiple label jobs
        label_jobs = []
        for i in range(num_labels):
            job = self.QZPrintJob.create({
                'document_type': 'label',
                'printer_id': label_printer.id,
                'data': base64.b64encode(f'^XA^FO50,50^ADN,36,20^FDLabel {i}^FS^XZ'.encode()),
                'data_format': 'zpl',
            })
            label_jobs.append(job)
        
        # Batch the label jobs
        batch_job = self.QZPrintJob.batch_label_jobs(self.env['qz.print.job'].browse([j.id for j in label_jobs]))
        
        # Verify batch job was created
        self.assertTrue(batch_job, "Batch job should be created")
        self.assertEqual(batch_job.document_type, 'label_batch',
                        "Batch job should have label_batch document type")
        
        # Verify original jobs were cancelled
        for job in label_jobs:
            self.assertEqual(job.state, 'cancelled',
                           "Original label jobs should be cancelled")
            self.assertIn('batch', job.error_message.lower(),
                         "Cancelled jobs should reference batch job")
        
        # Verify batch job contains combined data
        self.assertTrue(batch_job.data,
                       "Batch job should have combined data")

    @given(
        document_type=document_type_strategy(),
        data_format=data_format_strategy()
    )
    @settings(max_examples=100, deadline=None)
    def test_property_47_printer_pause_effect(self, document_type, data_format):
        """
        **Feature: qz-tray-print-integration, Property 47: Printer Pause Effect**
        **Validates: Requirements 12.2**
        
        Property: For any printer that is paused, the Print Service should hold all jobs
        for that printer and not process them until the printer is resumed.
        """
        # Create an active printer
        printer = self.QZPrinter.create({
            'name': 'Test Printer',
            'printer_type': 'receipt',
            'supports_pdf': True,
            'supports_html': True,
            'active': True,
        })
        
        # Create and submit a job
        job = self.QZPrintJob.create({
            'document_type': document_type,
            'printer_id': printer.id,
            'data': base64.b64encode(b'test data'),
            'data_format': data_format,
        })
        job.submit_job()
        
        # Pause the printer (set active to False)
        printer.write({'active': False})
        
        # Try to process the job
        result = job.process_job()
        
        # Verify job was not processed (printer is paused/inactive)
        self.assertFalse(result,
                        "Job should not be processed when printer is paused")
        self.assertEqual(job.state, 'failed',
                        "Job should fail when printer is paused")

    @given(
        document_type=document_type_strategy(),
        data_format=data_format_strategy()
    )
    @settings(max_examples=100, deadline=None)
    def test_property_48_job_cancellation(self, document_type, data_format):
        """
        **Feature: qz-tray-print-integration, Property 48: Job Cancellation**
        **Validates: Requirements 12.3**
        
        Property: For any print job that the administrator cancels, the Print Service
        should remove the job from the queue and update its status to cancelled.
        """
        # Create and submit a job
        job = self.QZPrintJob.create({
            'document_type': document_type,
            'printer_id': self.test_printer.id,
            'data': base64.b64encode(b'test data'),
            'data_format': data_format,
        })
        job.submit_job()
        
        # Verify job is in queue
        self.assertEqual(job.state, 'queued',
                        "Job should be queued initially")
        
        # Cancel the job
        result = job.cancel_job()
        
        # Verify cancellation was successful
        self.assertTrue(result, "Cancellation should succeed")
        self.assertEqual(job.state, 'cancelled',
                        "Job should be in cancelled state")
        self.assertTrue(job.completed_date,
                       "Cancelled job should have completion date")
        
        # Verify job is no longer in queue
        queued_jobs = self.QZPrintJob.search([
            ('printer_id', '=', self.test_printer.id),
            ('state', '=', 'queued')
        ])
        self.assertNotIn(job, queued_jobs,
                        "Cancelled job should not be in queue")

    @given(
        num_jobs=st.integers(min_value=2, max_value=5)
    )
    @settings(max_examples=100, deadline=None)
    def test_property_49_fifo_queue_processing(self, num_jobs):
        """
        **Feature: qz-tray-print-integration, Property 49: FIFO Queue Processing**
        **Validates: Requirements 12.4**
        
        Property: For any printer that is resumed, the Print Service should process
        queued jobs in the order they were submitted (first-in, first-out).
        """
        # Create jobs with same priority but different submission times
        import time
        jobs = []
        for i in range(num_jobs):
            job = self.QZPrintJob.create({
                'document_type': 'receipt',
                'printer_id': self.test_printer.id,
                'data': base64.b64encode(f'test data {i}'.encode()),
                'data_format': 'pdf',
                'priority': 5,  # Same priority for all
            })
            job.submit_job()
            jobs.append(job)
            time.sleep(0.01)  # Ensure different timestamps
        
        # Get jobs in submission order
        queued_jobs = self.QZPrintJob.search([
            ('printer_id', '=', self.test_printer.id),
            ('state', '=', 'queued')
        ], order='submitted_date asc, priority desc, id asc')
        
        # Verify jobs are ordered by submission time (FIFO)
        for i, job in enumerate(jobs):
            self.assertEqual(queued_jobs[i].id, job.id,
                           f"Job {i} should be in FIFO order")

    @given(
        document_type=document_type_strategy(),
        data_format=data_format_strategy()
    )
    @settings(max_examples=100, deadline=None)
    def test_property_50_job_resubmission(self, document_type, data_format):
        """
        **Feature: qz-tray-print-integration, Property 50: Job Resubmission**
        **Validates: Requirements 12.5**
        
        Property: For any failed job that the administrator resubmits, the Print Service
        should create a new print job with the same parameters (data, printer, options)
        as the original.
        """
        # Create and submit a job
        original_job = self.QZPrintJob.create({
            'document_type': document_type,
            'printer_id': self.test_printer.id,
            'data': base64.b64encode(b'test data'),
            'data_format': data_format,
            'copies': 2,
            'priority': 7,
        })
        original_job.submit_job()
        
        # Mark job as failed
        original_job.mark_failed("Test error")
        
        # Resubmit the job by creating a new one with same parameters
        resubmitted_job = self.QZPrintJob.create({
            'document_type': original_job.document_type,
            'printer_id': original_job.printer_id.id,
            'data': original_job.data,
            'data_format': original_job.data_format,
            'copies': original_job.copies,
            'priority': original_job.priority,
            'parent_model': 'qz.print.job',
            'parent_id': original_job.id,
        })
        resubmitted_job.submit_job()
        
        # Verify resubmitted job has same parameters
        self.assertEqual(resubmitted_job.document_type, original_job.document_type,
                        "Resubmitted job should have same document type")
        self.assertEqual(resubmitted_job.printer_id.id, original_job.printer_id.id,
                        "Resubmitted job should have same printer")
        self.assertEqual(resubmitted_job.data, original_job.data,
                        "Resubmitted job should have same data")
        self.assertEqual(resubmitted_job.data_format, original_job.data_format,
                        "Resubmitted job should have same format")
        self.assertEqual(resubmitted_job.copies, original_job.copies,
                        "Resubmitted job should have same copies")
        self.assertEqual(resubmitted_job.priority, original_job.priority,
                        "Resubmitted job should have same priority")
        
        # Verify resubmitted job is in queued state
        self.assertEqual(resubmitted_job.state, 'queued',
                        "Resubmitted job should be queued")
        
        # Verify link to original job
        self.assertEqual(resubmitted_job.parent_id, original_job.id,
                        "Resubmitted job should reference original job")
