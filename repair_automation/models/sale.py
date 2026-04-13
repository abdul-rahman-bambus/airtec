from odoo import fields, models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    repair_order_ids = fields.One2many('repair.order', 'sale_order_id', string='Repair Orders')
    is_maintanance_order = fields.Boolean(string='Is Maintenance Order', default=False, copy=False)

    def action_confirm(self):
        res = super().action_confirm()
        self._create_intake_pickings()
        return res

    def _create_intake_pickings(self):
        picking_model = self.env['stock.picking']
        for order in self:
            serial_lines = order.order_line.filtered(lambda line: line.serial_id and not line.display_type)
            if not serial_lines:
                continue

            incoming_type = self.env['stock.picking.type'].search([
                ('code', '=', 'incoming'),
                ('warehouse_id.company_id', '=', order.company_id.id),
            ], limit=1)
            if not incoming_type:
                continue

            src_location = order.partner_id.property_stock_customer
            dest_location = incoming_type.default_location_dest_id

            for line in serial_lines:
                existing = picking_model.search([
                    ('sale_order_id', '=', order.id),
                    ('lot_id', '=', line.serial_id.id),
                    ('picking_type_id', '=', incoming_type.id),
                    ('state', '!=', 'cancel'),
                ], limit=1)
                if existing:
                    continue

                picking = picking_model.create({
                    'partner_id': order.partner_id.id,
                    'sale_order_id': order.id,
                    'origin': order.name,
                    'picking_type_id': incoming_type.id,
                    'location_id': src_location.id,
                    'location_dest_id': dest_location.id,
                    'lot_id': line.serial_id.id,
                })
                move = self.env['stock.move'].create({
                    'name': line.name or line.product_id.display_name,
                    'product_id': line.product_id.id,
                    'product_uom_qty': 1,
                    'product_uom': line.product_uom_id.id,
                    'picking_id': picking.id,
                    'location_id': src_location.id,
                    'location_dest_id': dest_location.id,
                    'sale_line_id': line.id,
                })
                self.env['stock.move.line'].create({
                    'move_id': move.id,
                    'picking_id': picking.id,
                    'product_id': line.product_id.id,
                    'product_uom_id': line.product_uom_id.id,
                    'qty_done': 1,
                    'location_id': src_location.id,
                    'location_dest_id': dest_location.id,
                    'lot_id': line.serial_id.id,
                    'sale_line_id': line.id,
                })


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    serial_id = fields.Many2one(
        'stock.lot',
        string='Serial Number',
        domain="[('product_id', '=', product_id)]",
    )
    is_repair_line = fields.Boolean(string='Repair Generated Line', default=False)

    def _prepare_invoice_line(self, **optional_values):
        vals = super()._prepare_invoice_line(**optional_values)
        if self.serial_id:
            vals['name'] = f"{vals.get('name', self.name)}\nSerial: {self.serial_id.name}"
        return vals


class SaleOrderTemplate(models.Model):
    _inherit = 'sale.order.template'

    is_maintanance_quotation = fields.Boolean(string='Maintenance Quotation Template')
    maintanance_1 = fields.Boolean(string='Maintenance Window 1')
    maintanance_2 = fields.Boolean(string='Maintenance Window 2')
