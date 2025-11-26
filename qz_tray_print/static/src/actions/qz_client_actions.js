/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component } from "@odoo/owl";

/**
 * Client Action: Discover Printers
 * Connects to QZ Tray, retrieves available printers, and syncs with backend
 */
async function qzDiscoverPrinters(env, action) {
    const qzConnector = env.services.qz_connector;
    const rpc = env.services.rpc;
    const notification = env.services.notification;
    
    try {
        // Connect to QZ Tray
        notification.add('Connecting to QZ Tray...', {
            type: 'info',
        });
        
        const connected = await qzConnector.connect();
        if (!connected) {
            throw new Error('Failed to connect to QZ Tray');
        }
        
        // Get available printers from QZ Tray
        notification.add('Discovering printers...', {
            type: 'info',
        });
        
        const printers = await qzConnector.getPrinters();
        
        if (!printers || printers.length === 0) {
            notification.add('No printers found', {
                type: 'warning',
            });
            return;
        }
        
        // Sync discovered printers with backend
        const result = await rpc('/qz_tray/printers/sync', {
            printers: printers,
        });
        
        if (result.error) {
            throw new Error(result.error);
        }
        
        // Display success notification with results
        const newCount = result.new_count || 0;
        const updatedCount = result.updated_count || 0;
        const totalCount = printers.length;
        
        notification.add(
            `Printer discovery complete: ${totalCount} printers found (${newCount} new, ${updatedCount} updated)`,
            {
                type: 'success',
            }
        );
        
        // Reload the printer list view if we're in one
        if (action.context && action.context.reload_view) {
            env.services.action.doAction('reload');
        }
        
    } catch (error) {
        notification.add(`Printer discovery failed: ${error.message}`, {
            type: 'danger',
        });
        console.error('Printer discovery error:', error);
    }
}

/**
 * Client Action: Test Print
 * Sends a test page to the specified printer
 */
async function qzTestPrint(env, action) {
    const qzConnector = env.services.qz_connector;
    const rpc = env.services.rpc;
    const notification = env.services.notification;
    
    try {
        // Get printer_id from context
        const printerId = action.context && action.context.printer_id;
        
        if (!printerId) {
            throw new Error('No printer specified for test print');
        }
        
        // Get printer details from backend
        const printerResult = await rpc(`/qz_tray/printer/${printerId}`, {});
        
        if (printerResult.error || !printerResult.printer) {
            throw new Error(printerResult.error || 'Printer not found');
        }
        
        const printer = printerResult.printer;
        
        // Connect to QZ Tray
        const connected = await qzConnector.connect();
        if (!connected) {
            throw new Error('Failed to connect to QZ Tray');
        }
        
        // Generate test page content
        const now = new Date();
        const dateTimeStr = now.toLocaleString();
        
        const testPageContent = `
            <html>
            <head>
                <style>
                    body {
                        font-family: Arial, sans-serif;
                        padding: 20px;
                    }
                    h1 {
                        color: #333;
                        border-bottom: 2px solid #875A7B;
                        padding-bottom: 10px;
                    }
                    .info {
                        margin: 20px 0;
                        line-height: 1.6;
                    }
                    .test-pattern {
                        margin-top: 30px;
                        padding: 20px;
                        border: 1px solid #ccc;
                        background-color: #f9f9f9;
                    }
                    .pattern-line {
                        font-family: monospace;
                        font-size: 12px;
                    }
                </style>
            </head>
            <body>
                <h1>QZ Tray Test Page</h1>
                <div class="info">
                    <p><strong>Printer:</strong> ${printer.name}</p>
                    <p><strong>System Name:</strong> ${printer.system_name || 'N/A'}</p>
                    <p><strong>Type:</strong> ${printer.printer_type || 'N/A'}</p>
                    <p><strong>Date/Time:</strong> ${dateTimeStr}</p>
                </div>
                <div class="test-pattern">
                    <h2>Test Pattern</h2>
                    <div class="pattern-line">ABCDEFGHIJKLMNOPQRSTUVWXYZ</div>
                    <div class="pattern-line">abcdefghijklmnopqrstuvwxyz</div>
                    <div class="pattern-line">0123456789 !@#$%^&*()</div>
                    <div class="pattern-line">████████████████████████████</div>
                    <div class="pattern-line">▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓</div>
                    <div class="pattern-line">░░░░░░░░░░░░░░░░░░░░░░░░░░░░</div>
                </div>
            </body>
            </html>
        `;
        
        // Send test page to printer
        notification.add('Sending test page to printer...', {
            type: 'info',
        });
        
        await qzConnector.print({
            printer: printer.system_name || printer.name,
            data: testPageContent,
            format: 'html',
            options: {},
        });
        
        notification.add(`Test page sent successfully to ${printer.name}`, {
            type: 'success',
        });
        
    } catch (error) {
        notification.add(`Test print failed: ${error.message}`, {
            type: 'danger',
        });
        console.error('Test print error:', error);
    }
}

/**
 * Client Action: Print Preview
 * Opens the print preview dialog with the provided preview data
 */
async function qzPrintPreview(env, action) {
    const dialog = env.services.dialog;
    const notification = env.services.notification;
    const rpc = env.services.rpc;
    
    try {
        // Get preview data from context
        const previewData = action.context && action.context.preview_data;
        const previewFormat = action.context && action.context.preview_format || 'html';
        const printCallback = action.context && action.context.print_callback;
        const recordId = action.context && action.context.record_id;
        
        if (!previewData) {
            throw new Error('No preview data provided');
        }
        
        // Dynamically import the print preview dialog component
        const { PrintPreviewDialog } = await import(
            "@qz_tray_print/components/print_preview/print_preview"
        );
        
        // Show print preview dialog
        dialog.add(PrintPreviewDialog, {
            previewData: previewData,
            previewFormat: previewFormat,
            title: 'Print Preview',
        }, {
            onClose: async (result) => {
                if (result && result.action === 'print') {
                    // User approved the preview, proceed with printing
                    if (printCallback && recordId) {
                        try {
                            // Call the backend method to confirm and print
                            const printResult = await rpc('/web/dataset/call_kw', {
                                model: printCallback.split('.')[0] + '.' + printCallback.split('.')[1],
                                method: printCallback.split('.')[2] || 'confirm_print',
                                args: [[recordId]],
                                kwargs: {},
                            });
                            
                            if (printResult && printResult.error) {
                                throw new Error(printResult.error);
                            }
                            
                            notification.add('Print job submitted', {
                                type: 'success',
                            });
                        } catch (error) {
                            notification.add(`Print failed: ${error.message}`, {
                                type: 'danger',
                            });
                        }
                    } else {
                        notification.add('Print approved', {
                            type: 'info',
                        });
                    }
                } else {
                    // User cancelled the preview
                    notification.add('Print cancelled', {
                        type: 'info',
                    });
                }
            },
        });
        
    } catch (error) {
        notification.add(`Preview failed: ${error.message}`, {
            type: 'danger',
        });
        console.error('Print preview error:', error);
    }
}

// Register client actions in the actions registry
registry.category("actions").add("qz_discover_printers", qzDiscoverPrinters);
registry.category("actions").add("qz_test_print", qzTestPrint);
registry.category("actions").add("qz_print_preview", qzPrintPreview);

