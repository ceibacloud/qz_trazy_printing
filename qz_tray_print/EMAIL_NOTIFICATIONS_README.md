# Email Notifications for Failed Print Jobs

## Overview

The QZ Tray Print Integration module includes an automated email notification system that alerts administrators when print jobs fail after exhausting all retry attempts. This ensures that critical printing failures don't go unnoticed and can be addressed promptly.

## Features

- **Automated Alerts**: Automatically sends emails when print jobs fail after max retries
- **Professional Templates**: HTML email templates with detailed job information
- **Configurable**: Enable/disable notifications via system parameters
- **Targeted Recipients**: Sends to Print Administrator group members
- **Comprehensive Details**: Includes job name, document type, printer, user, error message, and troubleshooting steps
- **Direct Access**: Provides link to view job details in Odoo
- **Fallback Mechanisms**: Gracefully handles missing templates or admin groups

## Configuration

### Enabling Email Notifications

Email notifications are **disabled by default** for privacy and to prevent unwanted emails during initial setup.

To enable notifications:

1. Navigate to **Settings > Technical > Parameters > System Parameters**
2. Find or create the parameter: `qz_tray.email_notifications_enabled`
3. Set the value to: `True`
4. Save

Alternatively, use the Odoo shell:
```python
env['ir.config_parameter'].sudo().set_param('qz_tray.email_notifications_enabled', 'True')
```

### Configuring Recipients

By default, emails are sent to users in the **Print Administrator** group.

To add users to this group:

1. Navigate to **Settings > Users & Companies > Groups**
2. Search for: `Print Administrator`
3. Open the group
4. Add users to the **Users** tab
5. Ensure users have valid email addresses

**Important**: Users must have email addresses configured in their user profile to receive notifications.

### Customizing the Email Template

The email template can be customized to match your organization's branding:

1. Navigate to **Settings > Technical > Email > Templates**
2. Search for: `Print Job Failure Notification`
3. Edit the template:
   - Modify the subject line
   - Update the HTML body
   - Change colors and styling
   - Add company logo
4. Save changes

## Email Content

The notification email includes:

### Header Section
- Clear indication that a print job has failed
- Visual alert styling (red header)

### Job Details
- Job name and ID
- Document type
- Printer name
- User who submitted the job
- Submission date and time
- Number of retry attempts
- Current status

### Error Information
- Complete error message
- Formatted for easy reading

### Recommended Actions
- Check printer status
- Verify printer configuration
- Review error message
- Check QZ Tray status
- Instructions for manual resubmission

### Direct Access
- Link to view full job details in Odoo

## System Parameters

The following system parameters control email notifications:

| Parameter | Default | Description |
|-----------|---------|-------------|
| `qz_tray.email_notifications_enabled` | `False` | Enable/disable email notifications |
| `qz_tray.retry_enabled` | `True` | Enable automatic retry for failed jobs |
| `qz_tray.retry_count` | `3` | Maximum number of retry attempts |
| `qz_tray.retry_delay` | `5` | Delay between retries (seconds) |

## Testing

### Manual Testing

1. **Enable notifications** (see Configuration section above)

2. **Create a test scenario**:
   ```python
   # In Odoo shell
   printer = env['qz.printer'].create({
       'name': 'Test Printer',
       'printer_type': 'receipt',
       'system_name': 'TEST',
       'active': False,  # Offline printer
   })
   
   job = env['qz.print.job'].create({
       'document_type': 'test_receipt',
       'printer_id': printer.id,
       'user_id': env.user.id,
       'data_format': 'pdf',
       'state': 'failed',
       'retry_count': 3,
       'error_message': 'Test error message',
   })
   
   # Trigger notification
   job._notify_admin_failure()
   ```

3. **Check email queue**:
   ```python
   # View queued emails
   emails = env['mail.mail'].search([], order='id desc', limit=5)
   for email in emails:
       print(f"To: {email.email_to}, Subject: {email.subject}")
   ```

### Automated Testing

Run the unit tests:
```bash
odoo-bin -c odoo.conf -d test_db --test-tags=qz_tray_print -i qz_tray_print --stop-after-init
```

### Demo Script

Use the included demo script for interactive testing:
```bash
odoo-bin shell -c odoo.conf -d your_database
```

Then in the shell:
```python
from qz_tray_print.tests.demo_email_notification import demo_email_notification
demo_email_notification(env)
```

