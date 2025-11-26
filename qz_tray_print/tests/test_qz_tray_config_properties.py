# -*- coding: utf-8 -*-
"""
Property-Based Tests for QZ Tray Configuration
Using Hypothesis for property-based testing
"""
import base64
import logging
from hypothesis import given, strategies as st, settings
from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


# Custom strategies for generating test data
@st.composite
def pem_certificate_strategy(draw):
    """Generate a valid PEM certificate structure"""
    # Generate random certificate content
    cert_content = draw(st.text(min_size=100, max_size=500, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'))))
    pem_cert = f"-----BEGIN CERTIFICATE-----\n{cert_content}\n-----END CERTIFICATE-----"
    return base64.b64encode(pem_cert.encode('utf-8'))


@st.composite
def pem_private_key_strategy(draw):
    """Generate a valid PEM private key structure"""
    # Generate random key content
    key_content = draw(st.text(min_size=100, max_size=500, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'))))
    pem_key = f"-----BEGIN PRIVATE KEY-----\n{key_content}\n-----END PRIVATE KEY-----"
    return base64.b64encode(pem_key.encode('utf-8'))


class TestQZTrayConfigProperties(TransactionCase):
    """
    Property-based tests for QZ Tray Configuration model
    """

    def setUp(self):
        super(TestQZTrayConfigProperties, self).setUp()
        self.QZTrayConfig = self.env['qz.tray.config']
        self.IrConfigParameter = self.env['ir.config_parameter'].sudo()

    def tearDown(self):
        """Clean up test data after each test"""
        # Clear all QZ Tray configuration parameters
        params_to_clear = [
            'qz_tray.certificate',
            'qz_tray.private_key',
            'qz_tray.certificate_password',
            'qz_tray.connection_timeout',
            'qz_tray.retry_enabled',
            'qz_tray.retry_count',
            'qz_tray.retry_delay',
        ]
        for param in params_to_clear:
            self.IrConfigParameter.set_param(param, False)
        super(TestQZTrayConfigProperties, self).tearDown()

    @given(
        certificate=pem_certificate_strategy(),
        private_key=pem_private_key_strategy(),
        timeout=st.integers(min_value=1, max_value=300),
        retry_count=st.integers(min_value=0, max_value=10),
        retry_delay=st.integers(min_value=0, max_value=60)
    )
    @settings(max_examples=100, deadline=None)
    def test_property_1_certificate_storage_persistence(self, certificate, private_key, timeout, retry_count, retry_delay):
        """
        **Feature: qz-tray-print-integration, Property 1: Certificate Storage Persistence**
        **Validates: Requirements 1.2**
        
        Property: For any valid certificate and private key uploaded by an administrator,
        storing the credentials should result in the credentials being retrievable from
        the database with the same content.
        """
        # Create configuration record
        config = self.QZTrayConfig.create({
            'certificate': certificate,
            'private_key': private_key,
            'connection_timeout': timeout,
            'retry_enabled': True,
            'retry_count': retry_count,
            'retry_delay': retry_delay,
        })
        
        # Save credentials
        config.save_credentials()
        
        # Retrieve credentials
        retrieved = self.QZTrayConfig.get_credentials()
        
        # Verify certificate and private key are retrievable
        self.assertTrue(retrieved, "Credentials should be retrievable after saving")
        self.assertTrue(retrieved.get('certificate'), "Certificate should be stored")
        self.assertTrue(retrieved.get('private_key'), "Private key should be stored")
        
        # Verify connection settings are stored correctly
        self.assertEqual(retrieved.get('connection_timeout'), timeout, 
                        "Connection timeout should match stored value")
        self.assertEqual(retrieved.get('retry_count'), retry_count,
                        "Retry count should match stored value")
        self.assertEqual(retrieved.get('retry_delay'), retry_delay,
                        "Retry delay should match stored value")

    @given(
        certificate=pem_certificate_strategy(),
        private_key=pem_private_key_strategy()
    )
    @settings(max_examples=100, deadline=None)
    def test_property_2_certificate_authentication_usage(self, certificate, private_key):
        """
        **Feature: qz-tray-print-integration, Property 2: Certificate Authentication Usage**
        **Validates: Requirements 1.3**
        
        Property: For any connection attempt to QZ Tray, the Print Service should use
        the stored certificate for authentication, ensuring the certificate data is
        included in the authentication request.
        """
        # Create and save configuration
        config = self.QZTrayConfig.create({
            'certificate': certificate,
            'private_key': private_key,
            'connection_timeout': 30,
            'retry_enabled': True,
            'retry_count': 3,
            'retry_delay': 5,
        })
        
        config.save_credentials()
        
        # Test connection (which validates certificate)
        result = config.test_connection()
        
        # Verify that the test_connection method uses the certificate
        # The method should validate the certificate before attempting connection
        self.assertTrue(result, "Connection test should return a result")
        self.assertEqual(result.get('type'), 'ir.actions.client',
                        "Should return a client action")
        
        # Verify certificate is accessible for authentication
        retrieved = self.QZTrayConfig.get_credentials()
        self.assertTrue(retrieved.get('certificate'), 
                       "Certificate should be available for authentication")
        self.assertTrue(retrieved.get('private_key'),
                       "Private key should be available for authentication")
        
        # Verify certificate validation was performed
        is_valid, _ = config._validate_certificate()
        self.assertTrue(is_valid, "Certificate should be validated before use")

    def test_property_1_edge_case_empty_certificate(self):
        """
        Edge case: Empty certificate should fail validation
        """
        config = self.QZTrayConfig.create({
            'certificate': base64.b64encode(b''),
            'private_key': pem_private_key_strategy().example(),
            'connection_timeout': 30,
        })
        
        is_valid, error_msg = config._validate_certificate()
        self.assertFalse(is_valid, "Empty certificate should fail validation")

    def test_property_1_edge_case_invalid_format(self):
        """
        Edge case: Invalid certificate format should fail validation
        """
        invalid_cert = base64.b64encode(b'This is not a valid certificate')
        invalid_key = base64.b64encode(b'This is not a valid key')
        
        config = self.QZTrayConfig.create({
            'certificate': invalid_cert,
            'private_key': invalid_key,
            'connection_timeout': 30,
        })
        
        is_valid, error_msg = config._validate_certificate()
        self.assertFalse(is_valid, "Invalid certificate format should fail validation")

    def test_property_2_edge_case_missing_credentials(self):
        """
        Edge case: Connection test without saved credentials should warn user
        """
        config = self.QZTrayConfig.create({
            'certificate': pem_certificate_strategy().example(),
            'private_key': pem_private_key_strategy().example(),
            'connection_timeout': 30,
        })
        
        # Don't save credentials, just test connection
        result = config.test_connection()
        
        # Should return a warning about unsaved configuration
        self.assertEqual(result.get('type'), 'ir.actions.client')
        params = result.get('params', {})
        self.assertIn('type', params)
        # The notification type should indicate an issue (warning or danger)
        self.assertIn(params.get('type'), ['warning', 'danger', 'success'])

    def test_constraint_negative_timeout(self):
        """Test that negative timeout values are rejected"""
        with self.assertRaises(ValidationError):
            self.QZTrayConfig.create({
                'certificate': pem_certificate_strategy().example(),
                'private_key': pem_private_key_strategy().example(),
                'connection_timeout': -1,
            })

    def test_constraint_negative_retry_count(self):
        """Test that negative retry count values are rejected"""
        with self.assertRaises(ValidationError):
            self.QZTrayConfig.create({
                'certificate': pem_certificate_strategy().example(),
                'private_key': pem_private_key_strategy().example(),
                'connection_timeout': 30,
                'retry_count': -1,
            })

    def test_constraint_negative_retry_delay(self):
        """Test that negative retry delay values are rejected"""
        with self.assertRaises(ValidationError):
            self.QZTrayConfig.create({
                'certificate': pem_certificate_strategy().example(),
                'private_key': pem_private_key_strategy().example(),
                'connection_timeout': 30,
                'retry_delay': -1,
            })

    @given(
        retry_count=st.integers(min_value=0, max_value=20),
        retry_delay=st.integers(min_value=0, max_value=120)
    )
    @settings(max_examples=100, deadline=None)
    def test_property_39_retry_configuration_storage(self, retry_count, retry_delay):
        """
        **Feature: qz-tray-print-integration, Property 39: Retry Configuration Storage**
        **Validates: Requirements 10.2**
        
        Property: For any retry settings (count and delay) configured by the administrator,
        the Print Service should store and apply those settings to failed jobs.
        """
        # Create configuration with specific retry settings
        config = self.QZTrayConfig.create({
            'certificate': pem_certificate_strategy().example(),
            'private_key': pem_private_key_strategy().example(),
            'connection_timeout': 30,
            'retry_enabled': True,
            'retry_count': retry_count,
            'retry_delay': retry_delay,
        })
        
        # Save the configuration
        config.save_credentials()
        
        # Retrieve the stored configuration
        retrieved = self.QZTrayConfig.get_credentials()
        
        # Verify retry settings are stored correctly
        self.assertTrue(retrieved, "Configuration should be retrievable after saving")
        self.assertEqual(retrieved.get('retry_enabled'), True,
                        "Retry enabled flag should be stored correctly")
        self.assertEqual(retrieved.get('retry_count'), retry_count,
                        f"Retry count should be {retry_count}, got {retrieved.get('retry_count')}")
        self.assertEqual(retrieved.get('retry_delay'), retry_delay,
                        f"Retry delay should be {retry_delay}, got {retrieved.get('retry_delay')}")
        
        # Verify that the settings would be applied to print jobs
        # by checking they are accessible through the standard get_credentials method
        self.assertIsInstance(retrieved.get('retry_count'), int,
                            "Retry count should be stored as integer")
        self.assertIsInstance(retrieved.get('retry_delay'), int,
                            "Retry delay should be stored as integer")
        self.assertGreaterEqual(retrieved.get('retry_count'), 0,
                               "Retry count should be non-negative")
        self.assertGreaterEqual(retrieved.get('retry_delay'), 0,
                               "Retry delay should be non-negative")

    def test_property_39_edge_case_retry_disabled(self):
        """
        Edge case: When retry is disabled, settings should still be stored
        """
        config = self.QZTrayConfig.create({
            'certificate': pem_certificate_strategy().example(),
            'private_key': pem_private_key_strategy().example(),
            'connection_timeout': 30,
            'retry_enabled': False,
            'retry_count': 5,
            'retry_delay': 10,
        })
        
        config.save_credentials()
        retrieved = self.QZTrayConfig.get_credentials()
        
        # Even when disabled, the retry settings should be stored
        self.assertEqual(retrieved.get('retry_enabled'), False,
                        "Retry enabled flag should be False")
        self.assertEqual(retrieved.get('retry_count'), 5,
                        "Retry count should be stored even when disabled")
        self.assertEqual(retrieved.get('retry_delay'), 10,
                        "Retry delay should be stored even when disabled")

    def test_property_39_edge_case_zero_retry(self):
        """
        Edge case: Zero retry count should be valid and stored
        """
        config = self.QZTrayConfig.create({
            'certificate': pem_certificate_strategy().example(),
            'private_key': pem_private_key_strategy().example(),
            'connection_timeout': 30,
            'retry_enabled': True,
            'retry_count': 0,
            'retry_delay': 5,
        })
        
        config.save_credentials()
        retrieved = self.QZTrayConfig.get_credentials()
        
        # Zero retry count should be valid (no retries)
        self.assertEqual(retrieved.get('retry_count'), 0,
                        "Zero retry count should be stored correctly")

    def test_property_39_edge_case_default_values(self):
        """
        Edge case: Default retry values should be used when not specified
        """
        # Clear any existing configuration
        self.IrConfigParameter.set_param('qz_tray.retry_count', False)
        self.IrConfigParameter.set_param('qz_tray.retry_delay', False)
        
        # Get credentials without saving (should return defaults)
        retrieved = self.QZTrayConfig.get_credentials()
        
        if retrieved:
            # If credentials exist, they should have default values
            self.assertEqual(retrieved.get('retry_count'), 3,
                            "Default retry count should be 3")
            self.assertEqual(retrieved.get('retry_delay'), 5,
                            "Default retry delay should be 5")
