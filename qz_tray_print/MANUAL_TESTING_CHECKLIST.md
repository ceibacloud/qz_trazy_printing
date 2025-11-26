# Manual Testing Checklist for Task 18

This checklist provides step-by-step instructions for manually verifying all core functionality in a running Odoo instance.

## Prerequisites

- [ ] Odoo 18 instance is running
- [ ] QZ Tray Print Integration module is installed
- [ ] QZ Tray is installed on your local machine
- [ ] You have access to at least one printer

---

## 1. Menu Accessibility Tests

### Test 1.1: Navigate to QZ Tray Printing Menu
- [ ] Open Odoo
- [ ] Look for "QZ Tray Printing" in the main menu
- [ ] Click on "QZ Tray Printing"
- [ ] Verify submenu appears with: Configuration, Printers, Print Queue, Print Jobs

### Test 1.2: Access Printers Menu
- [ ] Click "QZ Tray Printing" > "Printers"
- [ ] Verify printer list view opens
- [ ] Verify "Discover Printers" button is visible in the header

### Test 1.3: Access Print Queue Menu
- [ ] Click "QZ Tray Printing" > "Print Queue"
- [ ] Verify kanban view opens showing print jobs grouped by state

### Test 1.4: Access Print Jobs Menu
- [ ] Click "QZ Tray Printing" > "Print Jobs"
- [ ] Verify list view opens showing print job history

### Test 1.5: Access Configuration Menus
- [ ] Click "QZ Tray Printing" > "Configuration" > "QZ Tray Settings"
- [ ] Verify configuration form opens
- [ ] Click "QZ Tray Printing" > "Configuration" > "Print Templates"
- [ ] Verify template list opens

**Result**: ☐ Pass ☐ Fail

---

## 2. Window Actions Tests

### Test 2.1: Printer Management Views
- [ ] Open "Printers" menu
- [ ] Verify list view displays: name, type, system name, location, department, default, priority, active
- [ ] Click on a printer (or create new)
- [ ] Verify form view opens with all fields organized in groups
- [ ] Verify "Test Print" button is visible in header
- [ ] Click "Back" to return to list view

### Test 2.2: Print Job Views
- [ ] Open "Print Jobs" menu
- [ ] Verify list view displays: name, document type, printer, user, state, dates
- [ ] Verify state field has color coding (green=completed, red=failed, etc.)
- [ ] Click on a job (or create new)
- [ ] Verify form view opens with job details
- [ ] Verify action buttons (Cancel, Retry, Resubmit) are visible based on state

### Test 2.3: Print Queue Kanban View
- [ ] Open "Print Queue" menu
- [ ] Verify kanban view displays jobs grouped by state
- [ ] Verify job cards show: document type, printer, user, submitted date, priority
- [ ] Verify color coding: gray=draft, yellow=queued, blue=printing, green=completed, red=failed
- [ ] Verify quick action buttons on cards (Cancel, Retry)

**Result**: ☐ Pass ☐ Fail

---

## 3. Client Actions Tests

### Test 3.1: Printer Discovery
**Prerequisites**: QZ Tray must be running on your machine

- [ ] Open "Printers" list view
- [ ] Click "Discover Printers" button in header
- [ ] Verify notification appears: "Connecting to QZ Tray..."
- [ ] Verify notification appears: "Discovering printers..."
- [ ] Verify success notification with count: "X printers found (Y new, Z updated)"
- [ ] Verify printer list refreshes with discovered printers

**If QZ Tray is not running**:
- [ ] Verify error notification: "Failed to connect to QZ Tray"

### Test 3.2: Test Print
**Prerequisites**: At least one printer configured

- [ ] Open a printer form view
- [ ] Click "Test Print" button in header
- [ ] Verify notification: "Sending test page to printer..."
- [ ] Verify success notification: "Test page sent successfully to [Printer Name]"
- [ ] Verify test page prints on the physical printer
- [ ] Verify test page contains: printer name, date/time, test pattern

**Expected Test Page Content**:
- Header: "QZ Tray Test Page"
- Printer details (name, system name, type)
- Current date and time
- Test pattern with letters, numbers, symbols

**Result**: ☐ Pass ☐ Fail

---

## 4. Print Job Submission Tests

### Test 4.1: Create and Submit Print Job
- [ ] Open "Print Jobs" menu
- [ ] Click "Create" button
- [ ] Fill in required fields:
  - Document Type: "test_document"
  - Printer: Select a printer
  - Data Format: "html"
  - Data: Upload or paste HTML content
- [ ] Click "Save"
- [ ] Verify job is in "Draft" state
- [ ] Click "Resubmit" button (or submit action)
- [ ] Verify job state changes to "Queued"
- [ ] Verify "Submitted Date" is populated