## Troubleshooting

### No Emails Being Sent

**Check 1: Notifications Enabled**
```python
env['ir.config_parameter'].sudo().get_param('qz_tray.email_notifications_enabled')
# Should return 'True'
```

**Check 2: Admin Users Exist**
```python
admin_group = env.ref('qz_tray_print.group_qz_print_admin')
print(f"Admins: {len(admin_group.users)}")
for admin in admin_group.users:
    print(f"  {admin.name}: {admin.email}")
```

**Check 3: Email Template Exists**
```python
template = env.ref('qz_tray_print.email_template_print_job_failure')
print(f"Template: {template.name}")
```

**Check 4: Outgoing Mail Server Configured**
```python
mail_server = env['ir.mail_server'].search([], limit=1)
if mail_server:
    print(f"Mail server: {mail_server.name}")
else:
    print("No mail server configured!")
```

### Emails Not Being Delivered

1. **Check Odoo mail server configuration**:
   - Navigate to **Settings > Technical > Outgoing Mail Servers**
   - Verify SMTP settings
   - Test connection

2. **Check email queue**:
   - Navigate to **Settings > Technical > Email > Emails**
   - Look for failed emails
   - Check error messages

3. **Check logs**:
   ```bash
   grep "Failure notification" odoo.log
   ```

### Template Not Found Error

If you see "Email template not found" in logs:

1. **Verify module installation**:
   ```python
   env['ir.module.module'].search([('name', '=', 'qz_tray_print')]).state
   # Should return 'installed'
   ```

2. **Update module**:
   - Navigate to **Apps**
   - Search for "QZ Tray Print Integration"
   - Click **Upgrade**

3. **Manually load template**:
   ```bash
   odoo-bin -c odoo.conf -d your_database -u qz_tray_print --stop-after-init
   ```

## Security & Privacy

### Data Protection
- Email notifications are **disabled by default**
- Only administrators receive failure notifications
- Emails are auto-deleted after sending (configurable)
- No sensitive print data is included in emails

### Access Control
- Only users in Print Administrator group receive emails
- Fallback to system administrators if Print Admin group unavailable
- Email addresses are validated before sending

### Compliance
- Emails contain only job metadata (no actual print content)
- Complies with data minimization principles
- Audit trail maintained in Odoo logs

## Best Practices

1. **Enable Gradually**: Start with a small group of administrators
2. **Monitor Volume**: Watch for email flooding if many jobs fail
3. **Customize Template**: Adapt email content to your organization's needs
4. **Regular Review**: Periodically review failed jobs and notification effectiveness
5. **Test Thoroughly**: Test notifications in staging before production
6. **Document Procedures**: Create runbooks for handling failure notifications

## Integration

### Automatic Triggers

Emails are automatically sent when:
- `retry_job()` determines max retries exceeded
- `mark_failed()` is called with a permanent error
- Job state changes to 'failed' with exhausted retries

### Manual Triggers

Administrators can manually trigger notifications:
```python
job = env['qz.print.job'].browse(job_id)
job._notify_admin_failure()
```

### Custom Integration

Extend the notification system:
```python
class QZPrintJob(models.Model):
    _inherit = 'qz.print.job'
    
    def _notify_admin_failure(self):
        # Call parent method
        super()._notify_admin_failure()
        
        # Add custom notification logic
        # e.g., send to Slack, create ticket, etc.
```

## Support

For issues or questions:
1. Check the logs: `grep "qz.print.job" odoo.log`
2. Review the test suite: `qz_tray_print/tests/test_email_notifications.py`
3. Run the demo script: `qz_tray_print/tests/demo_email_notification.py`
4. Consult the implementation summary: `qz_tray_print/tests/TASK_16_EMAIL_NOTIFICATIONS_SUMMARY.md`

## Related Documentation

- [QZ Tray Print Integration README](README.md)
- [Task 16 Implementation Summary](tests/TASK_16_EMAIL_NOTIFICATIONS_SUMMARY.md)
- [Requirements Document](.kiro/specs/qz-tray-print-integration/requirements.md)
- [Design Document](.kiro/specs/qz-tray-print-integration/design.md)

## Version History

- **v1.0.0** (2024): Initial implementation
  - Email template creation
  - System parameter configuration
  - Integration with retry mechanism
  - Unit tests and demo script
