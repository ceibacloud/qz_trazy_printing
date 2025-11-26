# QZ Tray Print Integration

Centralized printing service for Odoo 18 with QZ Tray integration.

## Features

- Certificate-based authentication with QZ Tray
- Support for multiple print formats (PDF, HTML, ESC/POS, ZPL)
- Automatic printer selection based on document type and location
- Print job queuing and retry handling
- Template-based document printing using QWeb
- Print job monitoring and history
- Receipt and label printing integration
- Preview documents before printing

## Requirements

- Odoo 18.0
- QZ Tray installed on client machines
- Digital certificates for QZ Tray authentication

## Installation

1. Copy this module to your Odoo addons directory
2. Update the apps list in Odoo
3. Install the "QZ Tray Print Integration" module

## Configuration

1. Navigate to Settings > QZ Tray Print Configuration
2. Upload your QZ Tray certificate and private key
3. Test the connection to QZ Tray
4. Configure printers in the Printer Management interface
5. Set default printers for each document type

## Usage

### For Developers

Integrate printing into your module by inheriting from `qz.print.service`:

```python
from odoo import models

class MyModel(models.Model):
    _name = 'my.model'
    _inherit = ['qz.print.service']
    
    def print_my_document(self):
        self.print_document(
            template='my_module.my_template',
            data={'record': self},
            document_type='my_document'
        )
```

### For Users

- Submit print jobs from any integrated module
- Monitor print job status in the Print Job Monitor
- View print history and retry failed jobs
- Configure printer preferences

## Security

Three security groups are provided:

- **Print User**: Can submit print jobs and view own job history
- **Print Manager**: Can configure printers and view all jobs for their location
- **Print Administrator**: Full access including certificate configuration

## Support

For issues and questions, please contact your system administrator.

## License

LGPL-3

## Author

Your Company
