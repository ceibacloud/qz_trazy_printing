/** @odoo-module **/

import { Component, useState, onWillStart, onMounted, onWillUnmount } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";

/**
 * Print Job Monitor Component
 * Displays and manages print jobs with filtering and actions
 */
export class PrintJobMonitor extends Component {
    static template = "qz_tray_print.PrintJobMonitor";
    static props = {};

    setup() {
        this.rpc = useService("rpc");
        this.notification = useService("notification");
        this.printService = useService("print_service");
        
        this.state = useState({
            jobs: [],
            loading: true,
            filters: {
                dateFrom: null,
                dateTo: null,
                user: null,
                printer: null,
                status: null,
            },
            printers: [],
            users: [],
        });

        this.refreshInterval = null;

        onWillStart(async () => {
            await this.loadInitialData();
        });

        onMounted(() => {
            // Auto-refresh every 5 seconds
            this.refreshInterval = setInterval(() => {
                this.loadJobs();
            }, 5000);
        });

        onWillUnmount(() => {
            if (this.refreshInterval) {
                clearInterval(this.refreshInterval);
            }
        });
    }

    /**
     * Load initial data (jobs, printers, users)
     */
    async loadInitialData() {
        try {
            await Promise.all([
                this.loadJobs(),
                this.loadPrinters(),
                this.loadUsers(),
            ]);
        } catch (error) {
            this.notification.add(`Failed to load data: ${error.message}`, {
                type: 'danger',
            });
        } finally {
            this.state.loading = false;
        }
    }

    /**
     * Load print jobs with current filters
     */
    async loadJobs() {
        try {
            const domain = this.buildDomain();
            const result = await this.rpc('/qz_tray/jobs', {
                domain: domain,
                limit: 100,
                order: 'submitted_date desc',
            });
            
            this.state.jobs = result.jobs || [];
        } catch (error) {
            console.error('Failed to load jobs:', error);
        }
    }

    /**
     * Load available printers for filtering
     */
    async loadPrinters() {
        try {
            const result = await this.rpc('/qz_tray/printers', {});
            this.state.printers = result.printers || [];
        } catch (error) {
            console.error('Failed to load printers:', error);
        }
    }

    /**
     * Load users for filtering
     */
    async loadUsers() {
        try {
            const result = await this.rpc('/web/dataset/call_kw', {
                model: 'res.users',
                method: 'search_read',
                args: [[], ['id', 'name']],
                kwargs: { limit: 100 },
            });
            this.state.users = result || [];
        } catch (error) {
            console.error('Failed to load users:', error);
        }
    }

    /**
     * Build search domain from filters
     */
    buildDomain() {
        const domain = [];
        
        if (this.state.filters.dateFrom) {
            domain.push(['submitted_date', '>=', this.state.filters.dateFrom]);
        }
        
        if (this.state.filters.dateTo) {
            domain.push(['submitted_date', '<=', this.state.filters.dateTo]);
        }
        
        if (this.state.filters.user) {
            domain.push(['user_id', '=', parseInt(this.state.filters.user)]);
        }
        
        if (this.state.filters.printer) {
            domain.push(['printer_id', '=', parseInt(this.state.filters.printer)]);
        }
        
        if (this.state.filters.status) {
            domain.push(['state', '=', this.state.filters.status]);
        }
        
        return domain;
    }

    /**
     * Apply filters and reload jobs
     */
    async applyFilters() {
        this.state.loading = true;
        await this.loadJobs();
        this.state.loading = false;
    }

    /**
     * Clear all filters
     */
    async clearFilters() {
        this.state.filters = {
            dateFrom: null,
            dateTo: null,
            user: null,
            printer: null,
            status: null,
        };
        await this.applyFilters();
    }

    /**
     * Retry a failed job
     */
    async retryJob(jobId) {
        try {
            const success = await this.printService.retryJob(jobId);
            if (success) {
                await this.loadJobs();
            }
        } catch (error) {
            this.notification.add(`Failed to retry job: ${error.message}`, {
                type: 'danger',
            });
        }
    }

    /**
     * Cancel a pending job
     */
    async cancelJob(jobId) {
        try {
            const success = await this.printService.cancelJob(jobId);
            if (success) {
                await this.loadJobs();
            }
        } catch (error) {
            this.notification.add(`Failed to cancel job: ${error.message}`, {
                type: 'danger',
            });
        }
    }

    /**
     * Resubmit a job (create new job with same parameters)
     */
    async resubmitJob(jobId) {
        try {
            const result = await this.rpc('/qz_tray/job/resubmit', {
                job_id: jobId,
            });
            
            if (result.success) {
                this.notification.add(`Job resubmitted successfully`, {
                    type: 'success',
                });
                await this.loadJobs();
            }
        } catch (error) {
            this.notification.add(`Failed to resubmit job: ${error.message}`, {
                type: 'danger',
            });
        }
    }

    /**
     * Get badge class for job state
     */
    getStateBadgeClass(state) {
        const classes = {
            'draft': 'bg-secondary',
            'queued': 'bg-info',
            'printing': 'bg-primary',
            'completed': 'bg-success',
            'failed': 'bg-danger',
            'cancelled': 'bg-warning',
        };
        return classes[state] || 'bg-secondary';
    }

    /**
     * Format date for display
     */
    formatDate(dateString) {
        if (!dateString) return '-';
        const date = new Date(dateString);
        return date.toLocaleString();
    }
}

// Register as a client action
registry.category("actions").add("qz_tray_print.print_monitor", PrintJobMonitor);
