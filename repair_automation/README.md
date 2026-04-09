# Repair Automation (Odoo 19)

## Overview
`repair_automation` automates an end-to-end serialized repair and maintenance process in Odoo 19.

Core business rule:

- **1 Serial Number (`stock.lot`) → 1 Sales Order flow → 1 Repair Order → 1 Section on Sales Order billing**

The module links Sales, Inventory, and Repairs so that maintenance triggers, intake logistics, repair execution, cost billing, and return shipping are connected.

## Functional Workflows

### 1) Maintenance trigger to quotation (CRON)
- A scheduled action runs daily.
- It checks `stock.lot` records where maintenance start dates match today.
- Supported field names are auto-detected to handle naming variations:
  - `maintanance_1_start_date` / `maintanance_2_start_date`
  - `maintenance_1_start_date` / `maintenance_2_start_date`
- For each matching serial (`stock.lot`), it creates one draft quotation with one service line linked to that serial.
- Duplicate draft quotations for the same serial + maintenance product are prevented.

### 2) Sales confirmation to intake picking
- On `sale.order.action_confirm()`, the module creates incoming intake pickings for serial-linked sale lines.
- Intake picking, move, and move line are linked back to:
  - Sale Order
  - Sale Order Line
  - Serial Number (`stock.lot`)

### 3) QC-based routing
- `stock.move.line` includes `qc_result` with options:
  - Repair
  - Scrap
  - Maintenance
- Applying QC route updates destination location to a configured repair/maintenance/scrap location.

### 4) Auto repair creation from stock move completion
- When moves are completed (`stock.move._action_done()`), any move arriving at a repair location triggers repair order creation.
- Created repair orders are linked to the originating sale order / sale line where available.

### 5) Repair completion billing + return shipment
- On `repair.order.action_repair_done()`:
  - Billable repair lines are pushed to the linked sale order.
  - Lines are grouped under a serial-specific section (`line_section`).
  - Return delivery picking is auto-created and linked to both repair and sale.

## Technical Design

## Extended Models

### `stock.lot`
- Uses maintenance window fields from `airtec_product_extensions`.
- Adds:
  - `maintenance_sale_line_ids`
- Methods:
  - `_get_maintenance_product()`
  - `_cron_create_maintenance_quotations()`

### `sale.order`
- Adds:
  - `repair_order_ids`
- Overrides:
  - `action_confirm()` to create intake pickings

### `sale.order.line`
- Adds:
  - `serial_id` (`Many2one('stock.lot')`)
  - `is_repair_line` (`Boolean`)

### `stock.location`
- Adds routing flags:
  - `is_repair_location`
  - `is_maintenance_location`

### `stock.picking`
- Adds links:
  - `sale_order_id`
  - `repair_order_id`
  - `lot_id`

### `stock.move`
- Adds:
  - `sale_line_id`
- Overrides `_action_done()` for repair auto-creation.

### `stock.move.line`
- Adds:
  - `sale_line_id`
  - `qc_result`
- Method:
  - `action_apply_qc_route()`

### `repair.order`
- Adds:
  - `sale_order_id`
  - `sale_line_id`
- Constraint:
  - SQL unique on `lot_id` (`unique_serial_repair`)
- Overrides:
  - `action_repair_done()` for billing + return shipment automation

## Data & Views
- `data/cron.xml`
  - Daily maintenance quotation scheduled action.
- `views/sale_views.xml`
  - Sales order repairs tab and serial fields on order lines.
- `views/stock_views.xml`
  - Location flags, picking links, and move-line QC fields.
- `views/repair_views.xml`
  - Repair to sale linking fields.

## Dependencies
The module depends on:
- `sale_management`
- `sale_stock`
- `stock`
- `repair`
- `quality_control`
- `airtec_product_extensions`

`airtec_product_extensions` is required because maintenance window fields on `stock.lot` are defined there.

## Installation & Setup

1. Place `repair_automation` in your Odoo addons path.
2. Update app list.
3. Install dependencies (especially `airtec_product_extensions`).
4. Install **Repair Automation** module.

## Configuration Checklist

### A) Maintenance service product
Set one service product to be used by cron quotation creation:
- Preferred: set system parameter `repair_automation.maintenance_product_id` to the product ID.
- Fallback behavior: searches service product with internal reference `MAINTENANCE_SERVICE`.

### B) Locations
Configure stock locations:
- Mark one or more locations as:
  - Repair Location (`is_repair_location`)
  - Maintenance Location (`is_maintenance_location`)
- Ensure scrap location exists (`scrap_location=True`).

### C) Serialized products
- Ensure products are tracked by serial number.
- Maintain lot-level maintenance start dates in whichever supported field names exist on `stock.lot`.

### D) Repair billing data
- Ensure repair order lines (parts/fees/operations/moves) are correctly populated so billable lines can be transferred to SO.

## Usage Summary
1. Maintain lot maintenance dates.
2. Cron creates draft quotations when maintenance starts.
3. Confirm SO -> intake picking generated.
4. Receive and apply QC route to repair/scrap/maintenance.
5. Move to repair location -> repair order auto-created.
6. Complete repair -> costs pushed to SO under serial section and return delivery generated.

## Notes & Limitations
- This module assumes standard Odoo 19 models for Sale/Stock/Repair and compatible view architecture.
- Section and line sequencing are automated but may still be customized for specific invoicing layouts.
- For high-volume operation, consider adding extra indexes and integration tests around cron and move completion flows.
