# QZ Tray Print Integration - OWL Components

This directory contains the OWL 2 components for the QZ Tray Print Integration module.

## Components

### 1. Printer Selector Dialog (`printer_selector/`)

A modal dialog component that displays a list of available printers for user selection.

**Features:**
- Displays printer name, type, system name, and location
- Highlights default printers with a badge
- Visual feedback for selected printer
- Confirm and cancel actions
- Responsive design with Bootstrap styling

**Usage:**
```javascript
import { PrinterSelectorDialog } from "@qz_tray_print/components/printer_selector/printer_selector";

dialog.add(PrinterSelectorDialog, {
    printers: availablePrinters,
    title: "Select Printer",
}, {
    onClose: (selectedPrinter) => {
        // Handle printer selection
    },
});
```

**Props:**
- `printers` (Array): List of printer objects
- `title` (String, optional): Dialog title
- `close` (Function): Callback function when dialog closes

### 2. Print Preview Dialog (`print_preview/`)

A modal dialog component for previewing documents before printing.

**Features:**
- Supports PDF and HTML preview formats
- Embedded PDF viewer for PDF documents
- Direct HTML rendering for HTML documents
- Loading state indicator
- Error handling with user-friendly messages
- Print and cancel actions

**Usage:**
```javascript
import { PrintPreviewDialog } from "@qz_tray_print/components/print_preview/print_preview";

dialog.add(PrintPreviewDialog, {
    previewData: base64Data,
    previewFormat: 'pdf', // or 'html'
    title: "Preview Document",
}, {
    onClose: (result) => {
        if (result.action === 'print') {
            // Proceed with printing
        }
    },
});
```

**Props:**
- `previewData` (String): Base64-encoded PDF or HTML string
- `previewFormat` (String): Format type ('pdf' or 'html')
- `title` (String, optional): Dialog title
- `close` (Function): Callback function when dialog closes

### 3. Print Job Monitor (`print_monitor/`)

A full-page component for monitoring and managing print jobs.

**Features:**
- Real-time job status updates (auto-refresh every 5 seconds)
- Advanced filtering by date, user, printer, and status
- Job actions: retry, cancel, resubmit
- Color-coded status badges
- Detailed error messages for failed jobs
- Responsive table layout
- Registered as a client action

**Usage:**

The component is registered as a client action and can be opened via:

```xml
<record id="action_print_job_monitor" model="ir.actions.client">
    <field name="name">Print Job Monitor</field>
    <field name="tag">qz_tray_print.print_monitor</field>
</record>
```

Or programmatically:
```javascript
this.action.doAction({
    type: 'ir.actions.client',
    tag: 'qz_tray_print.print_monitor',
});
```

**Features:**
- Filter by date range, user, printer, and status
- View job details including timestamps and error messages
- Retry failed jobs
- Cancel queued/draft jobs
- Resubmit completed/failed/cancelled jobs

## Integration with Print Service

The components are integrated with the print service (`print_service.js`):

1. **Printer Selector**: Used by `selectPrinter()` method when no default printer is configured
2. **Print Preview**: Can be used by consumer modules to preview documents before printing
3. **Print Monitor**: Standalone component for administrators to monitor all print jobs

## Styling

All components use consistent styling defined in `qz_tray_print/static/src/css/qz_tray_print.css`:

- Bootstrap 5 classes for layout and components
- Custom CSS for component-specific styling
- Responsive design for mobile and desktop
- Consistent color scheme with Odoo UI

## Asset Registration

All components are automatically registered in the `web.assets_backend` bundle via the module manifest:

```python
'assets': {
    'web.assets_backend': [
        'qz_tray_print/static/src/components/**/*.js',
        'qz_tray_print/static/src/components/**/*.xml',
        'qz_tray_print/static/src/css/qz_tray_print.css',
    ],
}
```

## Requirements Validation

These components fulfill the following requirements:

- **Requirement 4.5**: Printer selection dialog for user to choose printer
- **Requirement 7.4**: Print job monitoring and history viewing
- **Requirement 11.1-11.5**: Document preview functionality
- **Requirement 12.1, 12.3, 12.5**: Print queue management with retry, cancel, and resubmit actions

## Technical Notes

- All components use OWL 2 framework
- Components follow Odoo 18 best practices
- Proper use of hooks: `useState`, `onMounted`, `onWillStart`, `onWillUnmount`, `useRef`
- Service dependencies injected via `useService` hook
- Dialog components use the standard Odoo Dialog component
- Proper error handling and user notifications
