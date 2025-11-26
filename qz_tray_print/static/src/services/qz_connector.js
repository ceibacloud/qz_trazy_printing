/** @odoo-module **/

import { registry } from "@web/core/registry";

/**
 * QZ Tray Connector Service
 * Handles communication with QZ Tray for local printing
 */
export const qzConnectorService = {
    dependencies: ["rpc", "notification"],
    
    async start(env, { rpc, notification }) {
        let qz = null;
        let connected = false;
        let connecting = false;
        let certificate = null;
        let privateKey = null;
        
        /**
         * Load QZ Tray JavaScript library dynamically
         */
        async function loadQZLibrary() {
            return new Promise((resolve, reject) => {
                if (window.qz) {
                    resolve(window.qz);
                    return;
                }
                
                const script = document.createElement('script');
                script.src = 'https://cdn.jsdelivr.net/npm/qz-tray@2.2/qz-tray.js';
                script.onload = () => {
                    if (window.qz) {
                        resolve(window.qz);
                    } else {
                        reject(new Error('QZ Tray library failed to load'));
                    }
                };
                script.onerror = () => reject(new Error('Failed to load QZ Tray library'));
                document.head.appendChild(script);
            });
        }
        
        /**
         * Load certificate and private key from backend
         */
        async function loadCertificates() {
            try {
                const result = await rpc('/qz_tray/get_certificates', {});
                if (result.certificate && result.private_key) {
                    certificate = result.certificate;
                    privateKey = result.private_key;
                    return true;
                }
                return false;
            } catch (error) {
                console.error('Failed to load certificates:', error);
                return false;
            }
        }
        
        /**
         * Set up certificate-based authentication for QZ Tray
         */
        function setupCertificateAuth() {
            if (!qz || !certificate || !privateKey) {
                return false;
            }
            
            qz.security.setCertificatePromise(function(resolve) {
                resolve(certificate);
            });
            
            qz.security.setSignaturePromise(function(toSign) {
                return function(resolve, reject) {
                    try {
                        // Use QZ Tray's signing mechanism with the private key
                        const signature = qz.security.signRequest(toSign, privateKey);
                        resolve(signature);
                    } catch (error) {
                        reject(error);
                    }
                };
            });
            
            return true;
        }
        
        /**
         * Connect to QZ Tray
         */
        async function connect() {
            if (connected) {
                return true;
            }
            
            if (connecting) {
                // Wait for existing connection attempt
                return new Promise((resolve) => {
                    const checkInterval = setInterval(() => {
                        if (!connecting) {
                            clearInterval(checkInterval);
                            resolve(connected);
                        }
                    }, 100);
                });
            }
            
            connecting = true;
            
            try {
                // Load QZ Tray library
                qz = await loadQZLibrary();
                
                // Load certificates from backend
                const certsLoaded = await loadCertificates();
                if (!certsLoaded) {
                    throw new Error('QZ Tray certificates not configured. Please configure certificates in Settings > Print Configuration.');
                }
                
                // Setup certificate authentication
                if (!setupCertificateAuth()) {
                    throw new Error('Failed to setup certificate authentication');
                }
                
                // Attempt connection
                if (!qz.websocket.isActive()) {
                    await qz.websocket.connect();
                }
                
                connected = true;
                connecting = false;
                
                notification.add('Connected to QZ Tray successfully', {
                    type: 'success',
                });
                
                return true;
            } catch (error) {
                connected = false;
                connecting = false;
                
                const errorMessage = error.message || 'Unknown error';
                notification.add(`Failed to connect to QZ Tray: ${errorMessage}`, {
                    type: 'danger',
                });
                
                console.error('QZ Tray connection error:', error);
                return false;
            }
        }
        
        /**
         * Disconnect from QZ Tray
         */
        async function disconnect() {
            if (!connected || !qz) {
                return;
            }
            
            try {
                if (qz.websocket.isActive()) {
                    await qz.websocket.disconnect();
                }
                connected = false;
                
                notification.add('Disconnected from QZ Tray', {
                    type: 'info',
                });
            } catch (error) {
                console.error('Error disconnecting from QZ Tray:', error);
            }
        }
        
        /**
         * Reconnect to QZ Tray
         */
        async function reconnect() {
            await disconnect();
            return await connect();
        }
        
        /**
         * Check if connected to QZ Tray
         */
        function isConnected() {
            return connected && qz && qz.websocket.isActive();
        }
        
        /**
         * Get available printers from QZ Tray
         */
        async function getPrinters() {
            if (!isConnected()) {
                const connectSuccess = await connect();
                if (!connectSuccess) {
                    throw new Error('Not connected to QZ Tray');
                }
            }
            
            try {
                const printers = await qz.printers.find();
                return printers;
            } catch (error) {
                console.error('Error getting printers:', error);
                throw new Error(`Failed to get printers: ${error.message}`);
            }
        }
        
        /**
         * Print data to specified printer
         * @param {Object} config - Print configuration
         * @param {string} config.printer - Printer name
         * @param {string} config.data - Print data
         * @param {string} config.format - Data format (pdf, html, escpos, zpl)
         * @param {Object} config.options - Additional print options
         */
        async function print(config) {
            if (!isConnected()) {
                const connectSuccess = await connect();
                if (!connectSuccess) {
                    throw new Error('Not connected to QZ Tray');
                }
            }
            
            try {
                const { printer, data, format, options = {} } = config;
                
                if (!printer) {
                    throw new Error('Printer name is required');
                }
                
                if (!data) {
                    throw new Error('Print data is required');
                }
                
                // Configure print job based on format
                const printConfig = qz.configs.create(printer, options);
                let printData;
                
                switch (format) {
                    case 'pdf':
                        printData = [{
                            type: 'pixel',
                            format: 'pdf',
                            data: data
                        }];
                        break;
                    case 'html':
                        printData = [{
                            type: 'pixel',
                            format: 'html',
                            data: data
                        }];
                        break;
                    case 'escpos':
                    case 'zpl':
                        printData = [{
                            type: 'raw',
                            format: format,
                            data: data
                        }];
                        break;
                    default:
                        throw new Error(`Unsupported format: ${format}`);
                }
                
                // Send print job to QZ Tray
                await qz.print(printConfig, printData);
                
                return { success: true };
            } catch (error) {
                console.error('Print error:', error);
                throw new Error(`Print failed: ${error.message}`);
            }
        }
        
        // Return service API
        return {
            connect,
            disconnect,
            reconnect,
            isConnected,
            getPrinters,
            print,
        };
    }
};

// Register the service
registry.category("services").add("qz_connector", qzConnectorService);