### Test 4.2: Submit Job for Active Printer
- [ ] Ensure printer is active (active checkbox checked)
- [ ] Create and submit a job for this printer
- [ ] Verify job goes to "Queued" state
- [ ] Verify no error message

### Test 4.3: Submit Job for Offline Printer
- [ ] Set a printer to inactive (uncheck active checkbox)
- [ ] Create and submit a job for this printer
- [ ] Verify job goes to "Queued" state
- [ ] Verify error message mentions "offline" or "inactive"

**Result**: ☐ Pass ☐ Fail

---

## 5. Job Management Actions Tests

### Test 5.1: Cancel Job
- [ ] Create and submit a job (should be in "Queued" state)
- [ ] Open the job form view
- [ ] Verify "Cancel" button is visible
- [ ] Click "Cancel" button
- [ ] Verify job state changes to "Cancelled"
- [ ] Verify "Completed Date" is populated
- [ ] Verify "Cancel" button is no longer visible

### Test 5.2: Retry Failed Job
**Prerequisites**: Configure retry settings first

- [ ] Go to Settings > Technical > System Parameters
- [ ] Set `qz_tray.retry_enabled` = `True`
- [ ] Set `qz_tray.retry_count` = `3`
- [ ] Create a job and manually set it to "Failed" state with error message containing "timeout"
- [ ] Open the job form view
- [ ] Verify "Retry" button is visible
- [ ] Click "Retry" button
- [ ] Verify job state changes to "Queued"
- [ ] Verify "Retry Count" increments by 1

### Test 5.3: Retry Job at Max Retries
- [ ] Create a job in "Failed" state with retry_count = 3 (max)
- [ ] Click "Retry" button
- [ ] Verify job remains in "Failed" state
- [ ] Verify error message includes "Maximum retry count exceeded"
- [ ] Verify "Completed Date" is populated

### Test 5.4: Resubmit Job
- [ ] Create a job in "Failed" or "Cancelled" state
- [ ] Open the job form view
- [ ] Verify "Resubmit" button is visible
- [ ] Click "Resubmit" button
- [ ] Verify job state changes to "Queued"
- [ ] Verify new "Submitted Date" is set

**Result**: ☐ Pass ☐ Fail

---

## 6. Record Rules / Access Control Tests

### Test 6.1: Print User Access
**Prerequisites**: Create a user with only "Print User" group

- [ ] Log in as Print User
- [ ] Open "Print Jobs" menu
- [ ] Create a job as this user
- [ ] Verify you can see your own job
- [ ] Log in as a different Print User
- [ ] Open "Print Jobs" menu
- [ ] Verify you CANNOT see the first user's job
- [ ] Try to access the first user's job directly (via URL or search)
- [ ] Verify access is denied or job is not visible

### Test 6.2: Print Manager Access
**Prerequisites**: Create a user with "Print Manager" group

- [ ] Log in as Print Manager
- [ ] Open "Print Jobs" menu
- [ ] Verify you can see jobs from ALL users
- [ ] Verify you can edit any job
- [ ] Verify you can delete jobs

### Test 6.3: Print Administrator Access
**Prerequisites**: Create a user with "Print Administrator" group

- [ ] Log in as Print Administrator
- [ ] Open "Print Jobs" menu
- [ ] Verify you can see jobs from ALL users
- [ ] Verify you can edit any job
- [ ] Verify you can delete jobs
- [ ] Open "Configuration" > "QZ Tray Settings"
- [ ] Verify you can access certificate configuration

**Result**: ☐ Pass ☐ Fail

---

## 7. Email Notification Tests

### Test 7.1: Enable Email Notifications
- [ ] Go to Settings > Technical > System Parameters
- [ ] Create or update parameter: `qz_tray.email_notifications_enabled` = `True`
- [ ] Verify parameter is saved

### Test 7.2: Test Email Notification on Failure
**Prerequisites**: Email must be configured in Odoo

- [ ] Ensure retry is enabled and max retry count is set to 2
- [ ] Create a job in "Failed" state with retry_count = 2
- [ ] Set error message to include "timeout" (transient error)
- [ ] Click "Retry" button
- [ ] Verify job fails (exceeds max retries)
- [ ] Go to Settings > Technical > Email > Emails
- [ ] Verify an email was created with subject "Print Job Failed: [Job Name]"
- [ ] Open the email
- [ ] Verify email contains:
  - Job details (name, document type, printer, user, submitted date, retry count)
  - Error message
  - Recommended actions
  - Link to view job in Odoo

### Test 7.3: Verify Email Recipients
- [ ] Check email recipients
- [ ] Verify email is sent to users in "Print Administrator" group
- [ ] Verify each admin with an email address receives the notification

### Test 7.4: Test Email Disabled
- [ ] Set `qz_tray.email_notifications_enabled` = `False`
- [ ] Create a job that fails after max retries
- [ ] Verify NO email is created

