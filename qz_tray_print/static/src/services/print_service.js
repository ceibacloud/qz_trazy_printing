/** @odoo-module **/

import { registry } from "@web/core/registry";

/**
 * Print Service
 * Frontend service for managing print operations and job status monitoring
 */
export const printService = {
    dependencies: ["qz_connector", "rpc", "notification", "dialog"],
    
    async start(env, { qz_connector, rpc, notification, dialog }) {
        const jobStatusCache = new Map();
        const jobMonitoringIntervals = new Map();
        
        /**
         * Print a document using a template
         * @param {string} documentType - Type of document being printed
         * @param {Object} data - Data to pass to the template
         * @param {number|string|null} printerId - Optional printer ID or name
         * @param {Object} options - Additional print options
         * @returns {Promise<number>} Job ID
         */
        async function printDocument(documentType, data, printerId = null, options = {}) {
            try {
                // Display submission notification
                notification.add('Submitting print job...', {
                    type: 'info',
                });
                
                // Call backend to create print job
                const result = await rpc('/qz_tray/print', {
                    document_type: documentType,
                    data: data,
                    printer_id: printerId,
                    options: options,
                });
                
                if (result.error) {
                    throw new Error(result.error);
                }
                
                const jobId = result.job_id;
                
                // Display submission confirmation
                notification.add(`Print job #${jobId} submitted successfully`, {
                    type: 'success',
                });
                
                // Start monitoring job status
                monitorJobStatus(jobId);
                
                return jobId;
            } catch (error) {
                // Display error notification
                notification.add(`Print failed: ${error.message}`, {
                    type: 'danger',
                });
                throw error;
            }
        }
        
        /**
         * Print raw data
         * @param {string} data - Raw print data
         * @param {string} format - Data format (pdf, html, escpos, zpl)
         * @param {number|string|null} printerId - Optional printer ID or name
         * @param {Object} options - Additional print options
         * @returns {Promise<number>} Job ID
         */
        async function printRaw(data, format, printerId = null, options = {}) {
            try {
                // Display submission notification
                notification.add('Submitting print job...', {
                    type: 'info',
                });
                
                // Call backend to create print job
                const result = await rpc('/qz_tray/print_raw', {
                    data: data,
                    format: format,
                    printer_id: printerId,
                    options: options,
                });
                
                if (result.error) {
                    throw new Error(result.error);
                }
                
                const jobId = result.job_id;
                
                // Display submission confirmation
                notification.add(`Print job #${jobId} submitted successfully`, {
                    type: 'success',
                });
                
                // Start monitoring job status
                monitorJobStatus(jobId);
                
                return jobId;
            } catch (error) {
                // Display error notification
                notification.add(`Print failed: ${error.message}`, {
                    type: 'danger',
                });
                throw error;
            }
        }
        
        /**
         * Generate document preview
         * @param {string} documentType - Type of document
         * @param {Object} data - Data to pass to the template
         * @returns {Promise<Object>} Preview data
         */
        async function previewDocument(documentType, data) {
            try {
                const result = await rpc('/qz_tray/preview', {
                    document_type: documentType,
                    data: data,
                });
                
                if (result.error) {
                    throw new Error(result.error);
                }
                
                return result;
            } catch (error) {
                notification.add(`Preview generation failed: ${error.message}`, {
                    type: 'danger',
                });
                throw error;
            }
        }
        
        /**
         * Get job status
         * @param {number} jobId - Job ID
         * @returns {Promise<Object>} Job status
         */
        async function getJobStatus(jobId) {
            try {
                const result = await rpc(`/qz_tray/job/${jobId}/status`, {});
                
                if (result.error) {
                    throw new Error(result.error);
                }
                
                return result;
            } catch (error) {
                console.error(`Failed to get job status for job ${jobId}:`, error);
                return null;
            }
        }
        
        /**
         * Monitor job status and display notifications
         * @param {number} jobId - Job ID to monitor
         */
        function monitorJobStatus(jobId) {
            // Don't monitor if already monitoring
            if (jobMonitoringIntervals.has(jobId)) {
                return;
            }
            
            const intervalId = setInterval(async () => {
                const status = await getJobStatus(jobId);
                
                if (!status) {
                    // Stop monitoring if we can't get status
                    stopMonitoring(jobId);
                    return;
                }
                
                const previousStatus = jobStatusCache.get(jobId);
                jobStatusCache.set(jobId, status.state);
                
                // Check for status changes
                if (previousStatus !== status.state) {
                    handleStatusChange(jobId, status);
                }
                
                // Stop monitoring if job is in terminal state
                if (['completed', 'failed', 'cancelled'].includes(status.state)) {
                    stopMonitoring(jobId);
                }
            }, 2000); // Poll every 2 seconds
            
            jobMonitoringIntervals.set(jobId, intervalId);
        }
        
        /**
         * Stop monitoring a job
         * @param {number} jobId - Job ID
         */
        function stopMonitoring(jobId) {
            const intervalId = jobMonitoringIntervals.get(jobId);
            if (intervalId) {
                clearInterval(intervalId);
                jobMonitoringIntervals.delete(jobId);
            }
        }
        
        /**
         * Handle job status changes
         * @param {number} jobId - Job ID
         * @param {Object} status - Job status object
         */
        function handleStatusChange(jobId, status) {
            switch (status.state) {
                case 'completed':
                    // Display success notification
                    notification.add(`Print job #${jobId} completed successfully`, {
                        type: 'success',
                    });
                    break;
                    
                case 'failed':
                    // Display error notification with failure reason
                    const errorMsg = status.error_message || 'Unknown error';
                    notification.add(`Print job #${jobId} failed: ${errorMsg}`, {
                        type: 'danger',
                    });
                    break;
                    
                case 'queued':
                    // Check if printer is offline
                    if (status.printer_offline) {
                        notification.add(
                            `Printer is offline. Job #${jobId} has been queued and will print when the printer comes online.`,
                            {
                                type: 'warning',
                            }
                        );
                    }
                    break;
                    
                case 'printing':
                    // Job is being processed
                    break;
                    
                default:
                    break;
            }
        }
        
        /**
         * Select printer from available printers
         * @param {Array} printers - Array of available printer objects
         * @param {string} title - Optional dialog title
         * @returns {Promise<Object>} Selected printer
         */
        async function selectPrinter(printers, title = "Select Printer") {
            if (!printers || printers.length === 0) {
                return null;
            }
            
            // Dynamically import the printer selector dialog
            const { PrinterSelectorDialog } = await import(
                "@qz_tray_print/components/printer_selector/printer_selector"
            );
            
            // Show printer selector dialog
            return new Promise((resolve) => {
                dialog.add(PrinterSelectorDialog, {
                    printers: printers,
                    title: title,
                }, {
                    onClose: (selectedPrinter) => {
                        resolve(selectedPrinter);
                    },
                });
            });
        }
        
        /**
         * Cancel a print job
         * @param {number} jobId - Job ID to cancel
         * @returns {Promise<boolean>} Success status
         */
        async function cancelJob(jobId) {
            try {
                const result = await rpc('/qz_tray/job/cancel', {
                    job_id: jobId,
                });
                
                if (result.success) {
                    notification.add(`Print job #${jobId} cancelled`, {
                        type: 'info',
                    });
                    stopMonitoring(jobId);
                    return true;
                }
                
                return false;
            } catch (error) {
                notification.add(`Failed to cancel job #${jobId}: ${error.message}`, {
                    type: 'danger',
                });
                return false;
            }
        }
        
        /**
         * Retry a failed print job
         * @param {number} jobId - Job ID to retry
         * @returns {Promise<boolean>} Success status
         */
        async function retryJob(jobId) {
            try {
                const result = await rpc('/qz_tray/job/retry', {
                    job_id: jobId,
                });
                
                if (result.success) {
                    notification.add(`Print job #${jobId} resubmitted`, {
                        type: 'info',
                    });
                    monitorJobStatus(jobId);
                    return true;
                }
                
                return false;
            } catch (error) {
                notification.add(`Failed to retry job #${jobId}: ${error.message}`, {
                    type: 'danger',
                });
                return false;
            }
        }
        
        // Return service API
        return {
            printDocument,
            printRaw,
            previewDocument,
            getJobStatus,
            selectPrinter,
            cancelJob,
            retryJob,
        };
    }
};

// Register the service
registry.category("services").add("print_service", printService);
