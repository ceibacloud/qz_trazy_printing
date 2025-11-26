# -*- coding: utf-8 -*-
import logging
from odoo import models, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class PosOrder(models.Model):
    """
    Extend POS Order model to add receipt printing capabilities.
    
    This extension integrates the QZ Tray print service with POS orders,
    enabling automatic receipt printing after sale completion.
    
    Note: This model only loads if the point_of_sale module is installed.
    """
    _name = 'pos.order'
    _inherit = ['pos.order', 'qz.print.service']
    _description = 'POS Order with QZ Tray Print Integration'
    
    @api.model
    def print_pos_receipt(self, order_id, printer=None, auto_print=False):
        """
        Print a POS receipt for the specified order.
        
        Args:
            order_id (int): ID of the POS order
            printer (int|str): Printer ID or name (optional)
            auto_print (bool): Whether this is automatic printing
            
        Returns:
            dict: Print job information or error details
            
        Validates: Requirements 5.1, 5.2, 5.3, 5.4
        """
        _logger.info(f'print_pos_receipt called for order {order_id}')
        
        try:
            # Get the order
            order = self.browse(order_id)
            if not order.exists():
                raise UserError(_('Order not found'))
            
            # Prepare receipt data
            receipt_data = self._prepare_receipt_data(order)
            
            # Print the receipt
            result = self.print_receipt(
                receipt_data=receipt_data,
                printer=printer,
                document_type='receipt',
                parent_model='pos.order',
                parent_id=order.id,
            )
            
            _logger.info(
                f'Receipt print job {result["job_id"]} created for order {order.name}'
            )
            
            return {
                'success': True,
                'job_id': result['job_id'],
                'order_name': order.name,
                'printer': result['printer'],
            }
            
        except Exception as e:
            _logger.error(f'Failed to print POS receipt: {str(e)}')
            return {
                'success': False,
                'error': str(e),
            }
    
    def _prepare_receipt_data(self, order):
        """
        Prepare receipt data from a POS order.
        
        Args:
            order (pos.order): POS order record
            
        Returns:
            dict: Receipt data formatted for printing
        """
        # Prepare line items
        lines = []
        for line in order.lines:
            lines.append({
                'name': line.product_id.name,
                'quantity': line.qty,
                'price_unit': line.price_unit,
                'price_subtotal': line.price_subtotal_incl,
                'discount': line.discount,
            })
        
        # Prepare payment information
        payments = []
        for payment in order.payment_ids:
            payments.append({
                'name': payment.payment_method_id.name,
                'amount': payment.amount,
            })
        
        # Build receipt data
        receipt_data = {
            'name': order.name,
            'date': order.date_order,
            'lines': lines,
            'amount_untaxed': order.amount_total - order.amount_tax,
            'amount_tax': order.amount_tax,
            'amount_total': order.amount_total,
            'amount_discount': sum(line.price_subtotal * line.discount / 100 
                                  for line in order.lines if line.discount > 0),
            'payments': payments,
        }
        
        # Add customer information if available
        if order.partner_id:
            receipt_data['partner_id'] = order.partner_id.id
        
        return receipt_data
    
    def action_print_receipt(self):
        """
        Action to print receipt from POS order form view.
        
        This method can be called from a button in the POS order form.
        
        Returns:
            dict: Action result with notification
        """
        self.ensure_one()
        
        result = self.print_pos_receipt(self.id)
        
        if result['success']:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Receipt Printing'),
                    'message': _('Receipt print job %s submitted successfully') % result['job_id'],
                    'type': 'success',
                    'sticky': False,
                }
            }
        else:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Receipt Printing Failed'),
                    'message': result['error'],
                    'type': 'danger',
                    'sticky': True,
                }
            }
    
    def _process_saved_order(self, draft):
        """
        Override to add automatic receipt printing after order is saved.
        
        This method is called when a POS order is finalized.
        
        Args:
            draft (dict): Order data from POS
            
        Returns:
            pos.order: Created/updated order record
        """
        # Call parent method to process the order
        order = super(PosOrder, self)._process_saved_order(draft)
        
        # Check if automatic printing is enabled for this session
        if order.session_id.config_id:
            config = order.session_id.config_id
            # Check if auto-print is enabled (this would be a custom field on pos.config)
            # For now, we'll check if there's a receipt printer configured
            receipt_printer = self.env['qz.printer'].search([
                ('printer_type', '=', 'receipt'),
                ('is_default', '=', True),
                ('active', '=', True),
            ], limit=1)
            
            if receipt_printer:
                _logger.info(
                    f'Auto-printing receipt for order {order.name} '
                    f'to printer {receipt_printer.name}'
                )
                try:
                    self.print_pos_receipt(order.id, printer=receipt_printer.id, auto_print=True)
                except Exception as e:
                    # Log error but don't fail the order processing
                    _logger.error(
                        f'Auto-print failed for order {order.name}: {str(e)}'
                    )
        
        return order
