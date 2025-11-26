# -*- coding: utf-8 -*-

from odoo import http
from odoo.http import request


class QZTrayController(http.Controller):
    
    @http.route('/qz_tray/get_certificates', type='json', auth='user')
    def get_certificates(self):
        """Get QZ Tray certificates for authentication"""
        try:
            IrConfigParameter = request.env['ir.config_parameter'].sudo()
            
            certificate = IrConfigParameter.get_param('qz_tray.certificate', default='')
            private_key = IrConfigParameter.get_param('qz_tray.private_key', default='')
            
            return {
                'certificate': certificate,
                'private_key': private_key,
            }
        except Exception as e:
            return {
                'error': str(e),
                'certificate': '',
                'private_key': '',
            }
    
    @http.route('/qz_tray/print', type='json', auth='user')
    def submit_print_job(self, document_type, data, printer_id=None, options=None):
        """Submit a new print job"""
        try:
            if options is None:
                options = {}
            
            # Get the print service
            print_service = request.env['qz.print.service']
            
            # Create print job
            job = print_service.print_document(
                template=document_type,
                data=data,
                printer=printer_id,
                **options
            )
            
            return {
                'success': True,
                'job_id': job.id,
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
            }
    
    @http.route('/qz_tray/print_raw', type='json', auth='user')
    def submit_raw_print_job(self, data, format, printer_id=None, options=None):
        """Submit a raw print job"""
        try:
            if options is None:
                options = {}
            
            # Get the print service
            print_service = request.env['qz.print.service']
            
            # Create print job
            job = print_service.print_raw(
                data=data,
                format=format,
                printer=printer_id,
                **options
            )
            
            return {
                'success': True,
                'job_id': job.id,
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
            }
    
    @http.route('/qz_tray/job/<int:job_id>/status', type='json', auth='user')
    def get_job_status(self, job_id):
        """Get status of a print job"""
        try:
            job = request.env['qz.print.job'].browse(job_id)
            
            if not job.exists():
                return {
                    'error': 'Job not found',
                }
            
            # Check if printer is offline
            printer_offline = False
            if job.printer_id:
                printer_offline = not job.printer_id.active
            
            return {
                'success': True,
                'job_id': job.id,
                'state': job.state,
                'error_message': job.error_message or '',
                'printer_offline': printer_offline,
                'submitted_date': job.submitted_date.isoformat() if job.submitted_date else None,
                'completed_date': job.completed_date.isoformat() if job.completed_date else None,
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
            }
    
    @http.route('/qz_tray/preview', type='json', auth='user')
    def generate_preview(self, document_type, data):
        """Generate document preview"""
        try:
            # Get the print service
            print_service = request.env['qz.print.service']
            
            # Generate preview
            preview = print_service.preview_document(
                template=document_type,
                data=data
            )
            
            return {
                'success': True,
                'preview': preview,
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
            }
    
    @http.route('/qz_tray/job/cancel', type='json', auth='user')
    def cancel_job(self, job_id):
        """Cancel a print job"""
        try:
            job = request.env['qz.print.job'].browse(job_id)
            
            if not job.exists():
                return {
                    'success': False,
                    'error': 'Job not found',
                }
            
            job.cancel_job()
            
            return {
                'success': True,
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
            }
    
    @http.route('/qz_tray/job/retry', type='json', auth='user')
    def retry_job(self, job_id):
        """Retry a failed print job"""
        try:
            job = request.env['qz.print.job'].browse(job_id)
            
            if not job.exists():
                return {
                    'success': False,
                    'error': 'Job not found',
                }
            
            job.retry_job()
            
            return {
                'success': True,
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
            }
    
    @http.route('/qz_tray/printers', type='json', auth='user')
    def get_printers(self):
        """Get list of configured printers"""
        try:
            printers = request.env['qz.printer'].search([('active', '=', True)])
            
            printer_list = []
            for printer in printers:
                printer_list.append({
                    'id': printer.id,
                    'name': printer.name,
                    'system_name': printer.system_name,
                    'printer_type': printer.printer_type,
                    'paper_size': printer.paper_size,
                    'orientation': printer.orientation,
                    'print_quality': printer.print_quality,
                    'location_id': printer.location_id.id if printer.location_id else False,
                    'location_name': printer.location_id.name if printer.location_id else '',
                    'department': printer.department or '',
                    'is_default': printer.is_default,
                    'priority': printer.priority,
                    'supports_pdf': printer.supports_pdf,
                    'supports_html': printer.supports_html,
                    'supports_escpos': printer.supports_escpos,
                    'supports_zpl': printer.supports_zpl,
                })
            
            return {
                'success': True,
                'printers': printer_list,
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
            }
    
    @http.route('/qz_tray/printer/<int:printer_id>/test', type='json', auth='user')
    def test_printer_connection(self, printer_id):
        """Test printer connection"""
        try:
            printer = request.env['qz.printer'].browse(printer_id)
            
            if not printer.exists():
                return {
                    'success': False,
                    'error': 'Printer not found',
                }
            
            # Return printer information for frontend to test
            # Actual test will be performed by JavaScript/QZ Tray
            return {
                'success': True,
                'printer_id': printer.id,
                'printer_name': printer.system_name or printer.name,
                'printer_type': printer.printer_type,
                'active': printer.active,
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
            }
    
    @http.route('/qz_tray/printer/<int:printer_id>', type='json', auth='user')
    def get_printer_config(self, printer_id):
        """Get printer configuration"""
        try:
            printer = request.env['qz.printer'].browse(printer_id)
            
            if not printer.exists():
                return {
                    'success': False,
                    'error': 'Printer not found',
                }
            
            return {
                'success': True,
                'printer': {
                    'id': printer.id,
                    'name': printer.name,
                    'system_name': printer.system_name,
                    'printer_type': printer.printer_type,
                    'paper_size': printer.paper_size,
                    'orientation': printer.orientation,
                    'print_quality': printer.print_quality,
                    'location_id': printer.location_id.id if printer.location_id else False,
                    'location_name': printer.location_id.name if printer.location_id else '',
                    'department': printer.department or '',
                    'is_default': printer.is_default,
                    'priority': printer.priority,
                    'active': printer.active,
                    'supports_pdf': printer.supports_pdf,
                    'supports_html': printer.supports_html,
                    'supports_escpos': printer.supports_escpos,
                    'supports_zpl': printer.supports_zpl,
                }
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
            }
    
    @http.route('/qz_tray/printer/<int:printer_id>/update', type='json', auth='user')
    def update_printer_settings(self, printer_id, **settings):
        """Update printer settings"""
        try:
            printer = request.env['qz.printer'].browse(printer_id)
            
            if not printer.exists():
                return {
                    'success': False,
                    'error': 'Printer not found',
                }
            
            # Filter allowed settings to update
            allowed_fields = [
                'paper_size', 'orientation', 'print_quality',
                'location_id', 'department', 'is_default',
                'priority', 'active', 'supports_pdf',
                'supports_html', 'supports_escpos', 'supports_zpl'
            ]
            
            update_vals = {}
            for field in allowed_fields:
                if field in settings:
                    update_vals[field] = settings[field]
            
            if update_vals:
                printer.write(update_vals)
            
            return {
                'success': True,
                'printer_id': printer.id,
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
            }
    
    @http.route('/qz_tray/job/<int:job_id>/resubmit', type='json', auth='user')
    def resubmit_job(self, job_id):
        """Resubmit a failed print job"""
        try:
            job = request.env['qz.print.job'].browse(job_id)
            
            if not job.exists():
                return {
                    'success': False,
                    'error': 'Job not found',
                }
            
            # Create a new job with the same parameters
            new_job = request.env['qz.print.job'].create({
                'document_type': job.document_type,
                'printer_id': job.printer_id.id,
                'user_id': request.env.user.id,
                'data': job.data,
                'data_format': job.data_format,
                'template_id': job.template_id.id if job.template_id else False,
                'template_data': job.template_data,
                'copies': job.copies,
                'priority': job.priority,
                'parent_model': job.parent_model,
                'parent_id': job.parent_id,
            })
            
            # Submit the new job
            new_job.submit_job()
            
            return {
                'success': True,
                'job_id': new_job.id,
                'original_job_id': job.id,
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
            }
    
    @http.route('/qz_tray/printer/<int:printer_id>/pause', type='json', auth='user')
    def pause_printer(self, printer_id):
        """Pause a printer (stop processing jobs)"""
        try:
            printer = request.env['qz.printer'].browse(printer_id)
            
            if not printer.exists():
                return {
                    'success': False,
                    'error': 'Printer not found',
                }
            
            # Set printer to inactive to pause it
            printer.write({'active': False})
            
            return {
                'success': True,
                'printer_id': printer.id,
                'status': 'paused',
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
            }
    
    @http.route('/qz_tray/printer/<int:printer_id>/resume', type='json', auth='user')
    def resume_printer(self, printer_id):
        """Resume a paused printer"""
        try:
            printer = request.env['qz.printer'].browse(printer_id)
            
            if not printer.exists():
                return {
                    'success': False,
                    'error': 'Printer not found',
                }
            
            # Set printer to active to resume it
            printer.write({'active': True})
            
            # Get queued jobs for this printer
            queued_jobs = request.env['qz.print.job'].search([
                ('printer_id', '=', printer.id),
                ('state', '=', 'queued')
            ], order='submitted_date asc, priority desc')
            
            return {
                'success': True,
                'printer_id': printer.id,
                'status': 'active',
                'queued_jobs_count': len(queued_jobs),
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
            }
    
    @http.route('/qz_tray/printers/sync', type='json', auth='user')
    def sync_printers(self, printers):
        """Sync discovered printers with backend database"""
        try:
            if not printers or not isinstance(printers, list):
                return {
                    'success': False,
                    'error': 'Invalid printers data',
                }
            
            Printer = request.env['qz.printer']
            new_count = 0
            updated_count = 0
            
            for printer_name in printers:
                # Check if printer already exists
                existing_printer = Printer.search([
                    ('system_name', '=', printer_name)
                ], limit=1)
                
                if existing_printer:
                    # Update existing printer (mark as active if it was inactive)
                    if not existing_printer.active:
                        existing_printer.write({'active': True})
                        updated_count += 1
                else:
                    # Create new printer record
                    Printer.create({
                        'name': printer_name,
                        'system_name': printer_name,
                        'printer_type': 'other',  # Default type, user can change later
                        'active': True,
                    })
                    new_count += 1
            
            return {
                'success': True,
                'new_count': new_count,
                'updated_count': updated_count,
                'total_count': len(printers),
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
            }