**Result**: ☐ Pass ☐ Fail

---

## 8. Additional Functionality Tests

### Test 8.1: Offline Printer Queuing
- [ ] Set a printer to inactive
- [ ] Submit a job for this printer
- [ ] Verify job is queued with offline message
- [ ] Set printer back to active
- [ ] Run queue processing (manually or wait for cron)
- [ ] Verify job is processed

### Test 8.2: Batch Label Printing
- [ ] Create a label printer (printer_type = 'label')
- [ ] Create 3 label jobs for this printer in "Queued" state
- [ ] Call `batch_label_jobs()` method (via Python shell or automated process)
- [ ] Verify a single batch job is created
- [ ] Verify individual jobs are cancelled
- [ ] Verify batch job contains combined data

### Test 8.3: Queue Processing
- [ ] Create multiple jobs in "Queued" state for different printers
- [ ] Run the queue processing cron job or call `process_queued_jobs()` manually
- [ ] Verify jobs are processed in FIFO order per printer
- [ ] Verify jobs for higher priority printers are processed first
- [ ] Check logs for processing summary

### Test 8.4: Search and Filters
- [ ] Open "Print Jobs" menu
- [ ] Test search by job name
- [ ] Test filter by state (Draft, Queued, Printing, Completed, Failed, Cancelled)
- [ ] Test filter "My Jobs"
- [ ] Test filter "Active Jobs"
- [ ] Test date filters (Today, Last 7 Days, Last 30 Days)
- [ ] Test group by: Status, Printer, User, Document Type

**Result**: ☐ Pass ☐ Fail

---

## 9. Integration Tests

### Test 9.1: HTTP Endpoints (via Browser Console or API Client)
Test the following endpoints (requires authentication):

- [ ] GET `/qz_tray/get_certificates` - Returns certificates
- [ ] GET `/qz_tray/printers` - Returns printer list
- [ ] POST `/qz_tray/printers/sync` - Syncs printers
- [ ] POST `/qz_tray/print` - Submits print job
- [ ] GET `/qz_tray/job/<job_id>/status` - Returns job status
- [ ] POST `/qz_tray/job/cancel` - Cancels job
- [ ] POST `/qz_tray/job/retry` - Retries job

### Test 9.2: JavaScript Services
- [ ] Open browser console
- [ ] Verify no JavaScript errors on page load
- [ ] Verify QZ Connector service is registered
- [ ] Verify Print Service is registered
- [ ] Test printer discovery (should trigger QZ Connector)

**Result**: ☐ Pass ☐ Fail

---

## 10. Error Handling Tests

### Test 10.1: QZ Tray Not Running
- [ ] Stop QZ Tray application
- [ ] Try to discover printers
- [ ] Verify error notification: "Failed to connect to QZ Tray"
- [ ] Try to test print
- [ ] Verify error notification

### Test 10.2: Invalid Printer Configuration
- [ ] Create a printer with invalid system name
- [ ] Try to submit a job for this printer
- [ ] Verify appropriate error message

### Test 10.3: Missing Required Fields
- [ ] Try to create a job without document type
- [ ] Verify validation error
- [ ] Try to create a job without printer
- [ ] Verify validation error
- [ ] Try to create a job without data or template
- [ ] Verify validation error

**Result**: ☐ Pass ☐ Fail

---

## Summary

### Test Results

| Test Section | Status | Notes |
|-------------|--------|-------|
| 1. Menu Accessibility | ☐ Pass ☐ Fail | |
| 2. Window Actions | ☐ Pass ☐ Fail | |
| 3. Client Actions | ☐ Pass ☐ Fail | |
| 4. Print Job Submission | ☐ Pass ☐ Fail | |
| 5. Job Management Actions | ☐ Pass ☐ Fail | |
| 6. Record Rules | ☐ Pass ☐ Fail | |
| 7. Email Notifications | ☐ Pass ☐ Fail | |
| 8. Additional Functionality | ☐ Pass ☐ Fail | |
| 9. Integration Tests | ☐ Pass ☐ Fail | |
| 10. Error Handling | ☐ Pass ☐ Fail | |

### Overall Result: ☐ Pass ☐ Fail

### Issues Found:
1. 
2. 
3. 

### Recommendations:
1. 
2. 
3. 

---

## Notes

- All tests should be performed in a clean Odoo instance with the module freshly installed
- QZ Tray must be properly configured with valid certificates for full functionality
- Some tests require multiple user accounts with different security groups
- Email tests require proper email configuration in Odoo
- Keep browser console open during testing to catch JavaScript errors

---

**Tester Name**: ___________________
**Date**: ___________________
**Odoo Version**: 18.0
**Module Version**: 1.0.0
