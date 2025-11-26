/** @odoo-module **/

import { Component, useState } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";

/**
 * Printer Selector Dialog Component
 * Displays a list of available printers for user selection
 */
export class PrinterSelectorDialog extends Component {
    static template = "qz_tray_print.PrinterSelectorDialog";
    static components = { Dialog };
    static props = {
        printers: { type: Array },
        title: { type: String, optional: true },
        close: Function,
    };

    setup() {
        this.state = useState({
            selectedPrinter: null,
        });
    }

    /**
     * Handle printer selection
     * @param {Object} printer - Selected printer object
     */
    selectPrinter(printer) {
        this.state.selectedPrinter = printer;
    }

    /**
     * Confirm printer selection and close dialog
     */
    confirm() {
        if (this.state.selectedPrinter) {
            this.props.close(this.state.selectedPrinter);
        }
    }

    /**
     * Cancel selection and close dialog
     */
    cancel() {
        this.props.close(null);
    }

    /**
     * Check if a printer is currently selected
     * @param {Object} printer - Printer to check
     * @returns {boolean}
     */
    isSelected(printer) {
        return this.state.selectedPrinter && 
               this.state.selectedPrinter.id === printer.id;
    }
}
