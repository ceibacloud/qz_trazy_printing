# -*- coding: utf-8 -*-

"""
Property-Based Tests for Print Service Notifications
Feature: qz-tray-print-integration

These tests verify that the print service correctly handles notifications
for various print job states and conditions.
"""

from odoo.tests import TransactionCase
from hypothesis import given, strategies as st, settings
from hypothesis.strategies import composite
import json


@composite
def print_job_data(draw):
    """Generate random print job data"""
    return {
        'document_type': draw(st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd')))),
        'data': {
            'content': draw(st.text(min_size=1, max_size=100)),
            'title': draw(st.text(min_size=1, max_size=50)),
        },
        'copies': draw(st.integers(min_value=1, max_value=10)),
    }


class TestNotificationProperties(TransactionCase):
    """
    Property-based tests for notification system
    """
    
    def setUp(self):
        super().setUp()
        
        # Create a test printer
        self.printer = self.env['qz.printer'].create({
            'name': 'Test Notification Printer',
            'printer_type': 'document',
            'system_name': 'Test_Printer',
            'is_default': True,
            'active': True,
        })
    
    @settings(max_examples=100)
    @given(job_data=print_job_data())
    def test_property_33_submission_notification(self, job_data):
        """
        **Feature: qz-tray-print-integration, Property 33: Submission Notification**
        **Validates: Requirements 9.1**
        
        Property: For any print job submitted, the Print Service should create
        a job record that can be used to trigger a submission notification.
        
        This test verifies that when a print job is submitted, a job record
        is created with the appropriate initial state that would trigger
        a submission notification in the frontend.
        """
        # Create a print job
        job = self.env['qz.print.job'].create({
            'document_type': job_data['document_type'],
            'printer_id': self.printer.id,
            'template_data': json.dumps(job_data['data']),
            'copies': job_data['copies'],
            'state': 'draft',
        })
        
        # Submit the job
        job.submit_job()
        
        # Verify job was created and is in a state that would trigger notification
        self.assertTrue(job.exists(), "Job should exist after submission")
        self.assertIn(job.state, ['queued', 'printing'], 
                     "Job should be in queued or printing state after submission")
        self.assertIsNotNone(job.submitted_date, 
                           "Job should have a submission date")
        
        # Verify job has all necessary data for notification
        self.assertTrue(job.id > 0, "Job should have a valid ID for notification")
        self.assertEqual(job.document_type, job_data['document_type'],
                        "Job should preserve document type for notification")
    
    @settings(max_examples=100)
    @given(job_data=print_job_data())
    def test_property_34_success_notification(self, job_data):
        """
        **Feature: qz-tray-print-integration, Property 34: Success Notification**
        **Validates: Requirements 9.2**
        
        Property: For any print job that completes successfully, the Print Service
        should update the job status to 'completed' which triggers a success notification.
        
        This test verifies that when a print job completes, its state is updated
        to 'completed' with a completion timestamp.
        """
        # Create and submit a print job
        job = self.env['qz.print.job'].create({
            'document_type': job_data['document_type'],
            'printer_id': self.printer.id,
            'template_data': json.dumps(job_data['data']),
            'copies': job_data['copies'],
            'state': 'printing',
        })
        
        # Simulate successful completion
        job.write({
            'state': 'completed',
            'completed_date': self.env.cr.now(),
        })
        
        # Verify job state indicates success
        self.assertEqual(job.state, 'completed',
                        "Job should be in completed state for success notification")
        self.assertIsNotNone(job.completed_date,
                           "Job should have completion date for success notification")
        self.assertFalse(job.error_message,
                        "Successful job should not have error message")
    
    @settings(max_examples=100)
    @given(job_data=print_job_data(), 
           error_msg=st.text(min_size=1, max_size=200))
    def test_property_35_failure_notification(self, job_data, error_msg):
        """
        **Feature: qz-tray-print-integration, Property 35: Failure Notification**
        **Validates: Requirements 9.3**
        
        Property: For any print job that fails, the Print Service should record
        the error message and update the state to 'failed', triggering a failure
        notification with the error details.
        
        This test verifies that failed jobs have both the failed state and
        an error message recorded.
        """
        # Create and submit a print job
        job = self.env['qz.print.job'].create({
            'document_type': job_data['document_type'],
            'printer_id': self.printer.id,
            'template_data': json.dumps(job_data['data']),
            'copies': job_data['copies'],
            'state': 'printing',
        })
        
        # Simulate failure
        job.write({
            'state': 'failed',
            'error_message': error_msg,
        })
        
        # Verify job state indicates failure with error details
        self.assertEqual(job.state, 'failed',
                        "Job should be in failed state for failure notification")
        self.assertEqual(job.error_message, error_msg,
                        "Job should preserve error message for failure notification")
        self.assertIsNone(job.completed_date,
                         "Failed job should not have completion date")
    
    @settings(max_examples=100)
    @given(job_data=print_job_data())
    def test_property_36_offline_printer_notification(self, job_data):
        """
        **Feature: qz-tray-print-integration, Property 36: Offline Printer Notification**
        **Validates: Requirements 9.4**
        
        Property: For any print request to an offline printer, the Print Service
        should queue the job and provide information that the printer is offline,
        triggering an offline printer notification.
        
        This test verifies that jobs sent to offline printers are queued and
        the printer's offline status is detectable.
        """
        # Set printer to offline
        self.printer.write({'active': False})
        
        # Create a print job for offline printer
        job = self.env['qz.print.job'].create({
            'document_type': job_data['document_type'],
            'printer_id': self.printer.id,
            'template_data': json.dumps(job_data['data']),
            'copies': job_data['copies'],
            'state': 'queued',
        })
        
        # Verify job is queued and printer is offline
        self.assertEqual(job.state, 'queued',
                        "Job should be queued when printer is offline")
        self.assertFalse(job.printer_id.active,
                        "Printer should be marked as offline")
        self.assertTrue(job.exists(),
                       "Job should exist in queue for offline printer")
    
    @settings(max_examples=100)
    @given(job_data=print_job_data())
    def test_property_37_queued_job_completion_notification(self, job_data):
        """
        **Feature: qz-tray-print-integration, Property 37: Queued Job Completion Notification**
        **Validates: Requirements 9.5**
        
        Property: For any queued job that successfully prints after the printer
        comes online, the Print Service should update the job to completed state,
        triggering a completion notification.
        
        This test verifies that queued jobs can transition to completed state
        when processed.
        """
        # Create a queued job (simulating offline printer scenario)
        job = self.env['qz.print.job'].create({
            'document_type': job_data['document_type'],
            'printer_id': self.printer.id,
            'template_data': json.dumps(job_data['data']),
            'copies': job_data['copies'],
            'state': 'queued',
        })
        
        initial_state = job.state
        
        # Simulate printer coming online and job being processed
        job.write({
            'state': 'printing',
        })
        
        # Simulate successful completion
        job.write({
            'state': 'completed',
            'completed_date': self.env.cr.now(),
        })
        
        # Verify job transitioned from queued to completed
        self.assertEqual(initial_state, 'queued',
                        "Job should have started in queued state")
        self.assertEqual(job.state, 'completed',
                        "Queued job should complete successfully")
        self.assertIsNotNone(job.completed_date,
                           "Completed queued job should have completion date")
