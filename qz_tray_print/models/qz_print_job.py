# -*- coding: utf-8 -*-
import logging
import json
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class QZPrintJob(models.Model):
    _name = 'qz.print.job'
    _description = 'QZ Tray Print Job'
    _order = 'submitted_date desc, priority desc, id desc'
    _rec_name = 'name'

    # Job identifier
    name = fields.Char(
        string='Job Name',
        default=lambda self: self._get_default_name(),
        readonly=True,
        copy=False,
        help='Unique identifier for this print job'
    )
    
    # Document information
    document_type = fields.Char(
        string='Document Type',
        required=True,
        help='Type of document being printed (e.g., receipt, label, invoice)'
    )
    
    # Printer assignment
    printer_id = fields.Many2one(
        comodel_name='qz.printer',
        string='Printer',
        required=True,
        ondelete='restrict',
        help='Target printer for this job'
    )
    
    # User tracking
    user_id = fields.Many2one(
        comodel_name='res.users',
        string='User',
        required=True,
        default=lambda self: self.env.user,
        ondelete='restrict',
        help='User who submitted the print job'
    )
    
    # Job state machine
    state = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('queued', 'Queued'),
            ('printing', 'Printing'),
            ('completed', 'Completed'),
            ('failed', 'Failed'),
            ('cancelled', 'Cancelled')
        ],
        string='Status',
        required=True,
        default='draft',
        tracking=True,
        help='Current status of the print job'
    )
    
    # Print data storage
    data = fields.Binary(
        string='Print Data',
        attachment=True,
        help='Binary print data to be sent to printer'
    )
    
    data_format = fields.Selection(
        selection=[
            ('pdf', 'PDF'),
            ('html', 'HTML'),
            ('escpos', 'ESC/POS'),
            ('zpl', 'ZPL')
        ],
        string='Data Format',
        required=True,
        help='Format of the print data'
    )
    
    # Template information
    template_id = fields.Many2one(
        comodel_name='ir.ui.view',
        string='QWeb Template',
        ondelete='set null',
        help='QWeb template used to generate print data'
    )
    
    template_data = fields.Text(
        string='Template Data',
        help='JSON data passed to template for rendering'
    )
    
    # Print options
    copies = fields.Integer(
        string='Number of Copies',
        default=1,
        required=True,
        help='Number of copies to print'
    )
    
    priority = fields.Integer(
        string='Priority',
        default=5,
        required=True,
        help='Job priority (higher = more important)'
    )
    
    # Error handling
    error_message = fields.Text(
        string='Error Message',
        readonly=True,
        help='Error details if job failed'
    )
    
    retry_count = fields.Integer(
        string='Retry Count',
        default=0,
        readonly=True,
        help='Number of times this job has been retried'
    )
    
    # Timestamps
    submitted_date = fields.Datetime(
        string='Submitted Date',
        readonly=True,
        help='When the job was submitted'
    )
    
    completed_date = fields.Datetime(
        string='Completed Date',
        readonly=True,
        help='When the job was completed or failed'
    )
    
    # Parent record tracking
    parent_model = fields.Char(
        string='Source Model',
        help='Model name of the record that initiated this print job'
    )
    
    parent_id = fields.Integer(
        string='Source Record ID',
        help='ID of the record that initiated this print job'
    )
    
    # Audit fields
    create_date = fields.Datetime(string='Created On', readonly=True)
    write_date = fields.Datetime(string='Last Updated', readonly=True)
    create_uid = fields.Many2one('res.users', string='Created By', readonly=True)
    write_uid = fields.Many2one('res.users', string='Last Updated By', readonly=True)

    @api.model
    def _get_default_name(self):
        """Generate default job name using sequence"""
        sequence = self.env['ir.sequence'].next_by_code('qz.print.job') or 'New'
        return f'PrintJob-{sequence}'

    @api.model_create_multi
    def create(self, vals_list):
        """Override create to enhance name with document type and printer"""
        records = super().create(vals_list)
        for record in records:
            if record.name and record.name.startswith('PrintJob-'):
                # Enhance the name with document type and printer
                printer_name = record.printer_id.name if record.printer_id else 'Unknown'
                doc_type = record.document_type or 'Document'
                sequence_part = record.name.split('-')[1]
                record.name = f'{doc_type}-{printer_name}-{sequence_part}'
        return records

    @api.constrains('copies')
    def _check_copies(self):
        """Validate number of copies"""
        for record in self:
            if record.copies < 1:
                raise ValidationError(_('Number of copies must be at least 1'))

    @api.constrains('priority')
    def _check_priority(self):
        """Validate priority value"""
        for record in self:
            if record.priority < 0:
                raise ValidationError(_('Priority cannot be negative'))

    @api.constrains('retry_count')
    def _check_retry_count(self):
        """Validate retry count"""
        for record in self:
            if record.retry_count < 0:
                raise ValidationError(_('Retry count cannot be negative'))


    def submit_job(self):
        """
        Submit job for printing
        
        Validates job data, sets initial state, and timestamps.
        Automatically queues jobs for offline printers.
        
        Returns: Job ID
        """
        self.ensure_one()
        
        # Validate job data
        if not self.data and not self.template_id:
            raise ValidationError(_('Print job must have either data or a template'))
        
        if not self.printer_id:
            raise ValidationError(_('Print job must have a printer assigned'))
        
        # Check if printer is offline (inactive)
        if not self.printer_id.active:
            # Queue the job for offline printer
            self.write({
                'submitted_date': fields.Datetime.now(),
                'state': 'queued',
                'error_message': _('Printer %s is offline. Job queued for later processing.') % self.printer_id.name
            })
            
            _logger.info(
                f'Print job {self.name} queued for offline printer {self.printer_id.name}'
            )
            
            # Return job ID with offline status
            return self.id
        
        # Set submitted timestamp for active printer
        self.write({
            'submitted_date': fields.Datetime.now(),
            'state': 'queued'
        })
        
        _logger.info(
            f'Print job {self.name} submitted by user {self.user_id.name} '
            f'to printer {self.printer_id.name}'
        )
        
        return self.id

    def process_job(self):
        """
        Process the print job
        
        Handles different data formats and sends to QZ Tray
        Implements error handling and state transitions
        """
        self.ensure_one()
        
        # Check if job is in correct state
        if self.state not in ['queued', 'failed']:
            _logger.warning(f'Cannot process job {self.name} in state {self.state}')
            return False
        
        try:
            # Update state to printing
            self.write({'state': 'printing'})
            
            # Validate printer is active
            if not self.printer_id.active:
                raise ValidationError(
                    _('Printer %s is not active') % self.printer_id.name
                )
            
            # Check if printer supports the data format
            format_supported = False
            if self.data_format == 'pdf' and self.printer_id.supports_pdf:
                format_supported = True
            elif self.data_format == 'html' and self.printer_id.supports_html:
                format_supported = True
            elif self.data_format == 'escpos' and self.printer_id.supports_escpos:
                format_supported = True
            elif self.data_format == 'zpl' and self.printer_id.supports_zpl:
                format_supported = True
            
            if not format_supported:
                raise ValidationError(
                    _('Printer %s does not support format %s') % 
                    (self.printer_id.name, self.data_format)
                )
            
            # Actual printing would be handled by JavaScript/QZ Tray
            # This method prepares the job and validates it
            # The frontend will poll for jobs in 'printing' state and send them to QZ Tray
            
            _logger.info(
                f'Print job {self.name} ready for processing '
                f'(format: {self.data_format}, copies: {self.copies})'
            )
            
            # Job will remain in 'printing' state until frontend confirms completion
            # or reports an error
            return True
            
        except Exception as e:
            error_msg = str(e)
            _logger.error(f'Error processing print job {self.name}: {error_msg}')
            
            # Determine if error is transient or permanent
            is_transient = self._is_transient_error(error_msg)
            
            if is_transient:
                # Mark for retry
                self.write({
                    'state': 'failed',
                    'error_message': error_msg
                })
            else:
                # Permanent error
                self.write({
                    'state': 'failed',
                    'error_message': error_msg,
                    'completed_date': fields.Datetime.now()
                })
            
            return False

    def _is_transient_error(self, error_message):
        """
        Determine if an error is transient (can be retried)
        
        Args:
            error_message: Error message string
            
        Returns:
            bool: True if error is transient, False if permanent
        """
        transient_keywords = [
            'timeout',
            'connection',
            'network',
            'offline',
            'unavailable',
            'busy'
        ]
        
        error_lower = error_message.lower()
        return any(keyword in error_lower for keyword in transient_keywords)

    def retry_job(self):
        """
        Retry a failed print job
        
        Checks retry count against configuration
        Implements exponential backoff for retries
        Handles transient vs permanent errors
        """
        self.ensure_one()
        
        # Check if job can be retried
        if self.state != 'failed':
            _logger.warning(f'Cannot retry job {self.name} in state {self.state}')
            return False
        
        # Get retry configuration
        IrConfigParameter = self.env['ir.config_parameter'].sudo()
        retry_enabled = IrConfigParameter.get_param('qz_tray.retry_enabled', default='True') == 'True'
        max_retries = int(IrConfigParameter.get_param('qz_tray.retry_count', default=3))
        retry_delay = int(IrConfigParameter.get_param('qz_tray.retry_delay', default=5))
        
        if not retry_enabled:
            _logger.info(f'Retry disabled for job {self.name}')
            return False
        
        # Check if max retries exceeded
        if self.retry_count >= max_retries:
            _logger.warning(
                f'Job {self.name} has exceeded maximum retry count ({max_retries})'
            )
            self.write({
                'completed_date': fields.Datetime.now(),
                'error_message': self.error_message + '\n' + 
                                _('Maximum retry count exceeded')
            })
            # Notify administrator
            self._notify_admin_failure()
            return False
        
        # Check if error is transient
        if not self._is_transient_error(self.error_message or ''):
            _logger.info(f'Job {self.name} has permanent error, cannot retry')
            self.write({'completed_date': fields.Datetime.now()})
            return False
        
        # Increment retry count
        new_retry_count = self.retry_count + 1
        
        # Calculate exponential backoff delay (optional, for future use)
        backoff_delay = retry_delay * (2 ** (new_retry_count - 1))
        
        _logger.info(
            f'Retrying job {self.name} (attempt {new_retry_count}/{max_retries})'
        )
        
        # Reset job state for retry
        self.write({
            'state': 'queued',
            'retry_count': new_retry_count,
            'error_message': self.error_message + '\n' + 
                           _('Retry attempt %d at %s') % (new_retry_count, fields.Datetime.now())
        })
        
        # Process the job
        return self.process_job()

    def _notify_admin_failure(self):
        """
        Notify administrator of job failure after max retries
        
        Sends email notification using the configured email template
        to Print Administrator group members when a job fails after
        exhausting all retry attempts.
        """
        self.ensure_one()
        
        # Get email notification setting
        IrConfigParameter = self.env['ir.config_parameter'].sudo()
        email_enabled = IrConfigParameter.get_param(
            'qz_tray.email_notifications_enabled', 
            default='False'
        ) == 'True'
        
        if not email_enabled:
            _logger.debug(
                f'Email notifications disabled, skipping notification for job {self.name}'
            )
            return
        
        # Get Print Administrator group
        try:
            admin_group = self.env.ref('qz_tray_print.group_qz_print_admin')
        except ValueError:
            _logger.warning(
                'Print Administrator group not found, falling back to system administrators'
            )
            admin_group = self.env.ref('base.group_system', raise_if_not_found=False)
        
        if not admin_group:
            _logger.error('No administrator group found for notifications')
            return
        
        admin_users = admin_group.users
        if not admin_users:
            _logger.warning('No users in administrator group for notifications')
            return
        
        # Get email template
        try:
            template = self.env.ref('qz_tray_print.email_template_print_job_failure')
        except ValueError:
            _logger.error('Email template not found, sending basic notification')
            # Fallback to basic email
            self._send_basic_failure_email(admin_users)
            return
        
        # Send email to each administrator
        for admin in admin_users:
            if not admin.email:
                _logger.warning(f'Administrator {admin.name} has no email address')
                continue
            
            try:
                # Use the template to send email
                template.send_mail(
                    self.id,
                    force_send=True,
                    email_values={
                        'email_to': admin.email,
                        'recipient_ids': [(4, admin.partner_id.id)],
                    }
                )
                _logger.info(
                    f'Failure notification sent to {admin.name} ({admin.email}) '
                    f'for job {self.name}'
                )
            except Exception as e:
                _logger.error(
                    f'Failed to send email notification to {admin.name}: {str(e)}'
                )
    
    def _send_basic_failure_email(self, admin_users):
        """
        Send basic failure email without template (fallback method)
        
        Args:
            admin_users: Recordset of users to notify
        """
        subject = _('Print Job Failed: %s') % self.name
        body = _(
            '<div style="font-family: Arial, sans-serif;">'
            '<h2 style="color: #dc3545;">Print Job Failed</h2>'
            '<p>Print job <strong>%s</strong> has failed after %d retry attempts.</p>'
            '<h3>Details:</h3>'
            '<ul>'
            '<li><strong>Document Type:</strong> %s</li>'
            '<li><strong>Printer:</strong> %s</li>'
            '<li><strong>User:</strong> %s</li>'
            '<li><strong>Submitted:</strong> %s</li>'
            '<li><strong>Error:</strong> %s</li>'
            '</ul>'
            '<p>Please check the printer status and configuration.</p>'
            '</div>'
        ) % (
            self.name,
            self.retry_count,
            self.document_type,
            self.printer_id.name,
            self.user_id.name,
            self.submitted_date,
            self.error_message or 'No error message available'
        )
        
        # Send notification to admins
        for admin in admin_users:
            if not admin.email:
                continue
            
            try:
                self.env['mail.mail'].create({
                    'subject': subject,
                    'body_html': body,
                    'email_to': admin.email,
                    'auto_delete': True,
                }).send()
                
                _logger.info(
                    f'Basic failure notification sent to {admin.name} for job {self.name}'
                )
            except Exception as e:
                _logger.error(
                    f'Failed to send basic email to {admin.name}: {str(e)}'
                )

    def cancel_job(self):
        """
        Cancel a pending print job
        """
        self.ensure_one()
        
        if self.state in ['completed', 'cancelled']:
            _logger.warning(f'Cannot cancel job {self.name} in state {self.state}')
            return False
        
        self.write({
            'state': 'cancelled',
            'completed_date': fields.Datetime.now()
        })
        
        _logger.info(f'Print job {self.name} cancelled by user {self.env.user.name}')
        return True

    def mark_completed(self):
        """
        Mark job as completed (called by frontend after successful print)
        """
        self.ensure_one()
        
        self.write({
            'state': 'completed',
            'completed_date': fields.Datetime.now(),
            'error_message': False
        })
        
        _logger.info(f'Print job {self.name} completed successfully')
        return True

    def mark_failed(self, error_message):
        """
        Mark job as failed (called by frontend after print error)
        
        Args:
            error_message: Error message from QZ Tray or frontend
        """
        self.ensure_one()
        
        self.write({
            'state': 'failed',
            'error_message': error_message
        })
        
        _logger.error(f'Print job {self.name} failed: {error_message}')
        
        # Attempt automatic retry if configured
        if self._is_transient_error(error_message):
            self.retry_job()
        else:
            self.write({'completed_date': fields.Datetime.now()})
            self._notify_admin_failure()
        
        return True

    @api.model
    def batch_label_jobs(self, label_jobs):
        """
        Combine multiple label print jobs into a single batch job
        
        This method detects multiple label requests for the same printer
        and combines them into a single print job for efficiency.
        
        Args:
            label_jobs: Recordset of qz.print.job records for labels
            
        Returns:
            qz.print.job: The batch job record
        """
        if not label_jobs:
            raise ValidationError(_('No label jobs provided for batching'))
        
        if len(label_jobs) == 1:
            # No batching needed for single job
            return label_jobs
        
        # Validate all jobs are for the same printer
        printers = label_jobs.mapped('printer_id')
        if len(printers) > 1:
            raise ValidationError(
                _('Cannot batch labels for different printers: %s') % 
                ', '.join(printers.mapped('name'))
            )
        
        printer = printers[0]
        
        # Validate all jobs are label type
        non_label_jobs = label_jobs.filtered(
            lambda j: j.document_type not in ['label', 'barcode', 'product_label']
        )
        if non_label_jobs:
            _logger.warning(
                f'Skipping non-label jobs in batch: '
                f'{", ".join(non_label_jobs.mapped("name"))}'
            )
            label_jobs = label_jobs - non_label_jobs
        
        if not label_jobs:
            raise ValidationError(_('No valid label jobs to batch'))
        
        # Determine the format (all labels should use same format)
        formats = label_jobs.mapped('data_format')
        if len(set(formats)) > 1:
            _logger.warning(
                f'Multiple formats detected in batch: {formats}. '
                f'Using format of first job.'
            )
        
        batch_format = label_jobs[0].data_format
        
        # Combine label data
        combined_data = b''
        for job in label_jobs.sorted(key=lambda j: j.submitted_date):
            if job.data:
                combined_data += job.data
                # Add separator between labels if needed
                if batch_format == 'zpl':
                    # ZPL labels are typically self-contained
                    combined_data += b'\n'
                elif batch_format == 'escpos':
                    # ESC/POS may need cut command between labels
                    combined_data += b'\x1D\x56\x00'  # Cut paper command
        
        # Create batch job
        batch_job = self.create({
            'document_type': 'label_batch',
            'printer_id': printer.id,
            'user_id': label_jobs[0].user_id.id,
            'data': combined_data,
            'data_format': batch_format,
            'copies': 1,  # Batch already contains all copies
            'priority': max(label_jobs.mapped('priority')),
            'parent_model': 'qz.print.job',
            'parent_id': label_jobs[0].id,
        })
        
        # Cancel individual jobs (they're now part of batch)
        for job in label_jobs:
            job.write({
                'state': 'cancelled',
                'error_message': _('Combined into batch job %s') % batch_job.name,
                'completed_date': fields.Datetime.now()
            })
        
        _logger.info(
            f'Created batch job {batch_job.name} combining '
            f'{len(label_jobs)} label job(s) for printer {printer.name}'
        )
        
        return batch_job

    @api.model
    def process_queued_jobs(self):
        """
        Process queued print jobs in FIFO order per printer
        
        This method is designed to be called by a scheduled action (cron job).
        It processes jobs for active printers, respecting printer priority settings.
        
        Returns:
            dict: Summary of processed jobs
        """
        _logger.info('Starting queued print job processing')
        
        # Get all active printers ordered by priority (highest first)
        active_printers = self.env['qz.printer'].search([
            ('active', '=', True)
        ], order='priority desc, id')
        
        if not active_printers:
            _logger.warning('No active printers found for job processing')
            return {
                'processed': 0,
                'failed': 0,
                'message': 'No active printers available'
            }
        
        processed_count = 0
        failed_count = 0
        
        # Process jobs for each active printer
        for printer in active_printers:
            # Get queued jobs for this printer in FIFO order (oldest first)
            # Order by submitted_date (oldest first), then by priority (highest first)
            queued_jobs = self.search([
                ('printer_id', '=', printer.id),
                ('state', '=', 'queued')
            ], order='submitted_date asc, priority desc, id asc')
            
            if not queued_jobs:
                continue
            
            _logger.info(
                f'Processing {len(queued_jobs)} queued job(s) for printer {printer.name}'
            )
            
            # Check if printer is a label printer and if there are multiple label jobs
            # that can be batched together
            if printer.printer_type == 'label':
                label_jobs = queued_jobs.filtered(
                    lambda j: j.document_type in ['label', 'barcode', 'product_label']
                )
                
                # Batch labels if there are multiple label jobs
                if len(label_jobs) > 1:
                    try:
                        batch_job = self.batch_label_jobs(label_jobs)
                        # Add batch job to processing queue
                        queued_jobs = (queued_jobs - label_jobs) | batch_job
                        _logger.info(
                            f'Batched {len(label_jobs)} label jobs into {batch_job.name}'
                        )
                    except Exception as e:
                        _logger.error(f'Error batching label jobs: {str(e)}')
                        # Continue with individual processing if batching fails
            
            # Process each job
            for job in queued_jobs:
                try:
                    # Check if printer is still active before processing
                    if not job.printer_id.active:
                        _logger.warning(
                            f'Printer {job.printer_id.name} became inactive, '
                            f'skipping job {job.name}'
                        )
                        continue
                    
                    # Process the job
                    success = job.process_job()
                    
                    if success:
                        processed_count += 1
                        _logger.info(f'Successfully processed job {job.name}')
                    else:
                        failed_count += 1
                        _logger.warning(f'Failed to process job {job.name}')
                        
                except Exception as e:
                    failed_count += 1
                    error_msg = f'Error processing job {job.name}: {str(e)}'
                    _logger.error(error_msg)
                    
                    # Mark job as failed
                    job.write({
                        'state': 'failed',
                        'error_message': error_msg,
                        'completed_date': fields.Datetime.now()
                    })
        
        result_message = (
            f'Processed {processed_count} job(s), '
            f'{failed_count} failed for {len(active_printers)} active printer(s)'
        )
        
        _logger.info(f'Completed queued job processing: {result_message}')
        
        return {
            'processed': processed_count,
            'failed': failed_count,
            'printers': len(active_printers),
            'message': result_message
        }

