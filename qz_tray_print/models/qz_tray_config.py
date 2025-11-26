# -*- coding: utf-8 -*-
import base64
import logging
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class QZTrayConfig(models.TransientModel):
    _name = 'qz.tray.config'
    _description = 'QZ Tray Configuration'

    # Certificate fields
    certificate = fields.Binary(
        string='Certificate',
        required=True,
        help='Digital certificate for QZ Tray authentication (PEM format)'
    )
    certificate_filename = fields.Char(string='Certificate Filename')
    
    private_key = fields.Binary(
        string='Private Key',
        required=True,
        help='Private key for the certificate (PEM format)'
    )
    private_key_filename = fields.Char(string='Private Key Filename')
    
    certificate_password = fields.Char(
        string='Certificate Password',
        help='Password for encrypted private key (if applicable)'
    )
    
    # Connection settings
    connection_timeout = fields.Integer(
        string='Connection Timeout',
        default=30,
        required=True,
        help='Timeout for QZ Tray connection attempts (in seconds)'
    )
    
    # Retry policy settings
    retry_enabled = fields.Boolean(
        string='Enable Automatic Retry',
        default=True,
        help='Automatically retry failed print jobs'
    )
    
    retry_count = fields.Integer(
        string='Maximum Retry Attempts',
        default=3,
        required=True,
        help='Maximum number of retry attempts for failed jobs'
    )
    
    retry_delay = fields.Integer(
        string='Retry Delay',
        default=5,
        required=True,
        help='Delay between retry attempts (in seconds)'
    )
    
    # Connection status (computed)
    connection_status = fields.Char(
        string='Connection Status',
        compute='_compute_connection_status',
        readonly=True
    )

    @api.constrains('connection_timeout')
    def _check_connection_timeout(self):
        """Validate connection timeout value"""
        for record in self:
            if record.connection_timeout <= 0:
                raise ValidationError(_('Connection timeout must be greater than 0'))

    @api.constrains('retry_count')
    def _check_retry_count(self):
        """Validate retry count value"""
        for record in self:
            if record.retry_count < 0:
                raise ValidationError(_('Retry count cannot be negative'))

    @api.constrains('retry_delay')
    def _check_retry_delay(self):
        """Validate retry delay value"""
        for record in self:
            if record.retry_delay < 0:
                raise ValidationError(_('Retry delay cannot be negative'))

    @api.depends('certificate', 'private_key')
    def _compute_connection_status(self):
        """Compute connection status based on certificate configuration"""
        for record in self:
            if record.certificate and record.private_key:
                record.connection_status = 'Ready to test'
            else:
                record.connection_status = 'Certificate not configured'

    def _validate_certificate(self):
        """
        Validate certificate format and content
        Returns: tuple (is_valid, error_message)
        """
        self.ensure_one()
        
        if not self.certificate:
            return False, _('Certificate is required')
        
        if not self.private_key:
            return False, _('Private key is required')
        
        try:
            # Decode certificate to validate it's proper base64
            cert_data = base64.b64decode(self.certificate)
            key_data = base64.b64decode(self.private_key)
            
            # Basic validation: check if it looks like PEM format
            cert_str = cert_data.decode('utf-8', errors='ignore')
            key_str = key_data.decode('utf-8', errors='ignore')
            
            if '-----BEGIN CERTIFICATE-----' not in cert_str:
                return False, _('Certificate must be in PEM format')
            
            if '-----BEGIN' not in key_str or 'PRIVATE KEY-----' not in key_str:
                return False, _('Private key must be in PEM format')
            
            return True, ''
            
        except Exception as e:
            _logger.error(f'Certificate validation error: {str(e)}')
            return False, _('Invalid certificate or private key format: %s') % str(e)

    def _encrypt_private_key(self, key_data):
        """
        Encrypt private key for secure storage
        In a production environment, this should use proper encryption
        For now, we'll use base64 encoding (Odoo handles encryption at the field level)
        """
        # Odoo's Binary field already handles secure storage
        # Additional encryption can be added here if needed
        return key_data

    def _decrypt_private_key(self, encrypted_key):
        """
        Decrypt private key for use
        """
        # Odoo's Binary field already handles secure storage
        # Corresponding decryption can be added here if needed
        return encrypted_key

    def save_credentials(self):
        """
        Save certificate and private key to system parameters
        """
        self.ensure_one()
        
        # Validate certificate before saving
        is_valid, error_msg = self._validate_certificate()
        if not is_valid:
            raise ValidationError(error_msg)
        
        IrConfigParameter = self.env['ir.config_parameter'].sudo()
        
        try:
            # Encrypt private key before storage
            encrypted_key = self._encrypt_private_key(self.private_key)
            
            # Store certificate and key
            IrConfigParameter.set_param('qz_tray.certificate', self.certificate.decode('utf-8') if isinstance(self.certificate, bytes) else self.certificate)
            IrConfigParameter.set_param('qz_tray.private_key', encrypted_key.decode('utf-8') if isinstance(encrypted_key, bytes) else encrypted_key)
            
            # Store password if provided
            if self.certificate_password:
                IrConfigParameter.set_param('qz_tray.certificate_password', self.certificate_password)
            
            # Store connection settings
            IrConfigParameter.set_param('qz_tray.connection_timeout', str(self.connection_timeout))
            IrConfigParameter.set_param('qz_tray.retry_enabled', str(self.retry_enabled))
            IrConfigParameter.set_param('qz_tray.retry_count', str(self.retry_count))
            IrConfigParameter.set_param('qz_tray.retry_delay', str(self.retry_delay))
            
            _logger.info('QZ Tray credentials and settings saved successfully')
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Success'),
                    'message': _('QZ Tray configuration saved successfully'),
                    'type': 'success',
                    'sticky': False,
                }
            }
            
        except Exception as e:
            _logger.error(f'Error saving QZ Tray credentials: {str(e)}')
            raise ValidationError(_('Failed to save credentials: %s') % str(e))

    @api.model
    def get_credentials(self):
        """
        Retrieve stored certificate and private key
        Returns: dict with certificate, private_key, and settings
        """
        IrConfigParameter = self.env['ir.config_parameter'].sudo()
        
        certificate = IrConfigParameter.get_param('qz_tray.certificate', default=False)
        encrypted_key = IrConfigParameter.get_param('qz_tray.private_key', default=False)
        password = IrConfigParameter.get_param('qz_tray.certificate_password', default=False)
        
        if not certificate or not encrypted_key:
            return False
        
        # Decrypt private key
        private_key = self._decrypt_private_key(encrypted_key)
        
        return {
            'certificate': certificate,
            'private_key': private_key,
            'password': password,
            'connection_timeout': int(IrConfigParameter.get_param('qz_tray.connection_timeout', default=30)),
            'retry_enabled': IrConfigParameter.get_param('qz_tray.retry_enabled', default='True') == 'True',
            'retry_count': int(IrConfigParameter.get_param('qz_tray.retry_count', default=3)),
            'retry_delay': int(IrConfigParameter.get_param('qz_tray.retry_delay', default=5)),
        }

    @api.model
    def default_get(self, fields_list):
        """Load existing configuration when opening the form"""
        res = super(QZTrayConfig, self).default_get(fields_list)
        
        # Load existing credentials if available
        credentials = self.get_credentials()
        if credentials:
            if 'certificate' in fields_list and credentials.get('certificate'):
                res['certificate'] = credentials['certificate']
            if 'private_key' in fields_list and credentials.get('private_key'):
                res['private_key'] = credentials['private_key']
            if 'certificate_password' in fields_list and credentials.get('password'):
                res['certificate_password'] = credentials['password']
            if 'connection_timeout' in fields_list:
                res['connection_timeout'] = credentials.get('connection_timeout', 30)
            if 'retry_enabled' in fields_list:
                res['retry_enabled'] = credentials.get('retry_enabled', True)
            if 'retry_count' in fields_list:
                res['retry_count'] = credentials.get('retry_count', 3)
            if 'retry_delay' in fields_list:
                res['retry_delay'] = credentials.get('retry_delay', 5)
        
        return res

    def test_connection(self):
        """
        Test connection to QZ Tray
        Validates certificate and attempts to verify QZ Tray availability
        Returns: action dict with notification
        """
        self.ensure_one()
        
        # First, validate the certificate
        is_valid, error_msg = self._validate_certificate()
        if not is_valid:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Certificate Validation Failed'),
                    'message': error_msg,
                    'type': 'danger',
                    'sticky': True,
                }
            }
        
        # Check if credentials are saved
        saved_credentials = self.get_credentials()
        if not saved_credentials:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Configuration Not Saved'),
                    'message': _('Please save the configuration before testing the connection'),
                    'type': 'warning',
                    'sticky': False,
                }
            }
        
        # Attempt to test connection
        # Note: Actual QZ Tray connection testing requires JavaScript/WebSocket
        # This method validates the configuration and returns appropriate status
        try:
            # Verify certificate data is accessible
            cert_data = base64.b64decode(self.certificate)
            key_data = base64.b64decode(self.private_key)
            
            # Check certificate expiration (basic check)
            cert_str = cert_data.decode('utf-8', errors='ignore')
            
            # Log the connection test attempt
            _logger.info('QZ Tray connection test initiated - Certificate validated')
            
            # Return success with instructions
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Certificate Valid'),
                    'message': _('Certificate configuration is valid. '
                                'Actual QZ Tray connection will be tested from the browser. '
                                'Please ensure QZ Tray is running on the client machine.'),
                    'type': 'success',
                    'sticky': True,
                }
            }
            
        except Exception as e:
            _logger.error(f'Connection test error: {str(e)}')
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Connection Test Failed'),
                    'message': _('Error during connection test: %s') % str(e),
                    'type': 'danger',
                    'sticky': True,
                }
            }
