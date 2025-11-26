# -*- coding: utf-8 -*-
import logging
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class QZPrintTemplate(models.Model):
    """
    Model for managing print templates.
    
    This model tracks QWeb templates that are registered for printing,
    making them available for selection in printer configurations and
    providing template versioning support.
    """
    _name = 'qz.print.template'
    _description = 'QZ Print Template'
    _order = 'name'

    name = fields.Char(
        string='Template Name',
        required=True,
        help='Human-readable name for the template'
    )
    
    template_id = fields.Many2one(
        'ir.ui.view',
        string='QWeb Template',
        required=True,
        domain=[('type', '=', 'qweb')],
        help='Reference to the QWeb template view'
    )
    
    template_key = fields.Char(
        string='Template Key',
        related='template_id.key',
        store=True,
        help='XML ID of the template'
    )
    
    category = fields.Selection([
        ('receipt', 'Receipt'),
        ('label', 'Label'),
        ('invoice', 'Invoice'),
        ('document', 'Document'),
        ('report', 'Report'),
        ('other', 'Other'),
    ], string='Category', required=True, default='other',
       help='Category of the print template')
    
    description = fields.Text(
        string='Description',
        help='Description of what this template is used for'
    )
    
    active = fields.Boolean(
        string='Active',
        default=True,
        help='Whether this template is available for use'
    )
    
    version = fields.Integer(
        string='Version',
        default=1,
        readonly=True,
        help='Template version number, incremented on updates'
    )
    
    last_updated = fields.Datetime(
        string='Last Updated',
        readonly=True,
        help='When the template was last updated'
    )
    
    printer_ids = fields.Many2many(
        'qz.printer',
        'qz_printer_template_rel',
        'template_id',
        'printer_id',
        string='Associated Printers',
        help='Printers configured to use this template'
    )
    
    usage_count = fields.Integer(
        string='Usage Count',
        compute='_compute_usage_count',
        help='Number of print jobs using this template'
    )

    _sql_constraints = [
        ('template_id_unique', 'UNIQUE(template_id)',
         'A template can only be registered once!'),
    ]

    @api.depends('template_id')
    def _compute_usage_count(self):
        """Compute the number of print jobs using this template."""
        for template in self:
            if template.template_id:
                count = self.env['qz.print.job'].search_count([
                    ('template_id', '=', template.template_id.id)
                ])
                template.usage_count = count
            else:
                template.usage_count = 0

    @api.model
    def scan_and_register_templates(self):
        """
        Scan for QWeb templates with print category and register them.
        
        This method searches for ir.ui.view records that have a specific
        category or naming convention indicating they are print templates,
        and automatically registers them in the qz.print.template model.
        
        Returns:
            dict: Summary of registration results
            
        Validates: Requirements 8.1
        """
        _logger.info('Starting template scan and registration')
        
        # Search for templates with 'print' in their key or name
        # This is a convention-based approach
        templates_to_register = self.env['ir.ui.view'].search([
            ('type', '=', 'qweb'),
            '|',
            ('key', 'ilike', 'print'),
            ('name', 'ilike', 'print'),
        ])
        
        registered_count = 0
        updated_count = 0
        skipped_count = 0
        
        for view in templates_to_register:
            # Check if already registered
            existing = self.search([('template_id', '=', view.id)])
            
            if existing:
                # Update existing registration
                existing.write({
                    'last_updated': fields.Datetime.now(),
                })
                updated_count += 1
                _logger.debug(f'Updated template registration: {view.key}')
            else:
                # Determine category from template key/name
                category = self._determine_category(view)
                
                # Create new registration
                try:
                    self.create({
                        'name': view.name or view.key,
                        'template_id': view.id,
                        'category': category,
                        'description': f'Auto-registered template: {view.key}',
                        'last_updated': fields.Datetime.now(),
                    })
                    registered_count += 1
                    _logger.info(f'Registered new template: {view.key}')
                except Exception as e:
                    _logger.warning(f'Failed to register template {view.key}: {str(e)}')
                    skipped_count += 1
        
        result = {
            'registered': registered_count,
            'updated': updated_count,
            'skipped': skipped_count,
            'total_active': self.search_count([('active', '=', True)]),
        }
        
        _logger.info(
            f'Template scan complete: {registered_count} registered, '
            f'{updated_count} updated, {skipped_count} skipped'
        )
        
        return result

    @api.model
    def _determine_category(self, view):
        """
        Determine the category of a template based on its key/name.
        
        Args:
            view (ir.ui.view): The view record
            
        Returns:
            str: Category identifier
        """
        key_lower = (view.key or '').lower()
        name_lower = (view.name or '').lower()
        
        if 'receipt' in key_lower or 'receipt' in name_lower:
            return 'receipt'
        elif 'label' in key_lower or 'label' in name_lower:
            return 'label'
        elif 'invoice' in key_lower or 'invoice' in name_lower:
            return 'invoice'
        elif 'report' in key_lower or 'report' in name_lower:
            return 'report'
        elif 'document' in key_lower or 'document' in name_lower:
            return 'document'
        else:
            return 'other'

    @api.model
    def get_templates_by_category(self, category):
        """
        Get all active templates for a specific category.
        
        Args:
            category (str): Template category
            
        Returns:
            recordset: qz.print.template records
            
        Validates: Requirements 8.2
        """
        return self.search([
            ('category', '=', category),
            ('active', '=', True),
        ])

    @api.model
    def get_template_by_key(self, template_key):
        """
        Get a registered template by its XML ID key.
        
        Args:
            template_key (str): Template XML ID
            
        Returns:
            qz.print.template record or False
        """
        return self.search([
            ('template_key', '=', template_key),
            ('active', '=', True),
        ], limit=1)

    def increment_version(self):
        """
        Increment the template version number.
        
        This should be called when the underlying QWeb template is updated
        to track template changes and clear caches.
        
        Validates: Requirements 8.5
        """
        for template in self:
            template.write({
                'version': template.version + 1,
                'last_updated': fields.Datetime.now(),
            })
            _logger.info(
                f'Incremented template version: {template.name} -> v{template.version}'
            )
            
            # Clear template cache to ensure new version is used
            self._clear_template_cache(template.template_id)

    def _clear_template_cache(self, view):
        """
        Clear the QWeb template cache for a specific view.
        
        Args:
            view (ir.ui.view): The view to clear from cache
        """
        # Clear the view cache
        if hasattr(self.env['ir.qweb'], '_compiled_cache'):
            # Clear compiled template cache
            cache = self.env['ir.qweb']._compiled_cache
            if view.id in cache:
                del cache[view.id]
                _logger.debug(f'Cleared template cache for view {view.id}')
        
        # Invalidate the view cache
        view.invalidate_recordset(['arch', 'arch_db'])
        
        _logger.info(f'Template cache cleared for: {view.key}')

    @api.model
    def register_template(self, template_key, name=None, category='other', description=None):
        """
        Manually register a template by its XML ID.
        
        Args:
            template_key (str): XML ID of the template
            name (str): Human-readable name (optional)
            category (str): Template category
            description (str): Template description (optional)
            
        Returns:
            qz.print.template record
            
        Raises:
            ValidationError: If template not found or already registered
        """
        # Find the template view
        try:
            view = self.env.ref(template_key)
        except ValueError:
            raise ValidationError(_('Template "%s" not found') % template_key)
        
        if view.type != 'qweb':
            raise ValidationError(_('Template "%s" is not a QWeb template') % template_key)
        
        # Check if already registered
        existing = self.search([('template_id', '=', view.id)])
        if existing:
            raise ValidationError(
                _('Template "%s" is already registered') % template_key
            )
        
        # Create registration
        template = self.create({
            'name': name or view.name or template_key,
            'template_id': view.id,
            'category': category,
            'description': description or f'Manually registered template: {template_key}',
            'last_updated': fields.Datetime.now(),
        })
        
        _logger.info(f'Manually registered template: {template_key}')
        
        return template

    def unregister_template(self):
        """
        Unregister (deactivate) a template.
        
        This doesn't delete the template record, just marks it as inactive.
        """
        for template in self:
            template.active = False
            _logger.info(f'Unregistered template: {template.name}')

    @api.model
    def check_template_updates(self):
        """
        Check all registered templates for updates and increment versions if needed.
        
        This method compares the write_date of the underlying ir.ui.view records
        with the last_updated timestamp of the template registration. If the view
        has been modified since the last update, the version is incremented.
        
        This can be called periodically via a cron job or manually.
        
        Returns:
            dict: Summary of updates
            
        Validates: Requirements 8.5
        """
        _logger.info('Checking for template updates')
        
        updated_count = 0
        checked_count = 0
        
        # Get all active registered templates
        templates = self.search([('active', '=', True)])
        
        for template in templates:
            checked_count += 1
            
            if not template.template_id:
                continue
            
            view = template.template_id
            
            # Compare write dates
            if view.write_date and template.last_updated:
                if view.write_date > template.last_updated:
                    # Template has been updated
                    template.increment_version()
                    updated_count += 1
                    _logger.info(
                        f'Detected update for template {template.name}: '
                        f'view write_date={view.write_date}, '
                        f'last_updated={template.last_updated}'
                    )
        
        result = {
            'checked': checked_count,
            'updated': updated_count,
        }
        
        _logger.info(
            f'Template update check complete: {checked_count} checked, '
            f'{updated_count} updated'
        )
        
        return result
