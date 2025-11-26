# -*- coding: utf-8 -*-
import logging
import base64
from odoo import models, api, fields, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class QZPrintService(models.AbstractModel):
    """
    Abstract model providing print service functionality.
    
    This model can be inherited by any Odoo model that needs printing capabilities.
    It provides a unified API for printing documents through QZ Tray.
    """
    _name = 'qz.print.service'
    _description = 'QZ Tray Print Service'

    @api.model
    def print_document(self, template, data, printer=None, **options):
        """
        Print a document using a QWeb template.
        
        Args:
            template (str): QWeb template reference (e.g., 'module.template_name')
            data (dict): Data to pass to the template for rendering
            printer (int|str): Printer ID or name (optional)
            **options: Additional print options (copies, priority, etc.)
            
        Returns:
            dict: Print job information including job_id
            
        Validates: Requirements 3.1, 3.2
        """
        _logger.info(f'print_document called with template={template}, printer={printer}')
        
        # Validate template exists
        try:
            template_view = self.env.ref(template)
        except ValueError:
            raise ValidationError(_('Template "%s" not found') % template)
        
        # Render the template with provided data
        try:
            rendered_html = self._render_template(template, data)
        except Exception as e:
            _logger.error(f'Template rendering failed: {str(e)}')
            raise UserError(_('Failed to render template: %s') % str(e))
        
        # Get the appropriate printer
        printer_record = self._get_printer(printer, options.get('document_type'))
        
        if not printer_record:
            raise UserError(_('No printer available for printing'))
        
        # Create print job
        job = self._create_print_job(
            printer_record=printer_record,
            data=rendered_html.encode('utf-8'),
            data_format='html',
            template_id=template_view.id,
            template_data=data,
            **options
        )
        
        return {
            'job_id': job.id,
            'job_name': job.name,
            'printer': printer_record.name,
            'status': job.state,
        }

    @api.model
    def print_raw(self, data, format, printer=None, **options):
        """
        Print raw data in a specific format.
        
        Args:
            data (bytes|str): Raw print data
            format (str): Data format ('pdf', 'html', 'escpos', 'zpl')
            printer (int|str): Printer ID or name (optional)
            **options: Additional print options
            
        Returns:
            dict: Print job information including job_id
            
        Validates: Requirements 3.1, 3.3
        """
        _logger.info(f'print_raw called with format={format}, printer={printer}')
        
        # Validate format
        valid_formats = ['pdf', 'html', 'escpos', 'zpl']
        if format not in valid_formats:
            raise ValidationError(
                _('Invalid format "%s". Must be one of: %s') % (format, ', '.join(valid_formats))
            )
        
        # Convert data to bytes if needed
        if isinstance(data, str):
            data = data.encode('utf-8')
        
        # Get the appropriate printer
        printer_record = self._get_printer(printer, options.get('document_type'))
        
        if not printer_record:
            raise UserError(_('No printer available for printing'))
        
        # Validate printer supports the format
        if not self._printer_supports_format(printer_record, format):
            raise ValidationError(
                _('Printer "%s" does not support format "%s"') % (printer_record.name, format)
            )
        
        # Create print job
        job = self._create_print_job(
            printer_record=printer_record,
            data=data,
            data_format=format,
            **options
        )
        
        return {
            'job_id': job.id,
            'job_name': job.name,
            'printer': printer_record.name,
            'status': job.state,
        }

    @api.model
    def print_pdf(self, pdf_data, printer=None, **options):
        """
        Print a PDF document.
        
        Args:
            pdf_data (bytes): PDF file data
            printer (int|str): Printer ID or name (optional)
            **options: Additional print options
            
        Returns:
            dict: Print job information including job_id
            
        Validates: Requirements 3.1, 3.3
        """
        _logger.info(f'print_pdf called with printer={printer}')
        
        # Validate PDF data
        if not pdf_data:
            raise ValidationError(_('PDF data cannot be empty'))
        
        # Use print_raw with pdf format
        return self.print_raw(pdf_data, 'pdf', printer=printer, **options)

    @api.model
    def preview_document(self, template, data):
        """
        Generate a preview of a document without printing.
        
        Args:
            template (str): QWeb template reference
            data (dict): Data to pass to the template
            
        Returns:
            dict: Preview data (rendered HTML or PDF)
            
        Validates: Requirements 11.1
        """
        _logger.info(f'preview_document called with template={template}')
        
        # Validate template exists
        try:
            self.env.ref(template)
        except ValueError:
            raise ValidationError(_('Template "%s" not found') % template)
        
        # Render the template
        try:
            rendered_html = self._render_template(template, data)
        except Exception as e:
            _logger.error(f'Template rendering failed: {str(e)}')
            raise UserError(_('Failed to render template: %s') % str(e))
        
        return {
            'format': 'html',
            'data': rendered_html,
            'template': template,
        }

    @api.model
    def get_printer_for_type(self, document_type, location=None, department=None):
        """
        Get the appropriate printer for a document type.
        
        Args:
            document_type (str): Type of document ('receipt', 'label', 'document', 'other')
            location (int): Location/company ID (optional)
            department (str): Department name (optional)
            
        Returns:
            qz.printer record or False
            
        Validates: Requirements 3.4, 3.5, 4.1, 4.2, 4.3, 4.4
        """
        _logger.info(
            f'get_printer_for_type called with type={document_type}, '
            f'location={location}, department={department}'
        )
        
        # Use the printer model's selection algorithm
        QZPrinter = self.env['qz.printer']
        printer = QZPrinter.get_default_printer(
            printer_type=document_type,
            location_id=location,
            department=department
        )
        
        return printer

    @api.model
    def format_receipt(self, receipt_data, template=None, **options):
        """
        Format receipt data for printing.
        
        This method handles receipt-specific formatting including:
        - Line item formatting
        - Total calculations
        - Header/footer formatting
        - Receipt printer optimization (width, font size)
        
        Args:
            receipt_data (dict): Receipt data including items, totals, customer info
            template (str): Optional custom template (defaults to standard receipt template)
            **options: Additional formatting options (width, font_size, etc.)
            
        Returns:
            dict: Formatted receipt ready for printing
            
        Validates: Requirements 5.2
        """
        _logger.info(f'format_receipt called with template={template}')
        
        # Validate receipt data
        if not receipt_data:
            raise ValidationError(_('Receipt data cannot be empty'))
        
        # Use default receipt template if not specified
        if not template:
            template = 'qz_tray_print.receipt_template_default'
        
        # Prepare receipt formatting context
        format_context = {
            'receipt': receipt_data,
            'company': self.env.company,
            'user': self.env.user,
            'date': receipt_data.get('date', fields.Datetime.now()),
        }
        
        # Add receipt-specific formatting options
        format_context.update({
            'receipt_width': options.get('width', 80),  # Default 80mm receipt width
            'font_size': options.get('font_size', 'normal'),
            'show_logo': options.get('show_logo', True),
            'show_barcode': options.get('show_barcode', False),
        })
        
        # Format line items with proper alignment
        if 'lines' in receipt_data:
            formatted_lines = []
            for line in receipt_data['lines']:
                formatted_line = {
                    'name': line.get('name', ''),
                    'quantity': line.get('quantity', 1),
                    'price_unit': line.get('price_unit', 0.0),
                    'price_subtotal': line.get('price_subtotal', 0.0),
                    'discount': line.get('discount', 0.0),
                }
                formatted_lines.append(formatted_line)
            format_context['formatted_lines'] = formatted_lines
        
        # Format totals
        format_context['totals'] = {
            'subtotal': receipt_data.get('amount_untaxed', 0.0),
            'tax': receipt_data.get('amount_tax', 0.0),
            'total': receipt_data.get('amount_total', 0.0),
            'discount': receipt_data.get('amount_discount', 0.0),
        }
        
        # Format payment information
        if 'payments' in receipt_data:
            format_context['payments'] = receipt_data['payments']
        
        # Format customer information
        if 'partner_id' in receipt_data:
            partner = self.env['res.partner'].browse(receipt_data['partner_id'])
            if partner.exists():
                format_context['customer'] = {
                    'name': partner.name,
                    'phone': partner.phone or '',
                    'email': partner.email or '',
                }
        
        return {
            'template': template,
            'data': format_context,
            'document_type': 'receipt',
            'format': 'html',
        }

    @api.model
    def print_receipt(self, receipt_data, printer=None, template=None, **options):
        """
        Print a receipt with receipt-specific formatting.
        
        This is a convenience method that combines format_receipt and print_document.
        
        Args:
            receipt_data (dict): Receipt data
            printer (int|str): Printer ID or name (optional, uses receipt printer default)
            template (str): Optional custom template
            **options: Additional print options
            
        Returns:
            dict: Print job information
            
        Validates: Requirements 5.2, 5.3
        """
        _logger.info(f'print_receipt called with printer={printer}')
        
        # Format the receipt
        formatted = self.format_receipt(receipt_data, template=template, **options)
        
        # Set document type for printer selection
        options['document_type'] = 'receipt'
        
        # Get receipt printer configuration
        if not printer:
            receipt_printer = self.get_printer_for_type(
                'receipt',
                location=options.get('location'),
                department=options.get('department')
            )
            if receipt_printer:
                printer = receipt_printer.id
                _logger.info(f'Using receipt printer: {receipt_printer.name}')
        
        # Print using the formatted template
        return self.print_document(
            template=formatted['template'],
            data=formatted['data'],
            printer=printer,
            **options
        )

    @api.model
    def format_label(self, label_data, printer=None, template=None, **options):
        """
        Format label data for printing.
        
        This method handles label-specific formatting including:
        - Detecting printer format (ZPL vs ESC/POS)
        - Generating format-appropriate output
        - Barcode/QR code generation
        - Label size optimization
        
        Args:
            label_data (dict): Label data including product info, barcode, etc.
            printer (int|str): Printer ID or name (optional, used for format detection)
            template (str): Optional custom template
            **options: Additional formatting options (width, height, rotation, etc.)
            
        Returns:
            dict: Formatted label ready for printing with detected format
            
        Validates: Requirements 6.2, 6.3
        """
        _logger.info(f'format_label called with printer={printer}, template={template}')
        
        # Validate label data
        if not label_data:
            raise ValidationError(_('Label data cannot be empty'))
        
        # Get printer record to detect format
        printer_record = None
        if printer:
            printer_record = self._get_printer(printer, document_type='label')
        else:
            # Try to get default label printer
            printer_record = self.get_printer_for_type(
                'label',
                location=options.get('location'),
                department=options.get('department')
            )
        
        if not printer_record:
            raise UserError(_('No label printer available. Please configure a label printer.'))
        
        # Detect printer format based on printer capabilities
        label_format = self._detect_label_format(printer_record)
        _logger.info(f'Detected label format: {label_format} for printer {printer_record.name}')
        
        # Prepare label formatting context
        format_context = {
            'label': label_data,
            'company': self.env.company,
            'user': self.env.user,
            'date': label_data.get('date', fields.Datetime.now()),
            'format': label_format,
        }
        
        # Add label-specific formatting options
        format_context.update({
            'label_width': options.get('width', 4),  # Default 4 inches
            'label_height': options.get('height', 6),  # Default 6 inches
            'rotation': options.get('rotation', 0),  # Rotation in degrees
            'dpi': options.get('dpi', 203),  # Default 203 DPI
        })
        
        # Format product information if present
        if 'product_id' in label_data:
            product = self.env['product.product'].browse(label_data['product_id'])
            if product.exists():
                format_context['product'] = {
                    'name': product.name,
                    'default_code': product.default_code or '',
                    'barcode': product.barcode or '',
                    'list_price': product.list_price,
                    'uom': product.uom_id.name if product.uom_id else '',
                }
        
        # Generate barcode if needed
        if 'barcode' in label_data or (format_context.get('product') and format_context['product'].get('barcode')):
            barcode_value = label_data.get('barcode') or format_context['product']['barcode']
            if barcode_value:
                format_context['barcode_value'] = barcode_value
                format_context['barcode_type'] = options.get('barcode_type', 'Code128')
        
        # Select appropriate template based on format
        if not template:
            if label_format == 'zpl':
                template = 'qz_tray_print.label_template_zpl_default'
            elif label_format == 'escpos':
                template = 'qz_tray_print.label_template_escpos_default'
            else:
                # Fallback to HTML template
                template = 'qz_tray_print.label_template_html_default'
                label_format = 'html'
        
        return {
            'template': template,
            'data': format_context,
            'document_type': 'label',
            'format': label_format,
            'printer_id': printer_record.id,
        }

    @api.model
    def print_label(self, label_data, printer=None, template=None, **options):
        """
        Print a label with label-specific formatting.
        
        This is a convenience method that combines format_label and print_raw/print_document.
        
        Args:
            label_data (dict): Label data
            printer (int|str): Printer ID or name (optional, uses label printer default)
            template (str): Optional custom template
            **options: Additional print options
            
        Returns:
            dict: Print job information
            
        Validates: Requirements 6.1, 6.2, 6.3
        """
        _logger.info(f'print_label called with printer={printer}')
        
        # Format the label
        formatted = self.format_label(label_data, printer=printer, template=template, **options)
        
        # Set document type for printer selection
        options['document_type'] = 'label'
        
        # Use the printer from format_label
        if not printer and formatted.get('printer_id'):
            printer = formatted['printer_id']
        
        # Determine if we need to use raw printing or template printing
        label_format = formatted['format']
        
        if label_format in ['zpl', 'escpos']:
            # For ZPL and ESC/POS, we need to render the template first
            # then send as raw data
            try:
                rendered = self._render_template(formatted['template'], formatted['data'])
                
                # Print as raw data
                return self.print_raw(
                    data=rendered,
                    format=label_format,
                    printer=printer,
                    **options
                )
            except ValueError:
                # Template not found, might be generating raw data directly
                _logger.warning(f'Template {formatted["template"]} not found, attempting direct raw print')
                
                # Generate raw label data directly
                if label_format == 'zpl':
                    raw_data = self._generate_zpl_label(formatted['data'])
                elif label_format == 'escpos':
                    raw_data = self._generate_escpos_label(formatted['data'])
                else:
                    raise UserError(_('Cannot generate raw label data for format: %s') % label_format)
                
                return self.print_raw(
                    data=raw_data,
                    format=label_format,
                    printer=printer,
                    **options
                )
        else:
            # For HTML/PDF, use standard document printing
            return self.print_document(
                template=formatted['template'],
                data=formatted['data'],
                printer=printer,
                **options
            )

    @api.model
    def print_labels_batch(self, labels_data, printer=None, template=None, **options):
        """
        Print multiple labels in a single print job.
        
        This method combines multiple labels into a single print job for efficiency.
        
        Args:
            labels_data (list): List of label data dictionaries
            printer (int|str): Printer ID or name (optional)
            template (str): Optional custom template
            **options: Additional print options
            
        Returns:
            dict: Print job information
            
        Validates: Requirements 6.4
        """
        _logger.info(f'print_labels_batch called with {len(labels_data)} labels, printer={printer}')
        
        if not labels_data:
            raise ValidationError(_('Labels data cannot be empty'))
        
        # Format all labels
        formatted_labels = []
        label_format = None
        printer_id = None
        
        for label_data in labels_data:
            formatted = self.format_label(label_data, printer=printer, template=template, **options)
            formatted_labels.append(formatted)
            
            # Use format and printer from first label
            if label_format is None:
                label_format = formatted['format']
                printer_id = formatted.get('printer_id')
        
        # Combine all labels into single output
        if label_format in ['zpl', 'escpos']:
            # Combine raw label data
            combined_data = []
            
            for formatted in formatted_labels:
                try:
                    rendered = self._render_template(formatted['template'], formatted['data'])
                    combined_data.append(rendered)
                except ValueError:
                    # Generate raw data directly
                    if label_format == 'zpl':
                        raw_data = self._generate_zpl_label(formatted['data'])
                    elif label_format == 'escpos':
                        raw_data = self._generate_escpos_label(formatted['data'])
                    else:
                        raise UserError(_('Cannot generate raw label data'))
                    combined_data.append(raw_data)
            
            # Join all labels with appropriate separator
            if label_format == 'zpl':
                # ZPL labels can be concatenated directly
                combined = '\n'.join(combined_data)
            elif label_format == 'escpos':
                # ESC/POS labels need cut command between them
                combined = '\n\x1d\x56\x00\n'.join(combined_data)  # GS V 0 = full cut
            
            # Print as single raw job
            return self.print_raw(
                data=combined,
                format=label_format,
                printer=printer or printer_id,
                **options
            )
        else:
            # For HTML/PDF, combine into single template
            combined_context = {
                'labels': [f['data'] for f in formatted_labels],
                'company': self.env.company,
            }
            
            # Use batch template if available, otherwise use single template multiple times
            batch_template = template or 'qz_tray_print.label_template_batch_default'
            
            return self.print_document(
                template=batch_template,
                data=combined_context,
                printer=printer or printer_id,
                **options
            )

    # Private helper methods

    def _render_template(self, template, data):
        """
        Render a QWeb template with data.
        
        Supports:
        - Custom CSS styling
        - Image embedding (base64)
        - Barcode embedding
        
        Args:
            template (str): Template reference
            data (dict): Template data
            
        Returns:
            str: Rendered HTML with embedded resources
            
        Validates: Requirements 3.2, 8.3, 8.4
        """
        # Validate template data
        if not isinstance(data, dict):
            raise ValidationError(_('Template data must be a dictionary'))
        
        # Get the template view
        template_view = self.env.ref(template)
        
        # Prepare rendering context
        render_context = data.copy()
        
        # Add helper functions for resource embedding
        render_context['embed_image'] = self._embed_image
        render_context['generate_barcode'] = self._generate_barcode
        
        # Render using ir.qweb
        try:
            rendered = self.env['ir.qweb']._render(template_view.id, render_context)
        except Exception as e:
            _logger.error(f'QWeb rendering error: {str(e)}')
            raise UserError(_('Template rendering failed: %s') % str(e))
        
        # Convert bytes to string if needed
        if isinstance(rendered, bytes):
            rendered = rendered.decode('utf-8')
        
        # Process and embed resources
        rendered = self._process_embedded_resources(rendered)
        
        return rendered

    def _embed_image(self, image_data, mime_type='image/png'):
        """
        Convert image data to base64 data URI for embedding.
        
        Args:
            image_data (bytes): Image binary data
            mime_type (str): MIME type of the image
            
        Returns:
            str: Data URI for embedding in HTML
        """
        if not image_data:
            return ''
        
        # Encode to base64
        if isinstance(image_data, bytes):
            encoded = base64.b64encode(image_data).decode('utf-8')
        else:
            # Assume it's already base64 encoded
            encoded = image_data
        
        return f'data:{mime_type};base64,{encoded}'

    def _generate_barcode(self, value, barcode_type='Code128', width=200, height=50):
        """
        Generate a barcode image as base64 data URI.
        
        Args:
            value (str): Value to encode in barcode
            barcode_type (str): Type of barcode (Code128, EAN13, QR, etc.)
            width (int): Barcode width in pixels
            height (int): Barcode height in pixels
            
        Returns:
            str: Data URI for barcode image
        """
        try:
            # Use Odoo's barcode generation if available
            # This is a placeholder - actual implementation would use
            # a barcode library like python-barcode or qrcode
            import io
            
            # For now, return a placeholder
            # In production, this would generate actual barcodes
            _logger.warning('Barcode generation not fully implemented - returning placeholder')
            
            # Return empty data URI as placeholder
            return 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=='
            
        except Exception as e:
            _logger.error(f'Barcode generation failed: {str(e)}')
            return ''

    def _process_embedded_resources(self, html):
        """
        Process HTML to ensure all resources are properly embedded.
        
        This method can be extended to:
        - Convert external image URLs to embedded data URIs
        - Inline CSS from external stylesheets
        - Process custom directives
        
        Args:
            html (str): Rendered HTML
            
        Returns:
            str: Processed HTML with embedded resources
        """
        # For now, return HTML as-is
        # Future enhancements can add resource processing here
        return html

    def _get_printer(self, printer, document_type=None, location=None, department=None):
        """
        Get printer record using comprehensive selection algorithm.
        
        Selection algorithm (in order of priority):
        1. Check for explicitly specified printer (by ID or name)
        2. Fall back to default printer for document type
        3. Apply location/department filtering
        4. Use priority-based selection for multiple matches
        5. Fall back to system default if no match
        
        Args:
            printer (int|str|None): Printer ID, name, or None
            document_type (str): Document type for automatic selection
            location (int): Location/company ID
            department (str): Department name
            
        Returns:
            qz.printer record or False
            
        Validates: Requirements 3.4, 3.5, 4.1, 4.2, 4.3, 4.4
        """
        QZPrinter = self.env['qz.printer']
        
        # Step 1: Check for explicitly specified printer
        if printer:
            if isinstance(printer, int):
                # Printer ID provided
                printer_record = QZPrinter.browse(printer)
                if not printer_record.exists():
                    raise ValidationError(_('Printer with ID %s not found') % printer)
                if not printer_record.active:
                    raise ValidationError(_('Printer "%s" is not active') % printer_record.name)
                _logger.info(f'Using explicitly specified printer (ID): {printer_record.name}')
                return printer_record
            elif isinstance(printer, str):
                # Printer name provided
                printer_record = QZPrinter.search([
                    ('name', '=', printer),
                    ('active', '=', True)
                ], limit=1)
                if not printer_record:
                    raise ValidationError(_('Printer "%s" not found or not active') % printer)
                _logger.info(f'Using explicitly specified printer (name): {printer_record.name}')
                return printer_record
        
        # Step 2-5: Use automatic selection algorithm
        # Get user's location/company if not provided
        if location is None:
            location = self.env.user.company_id.id if self.env.user.company_id else None
        
        # Use printer model's comprehensive selection algorithm
        printer_record = QZPrinter.get_default_printer(
            printer_type=document_type,
            location_id=location,
            department=department
        )
        
        if printer_record:
            _logger.info(
                f'Selected printer via algorithm: {printer_record.name} '
                f'(type={document_type}, location={location}, dept={department})'
            )
            return printer_record
        
        # Step 6: Try to find any active printer as last resort (system default)
        fallback_printer = QZPrinter.search([('active', '=', True)], limit=1, order='priority desc')
        
        if fallback_printer:
            _logger.warning(
                f'No matching printer found, using fallback: {fallback_printer.name}'
            )
            return fallback_printer
        
        # No printer found at all
        _logger.error('No active printers available in the system')
        return False

    def _printer_supports_format(self, printer, format):
        """
        Check if a printer supports a specific format.
        
        Args:
            printer (qz.printer): Printer record
            format (str): Format to check
            
        Returns:
            bool: True if supported
        """
        format_field_map = {
            'pdf': 'supports_pdf',
            'html': 'supports_html',
            'escpos': 'supports_escpos',
            'zpl': 'supports_zpl',
        }
        
        field_name = format_field_map.get(format)
        if not field_name:
            return False
        
        return getattr(printer, field_name, False)

    def _create_print_job(self, printer_record, data, data_format, **options):
        """
        Create a print job record.
        
        Args:
            printer_record (qz.printer): Target printer
            data (bytes): Print data
            data_format (str): Data format
            **options: Additional job options
            
        Returns:
            qz.print.job record
        """
        QZPrintJob = self.env['qz.print.job']
        
        # Prepare job values
        job_values = {
            'printer_id': printer_record.id,
            'user_id': self.env.user.id,
            'state': 'draft',
            'data': base64.b64encode(data),
            'data_format': data_format,
            'document_type': options.get('document_type', 'other'),
            'copies': options.get('copies', 1),
            'priority': options.get('priority', 5),
        }
        
        # Add template information if provided
        if options.get('template_id'):
            job_values['template_id'] = options['template_id']
        if options.get('template_data'):
            job_values['template_data'] = options['template_data']
        
        # Add parent model reference if provided
        if options.get('parent_model'):
            job_values['parent_model'] = options['parent_model']
        if options.get('parent_id'):
            job_values['parent_id'] = options['parent_id']
        
        # Create the job
        job = QZPrintJob.create(job_values)
        
        _logger.info(f'Created print job {job.id} for printer {printer_record.name}')
        
        # Submit the job for processing
        job.submit_job()
        
        return job

    def _detect_label_format(self, printer):
        """
        Detect the appropriate label format for a printer.
        
        Checks printer capabilities to determine if it supports ZPL, ESC/POS, or HTML.
        
        Args:
            printer (qz.printer): Printer record
            
        Returns:
            str: Format ('zpl', 'escpos', or 'html')
            
        Validates: Requirements 6.2
        """
        # Check printer's supported formats in order of preference for labels
        # ZPL is preferred for label printers as it's most efficient
        if printer.supports_zpl:
            return 'zpl'
        elif printer.supports_escpos:
            return 'escpos'
        elif printer.supports_html:
            return 'html'
        elif printer.supports_pdf:
            return 'pdf'
        else:
            # Default to HTML as fallback
            _logger.warning(
                f'Printer {printer.name} has no explicitly supported formats, '
                f'defaulting to HTML'
            )
            return 'html'

    def _generate_zpl_label(self, label_context):
        """
        Generate ZPL (Zebra Programming Language) label data.
        
        This is a basic ZPL generator for simple labels. For complex labels,
        use QWeb templates with ZPL syntax.
        
        Args:
            label_context (dict): Label data context
            
        Returns:
            str: ZPL command string
        """
        # Extract label dimensions (convert inches to dots at 203 DPI)
        width = label_context.get('label_width', 4)
        height = label_context.get('label_height', 6)
        dpi = label_context.get('dpi', 203)
        
        width_dots = int(width * dpi)
        height_dots = int(height * dpi)
        
        # Start ZPL command
        zpl = [
            '^XA',  # Start format
            f'^PW{width_dots}',  # Print width
            f'^LL{height_dots}',  # Label length
        ]
        
        # Add product information if available
        product = label_context.get('product', {})
        if product:
            # Product name
            if product.get('name'):
                zpl.extend([
                    '^FO50,50',  # Field origin
                    '^A0N,40,40',  # Font
                    f'^FD{product["name"]}^FS',  # Field data
                ])
            
            # Product code
            if product.get('default_code'):
                zpl.extend([
                    '^FO50,100',
                    '^A0N,30,30',
                    f'^FDCode: {product["default_code"]}^FS',
                ])
            
            # Price
            if product.get('list_price'):
                zpl.extend([
                    '^FO50,150',
                    '^A0N,35,35',
                    f'^FDPrice: ${product["list_price"]:.2f}^FS',
                ])
            
            # Barcode
            if product.get('barcode'):
                barcode_type = label_context.get('barcode_type', 'Code128')
                zpl.extend([
                    '^FO50,200',
                    '^BY3',  # Bar width
                    f'^BC,100,Y,N,N',  # Code128 barcode
                    f'^FD{product["barcode"]}^FS',
                ])
        
        # Add custom barcode if specified separately
        elif label_context.get('barcode_value'):
            zpl.extend([
                '^FO50,100',
                '^BY3',
                '^BC,100,Y,N,N',
                f'^FD{label_context["barcode_value"]}^FS',
            ])
        
        # End format
        zpl.append('^XZ')
        
        return '\n'.join(zpl)

    def _generate_escpos_label(self, label_context):
        """
        Generate ESC/POS label data.
        
        This is a basic ESC/POS generator for simple labels. For complex labels,
        use QWeb templates with ESC/POS commands.
        
        Args:
            label_context (dict): Label data context
            
        Returns:
            str: ESC/POS command string
        """
        # ESC/POS commands
        ESC = '\x1b'
        GS = '\x1d'
        
        commands = []
        
        # Initialize printer
        commands.append(f'{ESC}@')  # Initialize
        commands.append(f'{ESC}a\x01')  # Center alignment
        
        # Add product information if available
        product = label_context.get('product', {})
        if product:
            # Product name (large text)
            if product.get('name'):
                commands.append(f'{ESC}!\x30')  # Double height and width
                commands.append(product['name'])
                commands.append('\n')
                commands.append(f'{ESC}!\x00')  # Normal text
            
            # Product code
            if product.get('default_code'):
                commands.append(f'Code: {product["default_code"]}\n')
            
            # Price
            if product.get('list_price'):
                commands.append(f'{ESC}!\x20')  # Double height
                commands.append(f'Price: ${product["list_price"]:.2f}\n')
                commands.append(f'{ESC}!\x00')  # Normal text
            
            # Barcode (if supported)
            if product.get('barcode'):
                commands.append('\n')
                # Note: Barcode printing in ESC/POS varies by printer model
                # This is a basic implementation
                commands.append(f'{GS}k\x49')  # CODE128
                commands.append(f'{chr(len(product["barcode"]))}')
                commands.append(product['barcode'])
        
        # Add custom barcode if specified separately
        elif label_context.get('barcode_value'):
            barcode = label_context['barcode_value']
            commands.append(f'{GS}k\x49')
            commands.append(f'{chr(len(barcode))}')
            commands.append(barcode)
        
        # Feed and cut
        commands.append('\n\n\n')
        commands.append(f'{GS}V\x00')  # Full cut
        
        return ''.join(commands)
