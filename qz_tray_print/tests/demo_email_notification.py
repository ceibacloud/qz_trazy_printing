#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Demo script to test email notification functionality

This script demonstrates how the email notification system works
when a print job fails after exhausting retry attempts.

Usage:
    Run this script from Odoo shell or as a standalone test
"""

import logging

_logger = logging.getLogger(__name__)


def demo_email_notification(env):
    """
    Demonstrate email notification for failed print job
    
    Args:
        env: Odoo environment
    """
    print("\n" + "="*70)
    print("QZ Tray Print Integration - Email Notification Demo")
    print("="*70 + "\n")
    
    # Step 1: Check if email notifications are enabled
    print("Step 1: Checking email notification configuration...")
    param_value = env['ir.config_parameter'].sudo().get_param(
        'qz_tray.email_notifications_enabled',
        default='False'
    )
    print(f"  Email notifications enabled: {param_value}")
    
    if param_value != 'True':
        print("\n  ⚠️  Email notifications are DISABLED")
        print("  To enable, set system parameter:")
        print("  Key: qz_tray.email_notifications_enabled")
        print("  Value: True")
        
        # Ask if we should enable for demo
        response = input("\n  Enable notifications for this demo? (y/n): ")
        if response.lower() == 'y':
            env['ir.config_parameter'].sudo().set_param(
                'qz_tray.email_notifications_enabled',
                'True'
            )
            print("  ✓ Email notifications enabled")
        else:
            print("  Demo will continue but no emails will be sent")
    else:
        print("  ✓ Email notifications are enabled")
    
    # Step 2: Check for administrators
    print("\nStep 2: Checking for Print Administrators...")
    try:
        admin_group = env.ref('qz_tray_print.group_qz_print_admin')
        admin_users = admin_group.users
        
        if admin_users:
            print(f"  Found {len(admin_users)} Print Administrator(s):")
            for admin in admin_users:
                email_status = "✓" if admin.email else "✗ (no email)"
                print(f"    - {admin.name} ({admin.login}) {email_status}")
        else:
            print("  ⚠️  No users in Print Administrator group")
            print("  Falling back to system administrators...")
            
            system_admin_group = env.ref('base.group_system')
            admin_users = system_admin_group.users
            print(f"  Found {len(admin_users)} System Administrator(s)")
    except Exception as e:
        print(f"  ✗ Error checking administrators: {str(e)}")
        return
    
    # Step 3: Check email template
    print("\nStep 3: Checking email template...")
    try:
        template = env.ref('qz_tray_print.email_template_print_job_failure')
        print(f"  ✓ Email template found: {template.name}")
        print(f"    Subject: {template.subject}")
        print(f"    Model: {template.model_id.model}")
    except Exception as e:
        print(f"  ✗ Email template not found: {str(e)}")
        return
    
    # Step 4: Create test printer
    print("\nStep 4: Creating test printer...")
    printer = env['qz.printer'].create({
        'name': 'Demo Test Printer',
        'printer_type': 'receipt',
        'system_name': 'DEMO_PRINTER',
        'active': True,
    })
    print(f"  ✓ Created printer: {printer.name} (ID: {printer.id})")
    
    # Step 5: Create test print job
    print("\nStep 5: Creating failed print job...")
    job = env['qz.print.job'].create({
        'document_type': 'demo_receipt',
        'printer_id': printer.id,
        'user_id': env.user.id,
        'data_format': 'pdf',
        'state': 'failed',
        'retry_count': 3,
        'error_message': (
            'Demo error: Printer connection timeout\n'
            'This is a simulated error for demonstration purposes.\n'
            'The printer appears to be offline or unreachable.'
        ),
        'submitted_date': env.cr.now(),
    })
    print(f"  ✓ Created print job: {job.name} (ID: {job.id})")
    print(f"    Document Type: {job.document_type}")
    print(f"    Printer: {job.printer_id.name}")
    print(f"    State: {job.state}")
    print(f"    Retry Count: {job.retry_count}")
    
    # Step 6: Trigger email notification
    print("\nStep 6: Triggering email notification...")
    try:
        # Count emails before
        mail_count_before = env['mail.mail'].search_count([])
        
        # Trigger notification
        job._notify_admin_failure()
        
        # Count emails after
        mail_count_after = env['mail.mail'].search_count([])
        emails_sent = mail_count_after - mail_count_before
        
        if emails_sent > 0:
            print(f"  ✓ Email notification triggered successfully")
            print(f"    Emails queued: {emails_sent}")
            
            # Show email details
            recent_emails = env['mail.mail'].search(
                [],
                order='id desc',
                limit=emails_sent
            )
            
            print("\n  Email Details:")
            for email in recent_emails:
                print(f"    - To: {email.email_to}")
                print(f"      Subject: {email.subject}")
                print(f"      State: {email.state}")
        else:
            print("  ℹ️  No emails were sent")
            print("     (Notifications may be disabled or no admins with email)")
    except Exception as e:
        print(f"  ✗ Error triggering notification: {str(e)}")
        import traceback
        traceback.print_exc()
    
    # Step 7: Cleanup
    print("\nStep 7: Cleanup...")
    response = input("  Delete demo printer and job? (y/n): ")
    if response.lower() == 'y':
        job.unlink()
        printer.unlink()
        print("  ✓ Demo data cleaned up")
    else:
        print("  ℹ️  Demo data preserved for inspection")
        print(f"     Printer ID: {printer.id}")
        print(f"     Job ID: {job.id}")
    
    print("\n" + "="*70)
    print("Demo Complete!")
    print("="*70 + "\n")


if __name__ == '__main__':
    print("This script should be run from Odoo shell:")
    print("  odoo-bin shell -c odoo.conf -d your_database")
    print("\nThen execute:")
    print("  from qz_tray_print.tests.demo_email_notification import demo_email_notification")
    print("  demo_email_notification(env)")
