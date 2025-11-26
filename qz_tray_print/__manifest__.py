# -*- coding: utf-8 -*-
{
    'name': 'QZ Tray Print Integration',
    'version': '18.0.1.0.0',
    'category': 'Tools',
    'summary': 'Centralized printing service for Odoo 18 with QZ Tray integration',
    'description': """
QZ Tray Print Integration
==========================

This module provides a centralized printing service for Odoo 18 that integrates 
with QZ Tray to enable seamless communication with local printers.

Features:
---------
* Certificate-based authentication with QZ Tray
* Support for multiple print formats (PDF, HTML, ESC/POS, ZPL)
* Automatic printer selection based on document type and location
* Print job queuing and retry handling
* Template-based document printing using QWeb
* Print job monitoring and history
* Receipt and label printing integration
* Preview documents before printing

Requirements:
-------------
* QZ Tray must be installed on client machines
* Digital certificates for QZ Tray authentication
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'web',
        'mail',
        'product',
    ],
    'data': [
        # Security
        'security/qz_tray_security.xml',
        'security/ir.model.access.csv',
        
        # Data
        'data/system_parameters.xml',
        'data/ir_cron_data.xml',
        'data/email_templates.xml',
        
        # Views
        'views/qz_tray_config_views.xml',
        'views/qz_printer_views.xml',
        'views/qz_print_job_views.xml',
        'views/qz_print_template_views.xml',
        'views/print_templates.xml',
        'views/pos_order_views.xml',
        'views/product_product_views.xml',
        'views/qz_tray_menus.xml',
    ],
    'assets': {
        'web.assets_backend': [
            # JavaScript Services
            'qz_tray_print/static/src/services/qz_connector.js',
            'qz_tray_print/static/src/services/print_service.js',
            
            # Client Actions
            'qz_tray_print/static/src/actions/qz_client_actions.js',
            
            # OWL Components
            'qz_tray_print/static/src/components/**/*.js',
            'qz_tray_print/static/src/components/**/*.xml',
            
            # Stylesheets
            'qz_tray_print/static/src/css/qz_tray_print.css',
        ],
        'web.assets_frontend': [
            # Frontend assets if needed
        ],
    },
    'demo': [],
    'installable': True,
    'application': False,
    'auto_install': False,
}
