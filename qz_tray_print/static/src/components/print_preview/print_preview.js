/** @odoo-module **/

import { Component, useState, onMounted, useRef } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";

/**
 * Print Preview Dialog Component
 * Displays a preview of the document before printing
 */
export class PrintPreviewDialog extends Component {
    static template = "qz_tray_print.PrintPreviewDialog";
    static components = { Dialog };
    static props = {
        previewData: { type: String },
        previewFormat: { type: String }, // 'pdf' or 'html'
        title: { type: String, optional: true },
        close: Function,
    };

    setup() {
        this.previewRef = useRef("preview");
        this.state = useState({
            loading: true,
            error: null,
        });

        onMounted(() => {
            this.renderPreview();
        });
    }

    /**
     * Render the preview based on format
     */
    renderPreview() {
        try {
            const previewElement = this.previewRef.el;
            
            if (this.props.previewFormat === 'pdf') {
                // For PDF, create an embed or iframe
                const pdfEmbed = document.createElement('embed');
                pdfEmbed.src = `data:application/pdf;base64,${this.props.previewData}`;
                pdfEmbed.type = 'application/pdf';
                pdfEmbed.width = '100%';
                pdfEmbed.height = '100%';
                previewElement.appendChild(pdfEmbed);
            } else if (this.props.previewFormat === 'html') {
                // For HTML, render directly
                previewElement.innerHTML = this.props.previewData;
            } else {
                throw new Error(`Unsupported preview format: ${this.props.previewFormat}`);
            }
            
            this.state.loading = false;
        } catch (error) {
            this.state.error = error.message;
            this.state.loading = false;
        }
    }

    /**
     * Confirm and proceed with printing
     */
    print() {
        this.props.close({ action: 'print' });
    }

    /**
     * Cancel preview and close dialog
     */
    cancel() {
        this.props.close({ action: 'cancel' });
    }
}
