# -*- coding: utf-8 -*-
"""
Checkpoint Verification Tests for QZ Tray Print Integration

This test file verifies all core functionality as specified in Task 18:
- All views are accessible from menus
- Window actions open correct views
- Client actions are properly registered
- Print job submission through UI
- Job cancellation, retry, and resubmit actions
- Record rules restrict job visibility correctly
- Email notifications for failed jobs
"""

import logging
from odoo.tests import tagged, TransactionCase
from odoo.exceptions import AccessError, ValidationError

_logger = logging.getLogger(__name__)


@tagged('post_install', '-at_install', 'qz_tray', 'checkpoint')
class TestCheckpointVerification(TransactionCase):
    """
    Comprehensive verification tests for QZ Tray Print Integration
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        
        # Create test users with different access levels
        cls.print_user = cls.env['res.users'].create({
            'name': 'Print User Test',
            'login': 'print_user_test',
            'email': 'print_user@test.com',
            'groups_id': [(6, 0, [
                cls.env.ref('base.group_user').id,
                cls.env.ref('qz_tray_print.group_qz_print_user').id,
            ])]
        })
        
        cls.print_manager = cls.env['res.users'].create({
            'name': 'Print Manager Test',
            'login': 'print_manager_test',
            'email': 'print_manager@test.com',
            'groups_id': [(6, 0, [
                cls.env.ref('base.group_user').id,
                cls.env.ref('qz_tray_print.group_qz_print_manager').id,
            ])]
        })
        
        cls.print_admin = cls.env['res.users'].create({
            'name': 'Print Admin Test',
            'login': 'print_admin_test',
            'email': 'print_admin@test.com',
            'groups_id': [(6, 0, [
                cls.env.ref('base.group_user').id,
                cls.env.ref('qz_tray_print.group_qz_print_admin').id,
            ])]
        })
        
        # Create test printer
        cls.test_printer = cls.env['qz.printer'].create({
            'name': 'Test Receipt Printer',
            'printer_type': 'receipt',
            'system_name': 'TEST_PRINTER_01',
            'paper_size': '80mm',
            'is_default': True,
            'active': True,
            'supports_pdf': True,
            'supports_html': True,
        })
        
        # Create test print jobs for different users
        cls.user_job = cls.env['qz.print.job'].with_user(cls.print_user).create({
            'document_type': 'receipt',
            'printer_id': cls.test_printer.id,
            'data_format': 'html',
            'data': b'<html><body>Test Receipt</body></html>',
            'state': 'draft',
        })
        
        cls.manager_job = cls.env['qz.print.job'].with_user(cls.print_manager).create({
            'document_type': 'invoice',
            'printer_id': cls.test_printer.id,
            'data_format': 'pdf',
            'data': b'%PDF-1.4 test',
            'state': 'queued',
        })

    def test_01_menu_structure_exists(self):
        """Verify all menus are properly defined"""
        _logger.info('Testing menu structure...')
        
        # Check root menu
        root_menu = self.env.ref('qz_tray_print.menu_qz_tray_root', raise_if_not_found=False)
        self.assertTrue(root_menu, 'Root menu should exist')
        
        # Check configuration menu
        config_menu = self.env.ref('qz_tray_print.menu_qz_tray_config', raise_if_not_found=False)
        self.assertTrue(config_menu, 'Configuration menu should exist')
        
        # Check printers menu
        printers_menu = self.env.ref('qz_tray_print.menu_qz_printers', raise_if_not_found=False)
        self.assertTrue(printers_menu, 'Printers menu should exist')
        self.assertTrue(printers_menu.action, 'Printers menu should have an action')
        
        # Check print queue menu
        queue_menu = self.env.ref('qz_tray_print.menu_qz_print_queue', raise_if_not_found=False)
        self.assertTrue(queue_menu, 'Print queue menu should exist')
        self.assertTrue(queue_menu.action, 'Print queue menu should have an action')
        
        # Check print jobs menu
        jobs_menu = self.env.ref('qz_tray_print.menu_qz_print_jobs', raise_if_not_found=False)
        self.assertTrue(jobs_menu, 'Print jobs menu should exist')
        self.assertTrue(jobs_menu.action, 'Print jobs menu should have an action')
        
        _logger.info('✓ All menus exist and are properly configured')

    def test_02_window_actions_exist(self):
        """Verify all window actions are properly defined"""
        _logger.info('Testing window actions...')
        
        # Check printer action
        printer_action = self.env.ref('qz_tray_print.action_qz_printer', raise_if_not_found=False)
        self.assertTrue(printer_action, 'Printer window action should exist')
        self.assertEqual(printer_action.res_model, 'qz.printer', 'Printer action should target qz.printer model')
        self.assertIn('list', printer_action.view_mode, 'Printer action should include list view')
        self.assertIn('form', printer_action.view_mode, 'Printer action should include form view')
        
        # Check print job action
        job_action = self.env.ref('qz_tray_print.action_qz_print_job', raise_if_not_found=False)
        self.assertTrue(job_action, 'Print job window action should exist')
        self.assertEqual(job_action.res_model, 'qz.print.job', 'Job action should target qz.print.job model')
        self.assertIn('list', job_action.view_mode, 'Job action should include list view')
        self.assertIn('form', job_action.view_mode, 'Job action should include form view')
        
        # Check print queue action
        queue_action = self.env.ref('qz_tray_print.action_qz_print_queue', raise_if_not_found=False)
        self.assertTrue(queue_action, 'Print queue window action should exist')
        self.assertEqual(queue_action.res_model, 'qz.print.job', 'Queue action should target qz.print.job model')
        self.assertIn('kanban', queue_action.view_mode, 'Queue action should include kanban view')
        
        _logger.info('✓ All window actions exist and are properly configured')

    def test_03_views_exist(self):
        """Verify all views are properly defined"""
        _logger.info('Testing view definitions...')
        
        # Printer views
        printer_tree = self.env.ref('qz_tray_print.view_qz_printer_tree', raise_if_not_found=False)
        self.assertTrue(printer_tree, 'Printer tree view should exist')
        
        printer_form = self.env.ref('qz_tray_print.view_qz_printer_form', raise_if_not_found=False)
        self.assertTrue(printer_form, 'Printer form view should exist')
        
        printer_search = self.env.ref('qz_tray_print.view_qz_printer_search', raise_if_not_found=False)
        self.assertTrue(printer_search, 'Printer search view should exist')
        
        # Print job views
        job_tree = self.env.ref('qz_tray_print.view_qz_print_job_tree', raise_if_not_found=False)
        self.assertTrue(job_tree, 'Print job tree view should exist')
        
        job_form = self.env.ref('qz_tray_print.view_qz_print_job_form', raise_if_not_found=False)
        self.assertTrue(job_form, 'Print job form view should exist')
        
        job_search = self.env.ref('qz_tray_print.view_qz_print_job_search', raise_if_not_found=False)
        self.assertTrue(job_search, 'Print job search view should exist')
        
        job_kanban = self.env.ref('qz_tray_print.view_qz_print_job_kanban', raise_if_not_found=False)
        self.assertTrue(job_kanban, 'Print job kanban view should exist')
        
        _logger.info('✓ All views exist and are properly defined')

    def test_04_print_job_submission(self):
        """Verify print job submission through UI"""
        _logger.info('Testing print job submission...')
        
        # Create a new print job
        job = self.env['qz.print.job'].create({
            'document_type': 'test_document',
            'printer_id': self.test_printer.id,
            'data_format': 'html',
            'data': b'<html><body>Test Document</body></html>',
        })
        
        self.assertTrue(job, 'Print job should be created')
        self.assertEqual(job.state, 'draft', 'New job should be in draft state')
        
        # Submit the job
        job_id = job.submit_job()
        
        self.assertEqual(job_id, job.id, 'Submit should return job ID')
        self.assertEqual(job.state, 'queued', 'Submitted job should be in queued state')
        self.assertTrue(job.submitted_date, 'Submitted job should have submitted_date')
        
        _logger.info('✓ Print job submission works correctly')

    def test_05_job_cancellation(self):
        """Verify job cancellation action"""
        _logger.info('Testing job cancellation...')
        
        # Create and submit a job
        job = self.env['qz.print.job'].create({
            'document_type': 'test_cancel',
            'printer_id': self.test_printer.id,
            'data_format': 'html',
            'data': b'<html><body>Cancel Test</body></html>',
        })
        job.submit_job()
        
        self.assertEqual(job.state, 'queued', 'Job should be queued')
        
        # Cancel the job
        result = job.cancel_job()
        
        self.assertTrue(result, 'Cancel should return True')
        self.assertEqual(job.state, 'cancelled', 'Job should be cancelled')
        self.assertTrue(job.completed_date, 'Cancelled job should have completed_date')
        
        _logger.info('✓ Job cancellation works correctly')

    def test_06_job_retry(self):
        """Verify job retry action"""
        _logger.info('Testing job retry...')
        
        # Enable retry in configuration
        self.env['ir.config_parameter'].sudo().set_param('qz_tray.retry_enabled', 'True')
        self.env['ir.config_parameter'].sudo().set_param('qz_tray.retry_count', '3')
        
        # Create a failed job
        job = self.env['qz.print.job'].create({
            'document_type': 'test_retry',
            'printer_id': self.test_printer.id,
            'data_format': 'html',
            'data': b'<html><body>Retry Test</body></html>',
            'state': 'failed',
            'error_message': 'Connection timeout - transient error',
        })
        
        initial_retry_count = job.retry_count
        
        # Retry the job
        result = job.retry_job()
        
        self.assertTrue(result, 'Retry should succeed for transient error')
        self.assertEqual(job.retry_count, initial_retry_count + 1, 'Retry count should increment')
        
        _logger.info('✓ Job retry works correctly')

    def test_07_job_resubmission(self):
        """Verify job resubmission action"""
        _logger.info('Testing job resubmission...')
        
        # Create a failed job
        job = self.env['qz.print.job'].create({
            'document_type': 'test_resubmit',
            'printer_id': self.test_printer.id,
            'data_format': 'html',
            'data': b'<html><body>Resubmit Test</body></html>',
            'state': 'failed',
            'error_message': 'Test error',
        })
        
        # Resubmit the job (submit_job can be called on failed jobs)
        job_id = job.submit_job()
        
        self.assertEqual(job_id, job.id, 'Resubmit should return job ID')
        self.assertEqual(job.state, 'queued', 'Resubmitted job should be queued')
        
        _logger.info('✓ Job resubmission works correctly')

    def test_08_record_rules_user_access(self):
        """Verify record rules restrict job visibility for users"""
        _logger.info('Testing record rules for print users...')
        
        # Print user should only see their own jobs
        user_jobs = self.env['qz.print.job'].with_user(self.print_user).search([])
        
        # Check that user can see their own job
        self.assertIn(self.user_job, user_jobs, 'User should see their own job')
        
        # Check that user cannot see manager's job
        self.assertNotIn(self.manager_job, user_jobs, 'User should not see other users\' jobs')
        
        # Try to access manager's job directly (should fail or be filtered)
        try:
            job_read = self.env['qz.print.job'].with_user(self.print_user).browse(self.manager_job.id)
            # If we can browse it, check if we can read it
            job_read.read(['name'])
            # If we get here, the record rule didn't restrict access properly
            self.fail('User should not be able to read other users\' jobs')
        except AccessError:
            # Expected behavior - access denied
            pass
        
        _logger.info('✓ Record rules correctly restrict user access')

    def test_09_record_rules_manager_access(self):
        """Verify record rules allow managers to see all jobs"""
        _logger.info('Testing record rules for print managers...')
        
        # Print manager should see all jobs
        manager_jobs = self.env['qz.print.job'].with_user(self.print_manager).search([])
        
        # Check that manager can see both jobs
        self.assertIn(self.user_job, manager_jobs, 'Manager should see user job')
        self.assertIn(self.manager_job, manager_jobs, 'Manager should see their own job')
        
        _logger.info('✓ Record rules correctly allow manager access to all jobs')

    def test_10_record_rules_admin_access(self):
        """Verify record rules allow admins to see all jobs"""
        _logger.info('Testing record rules for print administrators...')
        
        # Print admin should see all jobs
        admin_jobs = self.env['qz.print.job'].with_user(self.print_admin).search([])
        
        # Check that admin can see all jobs
        self.assertIn(self.user_job, admin_jobs, 'Admin should see user job')
        self.assertIn(self.manager_job, admin_jobs, 'Admin should see manager job')
        
        _logger.info('✓ Record rules correctly allow admin access to all jobs')

    def test_11_email_notification_system(self):
        """Verify email notification system for failed jobs"""
        _logger.info('Testing email notification system...')
        
        # Enable email notifications
        self.env['ir.config_parameter'].sudo().set_param('qz_tray.email_notifications_enabled', 'True')
        self.env['ir.config_parameter'].sudo().set_param('qz_tray.retry_enabled', 'True')
        self.env['ir.config_parameter'].sudo().set_param('qz_tray.retry_count', '2')
        
        # Create a job that will fail after max retries
        job = self.env['qz.print.job'].create({
            'document_type': 'test_email',
            'printer_id': self.test_printer.id,
            'data_format': 'html',
            'data': b'<html><body>Email Test</body></html>',
            'state': 'failed',
            'error_message': 'Connection timeout',
            'retry_count': 2,  # Already at max retries
        })
        
        # Count emails before
        mail_count_before = self.env['mail.mail'].search_count([])
        
        # Try to retry (should fail and send notification)
        job.retry_job()
        
        # Count emails after
        mail_count_after = self.env['mail.mail'].search_count([])
        
        # Check if email was created
        self.assertGreater(mail_count_after, mail_count_before, 
                          'Email notification should be created for failed job')
        
        # Check email template exists
        template = self.env.ref('qz_tray_print.email_template_print_job_failure', raise_if_not_found=False)
        self.assertTrue(template, 'Email template should exist')
        self.assertEqual(template.model_id.model, 'qz.print.job', 
                        'Email template should be for qz.print.job model')
        
        _logger.info('✓ Email notification system works correctly')

    def test_12_offline_printer_queuing(self):
        """Verify jobs are queued for offline printers"""
        _logger.info('Testing offline printer queuing...')
        
        # Create an offline printer
        offline_printer = self.env['qz.printer'].create({
            'name': 'Offline Test Printer',
            'printer_type': 'receipt',
            'system_name': 'OFFLINE_PRINTER',
            'active': False,  # Offline
            'supports_html': True,
        })
        
        # Create and submit a job for offline printer
        job = self.env['qz.print.job'].create({
            'document_type': 'test_offline',
            'printer_id': offline_printer.id,
            'data_format': 'html',
            'data': b'<html><body>Offline Test</body></html>',
        })
        
        job_id = job.submit_job()
        
        self.assertEqual(job.state, 'queued', 'Job for offline printer should be queued')
        self.assertIn('offline', job.error_message.lower(), 
                     'Error message should mention printer is offline')
        
        _logger.info('✓ Offline printer queuing works correctly')

    def test_13_batch_label_printing(self):
        """Verify batch label printing functionality"""
        _logger.info('Testing batch label printing...')
        
        # Create a label printer
        label_printer = self.env['qz.printer'].create({
            'name': 'Test Label Printer',
            'printer_type': 'label',
            'system_name': 'LABEL_PRINTER',
            'active': True,
            'supports_zpl': True,
        })
        
        # Create multiple label jobs
        label_jobs = self.env['qz.print.job']
        for i in range(3):
            job = self.env['qz.print.job'].create({
                'document_type': 'label',
                'printer_id': label_printer.id,
                'data_format': 'zpl',
                'data': f'^XA^FO50,50^ADN,36,20^FDLabel {i}^FS^XZ'.encode(),
                'state': 'queued',
            })
            label_jobs |= job
        
        # Batch the jobs
        batch_job = self.env['qz.print.job'].batch_label_jobs(label_jobs)
        
        self.assertTrue(batch_job, 'Batch job should be created')
        self.assertEqual(batch_job.document_type, 'label_batch', 
                        'Batch job should have label_batch document type')
        
        # Check that individual jobs were cancelled
        for job in label_jobs:
            self.assertEqual(job.state, 'cancelled', 
                           'Individual label jobs should be cancelled after batching')
        
        _logger.info('✓ Batch label printing works correctly')

    def test_14_queue_processing(self):
        """Verify queue processing functionality"""
        _logger.info('Testing queue processing...')
        
        # Create multiple queued jobs
        for i in range(3):
            self.env['qz.print.job'].create({
                'document_type': f'test_queue_{i}',
                'printer_id': self.test_printer.id,
                'data_format': 'html',
                'data': f'<html><body>Queue Test {i}</body></html>'.encode(),
                'state': 'queued',
                'priority': i,  # Different priorities
            })
        
        # Process queued jobs
        result = self.env['qz.print.job'].process_queued_jobs()
        
        self.assertIn('processed', result, 'Result should contain processed count')
        self.assertIn('failed', result, 'Result should contain failed count')
        self.assertGreater(result['processed'], 0, 'Some jobs should be processed')
        
        _logger.info('✓ Queue processing works correctly')

    def test_15_printer_configuration_persistence(self):
        """Verify printer configuration is properly stored and retrieved"""
        _logger.info('Testing printer configuration persistence...')
        
        # Create a printer with specific configuration
        printer = self.env['qz.printer'].create({
            'name': 'Config Test Printer',
            'printer_type': 'document',
            'system_name': 'CONFIG_PRINTER',
            'paper_size': 'A4',
            'orientation': 'landscape',
            'print_quality': 'high',
            'is_default': True,
            'priority': 15,
            'active': True,
            'supports_pdf': True,
            'supports_html': True,
        })
        
        # Retrieve the printer
        retrieved_printer = self.env['qz.printer'].browse(printer.id)
        
        # Verify all configuration is persisted
        self.assertEqual(retrieved_printer.name, 'Config Test Printer')
        self.assertEqual(retrieved_printer.printer_type, 'document')
        self.assertEqual(retrieved_printer.paper_size, 'A4')
        self.assertEqual(retrieved_printer.orientation, 'landscape')
        self.assertEqual(retrieved_printer.print_quality, 'high')
        self.assertTrue(retrieved_printer.is_default)
        self.assertEqual(retrieved_printer.priority, 15)
        self.assertTrue(retrieved_printer.active)
        
        _logger.info('✓ Printer configuration persistence works correctly')

    def test_16_security_groups_exist(self):
        """Verify all security groups are properly defined"""
        _logger.info('Testing security groups...')
        
        # Check Print User group
        user_group = self.env.ref('qz_tray_print.group_qz_print_user', raise_if_not_found=False)
        self.assertTrue(user_group, 'Print User group should exist')
        
        # Check Print Manager group
        manager_group = self.env.ref('qz_tray_print.group_qz_print_manager', raise_if_not_found=False)
        self.assertTrue(manager_group, 'Print Manager group should exist')
        self.assertIn(user_group, manager_group.implied_ids, 
                     'Print Manager should imply Print User')
        
        # Check Print Administrator group
        admin_group = self.env.ref('qz_tray_print.group_qz_print_admin', raise_if_not_found=False)
        self.assertTrue(admin_group, 'Print Administrator group should exist')
        self.assertIn(manager_group, admin_group.implied_ids, 
                     'Print Administrator should imply Print Manager')
        
        _logger.info('✓ All security groups exist and are properly configured')

    def test_17_comprehensive_workflow(self):
        """Verify complete print workflow from submission to completion"""
        _logger.info('Testing comprehensive print workflow...')
        
        # 1. Create a print job
        job = self.env['qz.print.job'].create({
            'document_type': 'workflow_test',
            'printer_id': self.test_printer.id,
            'data_format': 'html',
            'data': b'<html><body>Workflow Test</body></html>',
            'copies': 2,
            'priority': 10,
        })
        
        self.assertEqual(job.state, 'draft', 'New job should be in draft state')
        
        # 2. Submit the job
        job.submit_job()
        self.assertEqual(job.state, 'queued', 'Submitted job should be queued')
        self.assertTrue(job.submitted_date, 'Job should have submitted_date')
        
        # 3. Process the job
        job.process_job()
        self.assertEqual(job.state, 'printing', 'Processed job should be in printing state')
        
        # 4. Mark as completed (simulating frontend confirmation)
        job.mark_completed()
        self.assertEqual(job.state, 'completed', 'Job should be completed')
        self.assertTrue(job.completed_date, 'Job should have completed_date')
        
        _logger.info('✓ Comprehensive print workflow works correctly')


def run_checkpoint_verification():
    """
    Convenience function to run all checkpoint verification tests
    """
    import sys
    from odoo.tests.common import run_unit_tests
    
    _logger.info('='*80)
    _logger.info('STARTING CHECKPOINT VERIFICATION TESTS')
    _logger.info('='*80)
    
    # Run the tests
    result = run_unit_tests('qz_tray_print', TestCheckpointVerification)
    
    _logger.info('='*80)
    _logger.info('CHECKPOINT VERIFICATION COMPLETE')
    _logger.info('='*80)
    
    return result


if __name__ == '__main__':
    run_checkpoint_verification()
