# -*- coding: utf-8 -*-
import logging
from odoo import models, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class ProductProduct(models.Model):
    """
    Extend product.product with label printing capabilities.
    
    This model adds methods to print product labels using the QZ Tray print service.
    """
    _name = 'product.product'
    _inherit = ['product.product', 'qz.print.service']

    def action_print_label(self):
        """
        Print a single product label.
        
        This action can be called from the product form view or list view.
        
        Returns:
            dict: Action result with notification
        """
        self.ensure_one()
        
        _logger.info(f'Printing label for product {self.id}: {self.name}')
        
        try:
            # Prepare label data
            label_data = {
                'product_id': self.id,
                'date': self.env.context.get('label_date'),
            }
            
            # Print the label
            result = self.print_label(label_data)
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Label Print Submitted'),
                    'message': _('Label print job %s has been submitted for product %s') % (
                        result['job_id'], self.name
                    ),
                    'type': 'success',
                    'sticky': False,
                }
            }
        except Exception as e:
            _logger.error(f'Failed to print label for product {self.id}: {str(e)}')
            raise UserError(_('Failed to print label: %s') % str(e))

    def action_print_labels_batch(self):
        """
        Print labels for multiple products in a single job.
        
        This action can be called from the product list view with multiple selections.
        
        Returns:
            dict: Action result with notification
        """
        if not self:
            raise UserError(_('No products selected'))
        
        _logger.info(f'Printing batch labels for {len(self)} products')
        
        try:
            # Prepare label data for all products
            labels_data = []
            for product in self:
                label_data = {
                    'product_id': product.id,
                    'date': self.env.context.get('label_date'),
                }
                labels_data.append(label_data)
            
            # Print all labels in a single job
            result = self.print_labels_batch(labels_data)
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Batch Label Print Submitted'),
                    'message': _('Batch label print job %s has been submitted for %d products') % (
                        result['job_id'], len(self)
                    ),
                    'type': 'success',
                    'sticky': False,
                }
            }
        except Exception as e:
            _logger.error(f'Failed to print batch labels: {str(e)}')
            raise UserError(_('Failed to print batch labels: %s') % str(e))

    @api.model
    def print_product_label(self, product_id, **options):
        """
        API method to print a product label by ID.
        
        This method can be called from other modules or via RPC.
        
        Args:
            product_id (int): Product ID
            **options: Additional print options (printer, template, etc.)
            
        Returns:
            dict: Print job information
        """
        product = self.browse(product_id)
        if not product.exists():
            raise UserError(_('Product with ID %s not found') % product_id)
        
        label_data = {
            'product_id': product.id,
            'date': options.get('date'),
        }
        
        return self.print_label(
            label_data,
            printer=options.get('printer'),
            template=options.get('template'),
            **options
        )
