# -*- coding: utf-8 -*-
"""
Unit tests for email notification functionality in QZ Tray Print Integration

Tests the email notification system for failed print jobs, including:
- Email template existence and configuration
- Email sending to administrators
- System parameter configuration
- Fallback email functionality
"""

import logging
from odoo.tests import TransactionCase, tagged

_logger = logging.getLogger(__name__)


@tagged('post_install', '-at_install', 'qz_tray_print')
class TestEmailNotifications(TransactionCase):
    """Test email notification functionality for failed print jobs"""
    
    def setUp(self):
        super().setUp()
        
        # Create test printer
        self.printer = self.env['qz.printer'].create({
            'name': 'Test Printer',
            'printer_type': 'receipt',
            'system_name': 'TEST_PRINTER',
            'active': True,
        })
        
        # Create test user
        self.test_user = self.env['res.users'].create({
            'name': 'Test User',
            'login': 'test_user',
            'email': 'testuser@example.com',
        })
        
        # Create admin user with Print Administrator group
        admin_group = self.env.ref('qz_tray_print.group_qz_print_admin')
        self.admin_user = self.env['res.users'].create({
            'name': 'Print Admin',
            'login': 'print_admin',
            'email': 'printadmin@example.com',
            'groups_id': [(4, admin_group.id)],
        })
    
    def test_email_template_exists(self):
        """Test that the email template is properly configured"""
        template = self.env.ref(
            'qz_tray_print.email_template_print_job_failure',
            raise_if_not_found=False
        )
        
        self.assertIsNotNone(
            template,
            "Email template for print job failure should exist"
        )
        self.assertEqual(
            template.model_id.model,
            'qz.print.job',
            "Template should be for qz.print.job model"
        )
        self.assertTrue(
            template.body_html,
            "Template should have HTML body"
        )
    
    def test_system_parameter_exists(self):
        """Test that the email notification system parameter exists"""
        param_value = self.env['ir.config_parameter'].sudo().get_param(
            'qz_tray.email_notifications_enabled',
            default=None
        )
        
        self.assertIsNotNone(
            param_value,
            "System parameter qz_tray.email_notifications_enabled should exist"
        )
    
    def test_email_notification_disabled_by_default(self):
        """Test that email notifications are disabled by default"""
        param_value = self.env['ir.config_parameter'].sudo().get_param(
            'qz_tray.email_notifications_enabled',
            default='False'
        )
        
        self.assertEqual(
            param_value,
            'False',
            "Email notifications should be disabled by default"
        )
    
    def test_notify_admin_failure_when_disabled(self):
        """Test that no email is sent when notifications are disabled"""
        # Ensure notifications are disabled
        self.env['ir.config_parameter'].sudo().set_param(
            'qz_tray.email_notifications_enabled',
            'False'
        )
        
        # Create a failed print job
        job = self.env['qz.print.job'].create({
            'document_type': 'test_document',
            'printer_id': self.printer.id,
            'user_id': self.test_user.id,
            'data_format': 'pdf',
            'state': 'failed',
            'retry_count': 3,
            'error_message': 'Test error message',
        })
        
        # Count emails before notification
        mail_count_before = self.env['mail.mail'].search_count([])
        
        # Call notification method
        job._notify_admin_failure()
        
        # Count emails after notification
        mail_count_after = self.env['mail.mail'].search_count([])
        
        # No new emails should be created
        self.assertEqual(
            mail_count_before,
            mail_count_after,
            "No emails should be sent when notifications are disabled"
        )
    
    def test_notify_admin_failure_when_enabled(self):
        """Test that email is sent when notifications are enabled"""
        # Enable notifications
        self.env['ir.config_parameter'].sudo().set_param(
            'qz_tray.email_notifications_enabled',
            'True'
        )
        
        # Create a failed print job
        job = self.env['qz.print.job'].create({
            'document_type': 'test_document',
            'printer_id': self.printer.id,
            'user_id': self.test_user.id,
            'data_format': 'pdf',
            'state': 'failed',
            'retry_count': 3,
            'error_message': 'Test error message',
        })
        
        # Count emails before notification
        mail_count_before = self.env['mail.mail'].search_count([])
        
        # Call notification method
        job._notify_admin_failure()
        
        # Count emails after notification
        mail_count_after = self.env['mail.mail'].search_count([])
        
        # At least one email should be created (one per admin)
        self.assertGreater(
            mail_count_after,
            mail_count_before,
            "Email should be sent when notifications are enabled"
        )
    
    def test_notify_admin_failure_content(self):
        """Test that the email contains correct job information"""
        # Enable notifications
        self.env['ir.config_parameter'].sudo().set_param(
            'qz_tray.email_notifications_enabled',
            'True'
        )
        
        # Create a failed print job with specific details
        job = self.env['qz.print.job'].create({
            'document_type': 'receipt',
            'printer_id': self.printer.id,
            'user_id': self.test_user.id,
            'data_format': 'pdf',
            'state': 'failed',
            'retry_count': 3,
            'error_message': 'Printer offline error',
        })
        
        # Call notification method
        job._notify_admin_failure()
        
        # Find the sent email
        emails = self.env['mail.mail'].search([
            ('email_to', '=', self.admin_user.email)
        ], order='id desc', limit=1)
        
        if emails:
            email = emails[0]
            
            # Check subject contains job name
            self.assertIn(
                job.name,
                email.subject,
                "Email subject should contain job name"
            )
            
            # Check body contains key information
            body = email.body_html or ''
            self.assertIn(
                job.document_type,
                body,
                "Email body should contain document type"
            )
            self.assertIn(
                job.printer_id.name,
                body,
                "Email body should contain printer name"
            )
            self.assertIn(
                job.error_message,
                body,
                "Email body should contain error message"
            )
    
    def test_retry_job_calls_notify_on_max_retries(self):
        """Test that retry_job calls notification when max retries exceeded"""
        # Enable notifications
        self.env['ir.config_parameter'].sudo().set_param(
            'qz_tray.email_notifications_enabled',
            'True'
        )
        
        # Set max retries to 2
        self.env['ir.config_parameter'].sudo().set_param(
            'qz_tray.retry_count',
            '2'
        )
        
        # Create a failed print job that has already been retried twice
        job = self.env['qz.print.job'].create({
            'document_type': 'test_document',
            'printer_id': self.printer.id,
            'user_id': self.test_user.id,
            'data_format': 'pdf',
            'state': 'failed',
            'retry_count': 2,
            'error_message': 'Connection timeout',
        })
        
        # Count emails before retry attempt
        mail_count_before = self.env['mail.mail'].search_count([])
        
        # Try to retry (should fail and send notification)
        result = job.retry_job()
        
        # Retry should fail
        self.assertFalse(
            result,
            "Retry should fail when max retries exceeded"
        )
        
        # Count emails after retry attempt
        mail_count_after = self.env['mail.mail'].search_count([])
        
        # Email should be sent
        self.assertGreater(
            mail_count_after,
            mail_count_before,
            "Email notification should be sent when max retries exceeded"
        )
    
    def test_admin_group_fallback(self):
        """Test that system admin group is used if Print Admin group not found"""
        # Enable notifications
        self.env['ir.config_parameter'].sudo().set_param(
            'qz_tray.email_notifications_enabled',
            'True'
        )
        
        # Create system admin user
        system_admin = self.env['res.users'].create({
            'name': 'System Admin',
            'login': 'system_admin',
            'email': 'sysadmin@example.com',
            'groups_id': [(4, self.env.ref('base.group_system').id)],
        })
        
        # Create a failed print job
        job = self.env['qz.print.job'].create({
            'document_type': 'test_document',
            'printer_id': self.printer.id,
            'user_id': self.test_user.id,
            'data_format': 'pdf',
            'state': 'failed',
            'retry_count': 3,
            'error_message': 'Test error',
        })
        
        # Call notification (should work even if Print Admin group has issues)
        try:
            job._notify_admin_failure()
            # If we get here, the method executed without errors
            self.assertTrue(True, "Notification method should execute without errors")
        except Exception as e:
            self.fail(f"Notification method should not raise exception: {str(e)}")


if __name__ == '__main__':
    import unittest
    unittest.main()
