# -*- coding: utf-8 -*-
import logging
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class QZPrinter(models.Model):
    _name = 'qz.printer'
    _description = 'QZ Tray Printer Configuration'
    _order = 'priority desc, name'

    # Basic printer information
    name = fields.Char(
        string='Printer Name',
        required=True,
        help='Unique name for this printer configuration'
    )
    
    printer_type = fields.Selection(
        selection=[
            ('receipt', 'Receipt Printer'),
            ('label', 'Label Printer'),
            ('document', 'Document Printer'),
            ('other', 'Other')
        ],
        string='Printer Type',
        required=True,
        default='other',
        help='Type of printer for automatic selection'
    )
    
    system_name = fields.Char(
        string='System Printer Name',
        help='Printer name as reported by QZ Tray'
    )
    
    # Paper and print settings
    paper_size = fields.Selection(
        selection=[
            ('a4', 'A4'),
            ('letter', 'Letter'),
            ('80mm', '80mm (Receipt)'),
            ('58mm', '58mm (Receipt)'),
            ('4x6', '4x6 (Label)'),
            ('custom', 'Custom')
        ],
        string='Paper Size',
        default='a4',
        help='Default paper size for this printer'
    )
    
    orientation = fields.Selection(
        selection=[
            ('portrait', 'Portrait'),
            ('landscape', 'Landscape')
        ],
        string='Orientation',
        default='portrait',
        help='Default page orientation'
    )
    
    print_quality = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('normal', 'Normal'),
            ('high', 'High Quality')
        ],
        string='Print Quality',
        default='normal',
        help='Default print quality setting'
    )
    
    # Location and assignment
    location_id = fields.Many2one(
        comodel_name='res.company',
        string='Location/Company',
        help='Company or location this printer is assigned to'
    )
    
    department = fields.Char(
        string='Department',
        help='Department this printer is assigned to'
    )
    
    # Printer status and priority
    is_default = fields.Boolean(
        string='Default Printer',
        default=False,
        help='Use this printer as default for its type'
    )
    
    priority = fields.Integer(
        string='Priority',
        default=10,
        help='Selection priority when multiple printers match (higher = higher priority)'
    )
    
    active = fields.Boolean(
        string='Active',
        default=True,
        help='Whether this printer is available for use'
    )
    
    # Supported formats (stored as comma-separated string)
    supported_formats = fields.Selection(
        selection=[
            ('pdf', 'PDF'),
            ('html', 'HTML'),
            ('escpos', 'ESC/POS'),
            ('zpl', 'ZPL')
        ],
        string='Supported Formats',
        help='Print formats supported by this printer'
    )
    
    # Additional format support fields for multiple selection
    supports_pdf = fields.Boolean(string='Supports PDF', default=True)
    supports_html = fields.Boolean(string='Supports HTML', default=True)
    supports_escpos = fields.Boolean(string='Supports ESC/POS', default=False)
    supports_zpl = fields.Boolean(string='Supports ZPL', default=False)
    
    # Template relationship
    template_ids = fields.Many2many(
        'qz.print.template',
        'qz_printer_template_rel',
        'printer_id',
        'template_id',
        string='Available Templates',
        help='Print templates available for this printer'
    )
    
    # Audit fields
    create_date = fields.Datetime(string='Created On', readonly=True)
    write_date = fields.Datetime(string='Last Updated', readonly=True)
    create_uid = fields.Many2one('res.users', string='Created By', readonly=True)
    write_uid = fields.Many2one('res.users', string='Last Updated By', readonly=True)

    # SQL constraints
    _sql_constraints = [
        ('name_unique', 'UNIQUE(name)', 'Printer name must be unique!'),
    ]

    @api.constrains('name')
    def _check_name_not_empty(self):
        """Validate that printer name is not empty"""
        for record in self:
            if not record.name or not record.name.strip():
                raise ValidationError(_('Printer name cannot be empty'))

    @api.constrains('priority')
    def _check_priority(self):
        """Validate priority value"""
        for record in self:
            if record.priority < 0:
                raise ValidationError(_('Priority cannot be negative'))

    @api.model
    def get_available_printers(self):
        """
        Retrieve list of available printers from QZ Tray
        
        Note: This method prepares the structure for printer discovery.
        Actual QZ Tray communication happens via JavaScript/WebSocket.
        This method can be called from the frontend to trigger discovery
        and process the results.
        
        Returns:
            dict: Action dict or list of printer information
        """
        # Check if QZ Tray credentials are configured
        QZConfig = self.env['qz.tray.config']
        credentials = QZConfig.get_credentials()
        
        if not credentials:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Configuration Required'),
                    'message': _('Please configure QZ Tray credentials before discovering printers'),
                    'type': 'warning',
                    'sticky': False,
                }
            }
        
        # Return action to trigger JavaScript printer discovery
        # The actual discovery will be handled by the frontend
        return {
            'type': 'ir.actions.client',
            'tag': 'qz_discover_printers',
            'params': {
                'model': self._name,
                'method': 'process_discovered_printers',
            }
        }
    
    @api.model
    def process_discovered_printers(self, printer_list):
        """
        Process printer list received from QZ Tray
        
        Args:
            printer_list: List of printer names from QZ Tray
            
        Returns:
            dict: Result with created/updated printer records
        """
        if not printer_list:
            return {
                'success': False,
                'message': _('No printers found')
            }
        
        created_printers = []
        updated_printers = []
        
        for printer_name in printer_list:
            # Check if printer already exists
            existing_printer = self.search([('system_name', '=', printer_name)], limit=1)
            
            if existing_printer:
                # Update existing printer
                existing_printer.write({
                    'active': True,
                })
                updated_printers.append(existing_printer.name)
            else:
                # Create new printer record
                # Try to detect printer type from name
                printer_type = self._detect_printer_type(printer_name)
                
                new_printer = self.create({
                    'name': printer_name,
                    'system_name': printer_name,
                    'printer_type': printer_type,
                    'active': True,
                })
                created_printers.append(new_printer.name)
        
        # Build result message
        message_parts = []
        if created_printers:
            message_parts.append(_('Created %d printer(s): %s') % (
                len(created_printers), ', '.join(created_printers)
            ))
        if updated_printers:
            message_parts.append(_('Updated %d printer(s): %s') % (
                len(updated_printers), ', '.join(updated_printers)
            ))
        
        return {
            'success': True,
            'message': '\n'.join(message_parts),
            'created_count': len(created_printers),
            'updated_count': len(updated_printers),
        }
    
    def _detect_printer_type(self, printer_name):
        """
        Attempt to detect printer type from printer name
        
        Args:
            printer_name: Name of the printer
            
        Returns:
            str: Detected printer type
        """
        name_lower = printer_name.lower()
        
        # Check for common receipt printer keywords
        if any(keyword in name_lower for keyword in ['receipt', 'pos', 'thermal', 'tm-', 'epson']):
            return 'receipt'
        
        # Check for common label printer keywords
        if any(keyword in name_lower for keyword in ['label', 'zebra', 'zpl', 'barcode']):
            return 'label'
        
        # Check for document printer keywords
        if any(keyword in name_lower for keyword in ['laser', 'inkjet', 'office', 'hp', 'canon', 'brother']):
            return 'document'
        
        # Default to 'other' if no match
        return 'other'

    @api.model
    def get_default_printer(self, printer_type=None, location_id=None, department=None):
        """
        Get the default printer for a given type and location
        
        Selection algorithm:
        1. Look for printers matching the type
        2. Filter by location/department if specified
        3. Prioritize by:
           - is_default flag
           - priority value (higher is better)
           - creation date (newer first)
        
        Args:
            printer_type: Type of printer ('receipt', 'label', 'document', 'other')
            location_id: Company/location ID for filtering
            department: Department name for filtering
            
        Returns:
            qz.printer record or False if no match found
        """
        domain = [('active', '=', True)]
        
        # Filter by printer type if specified
        if printer_type:
            domain.append(('printer_type', '=', printer_type))
        
        # Filter by location if specified
        if location_id:
            domain.append('|')
            domain.append(('location_id', '=', location_id))
            domain.append(('location_id', '=', False))
        
        # Filter by department if specified
        if department:
            domain.append('|')
            domain.append(('department', '=', department))
            domain.append(('department', '=', False))
        
        # Search for matching printers
        printers = self.search(domain)
        
        if not printers:
            _logger.warning(
                f'No printer found for type={printer_type}, '
                f'location_id={location_id}, department={department}'
            )
            return False
        
        # Apply selection algorithm
        selected_printer = self._select_best_printer(
            printers, 
            location_id=location_id, 
            department=department
        )
        
        return selected_printer
    
    def _select_best_printer(self, printers, location_id=None, department=None):
        """
        Select the best printer from a list based on priority rules
        
        Priority order:
        1. Exact location and department match with is_default=True
        2. Exact location and department match with highest priority
        3. Location match with is_default=True
        4. Location match with highest priority
        5. Department match with is_default=True
        6. Department match with highest priority
        7. Any printer with is_default=True
        8. Any printer with highest priority
        
        Args:
            printers: Recordset of qz.printer records
            location_id: Preferred location ID
            department: Preferred department
            
        Returns:
            qz.printer record
        """
        if not printers:
            return False
        
        if len(printers) == 1:
            return printers
        
        # Score each printer
        scored_printers = []
        for printer in printers:
            score = 0
            
            # Location match scoring
            if location_id and printer.location_id.id == location_id:
                score += 1000
            elif not printer.location_id:
                score += 100  # Unassigned printers are fallback
            
            # Department match scoring
            if department and printer.department == department:
                score += 500
            elif not printer.department:
                score += 50  # Unassigned printers are fallback
            
            # Default flag scoring
            if printer.is_default:
                score += 10000
            
            # Priority scoring
            score += printer.priority
            
            scored_printers.append((score, printer))
        
        # Sort by score (descending) and return the best match
        scored_printers.sort(key=lambda x: x[0], reverse=True)
        
        best_printer = scored_printers[0][1]
        
        _logger.info(
            f'Selected printer: {best_printer.name} '
            f'(type={best_printer.printer_type}, score={scored_printers[0][0]})'
        )
        
        return best_printer
    
    def test_print(self):
        """
        Send a test page to this printer
        
        Returns:
            dict: Action dict with notification
        """
        self.ensure_one()
        
        # Check if QZ Tray is configured
        QZConfig = self.env['qz.tray.config']
        credentials = QZConfig.get_credentials()
        
        if not credentials:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Configuration Required'),
                    'message': _('Please configure QZ Tray credentials before testing printer'),
                    'type': 'warning',
                    'sticky': False,
                }
            }
        
        # Return action to trigger JavaScript test print
        return {
            'type': 'ir.actions.client',
            'tag': 'qz_test_print',
            'params': {
                'printer_id': self.id,
                'printer_name': self.system_name or self.name,
            }
        }

    def write(self, vals):
        """
        Override write to detect when printer comes online
        and automatically process queued jobs
        """
        # Track printers that are being activated
        printers_to_process = self.env['qz.printer']
        
        for printer in self:
            # Check if printer is being activated (offline -> online)
            if 'active' in vals and vals['active'] and not printer.active:
                printers_to_process |= printer
        
        # Call parent write method
        result = super(QZPrinter, self).write(vals)
        
        # Process queued jobs for printers that came online
        if printers_to_process:
            for printer in printers_to_process:
                printer._process_queued_jobs_on_activation()
        
        return result
    
    def _process_queued_jobs_on_activation(self):
        """
        Automatically process queued jobs when printer comes online
        
        This method is called when a printer's active flag changes from False to True
        """
        self.ensure_one()
        
        # Get all queued jobs for this printer
        queued_jobs = self.env['qz.print.job'].search([
            ('printer_id', '=', self.id),
            ('state', '=', 'queued')
        ], order='submitted_date asc, priority desc, id asc')
        
        if not queued_jobs:
            _logger.info(f'No queued jobs found for printer {self.name}')
            return
        
        _logger.info(
            f'Printer {self.name} came online. '
            f'Processing {len(queued_jobs)} queued job(s)'
        )
        
        processed_count = 0
        failed_count = 0
        
        # Process each queued job
        for job in queued_jobs:
            try:
                success = job.process_job()
                if success:
                    processed_count += 1
                else:
                    failed_count += 1
            except Exception as e:
                failed_count += 1
                _logger.error(
                    f'Error processing queued job {job.name} '
                    f'for printer {self.name}: {str(e)}'
                )
        
        _logger.info(
            f'Completed processing queued jobs for printer {self.name}: '
            f'{processed_count} processed, {failed_count} failed'
        )
