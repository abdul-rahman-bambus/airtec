from odoo import fields, models


class StockLocation(models.Model):
    _inherit = 'stock.location'

    is_repair_location = fields.Boolean(string='Repair Location')
    is_maintenance_location = fields.Boolean(string='Maintenance Location')


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    sale_order_id = fields.Many2one('sale.order', string='Sales Order', index=True)
    repair_order_id = fields.Many2one('repair.order', string='Repair Order', index=True)
    lot_id = fields.Many2one('stock.lot', string='Serial Number', index=True)


class StockMove(models.Model):
    _inherit = 'stock.move'

    sale_line_id = fields.Many2one('sale.order.line', string='Sales Order Line')

    def _action_done(self, cancel_backorder=False):
        moves = super()._action_done(cancel_backorder=cancel_backorder)
        moves._create_repair_orders_from_moves()
        return moves

    def _create_repair_orders_from_moves(self):
        repair_order_model = self.env['repair.order']
        for move in self:
            destination = move.location_dest_id
            if not destination or not destination.is_repair_location:
                continue
            lot = move.move_line_ids[:1].lot_id
            if not lot:
                continue
            existing = repair_order_model.search([('lot_id', '=', lot.id)], limit=1)
            if existing:
                continue

            sale_line = move.sale_line_id or move.move_line_ids[:1].sale_line_id
            sale_order = sale_line.order_id if sale_line else move.picking_id.sale_order_id

            repair_order_model.create({
                'product_id': move.product_id.id,
                'product_uom': move.product_uom.id,
                'lot_id': lot.id,
                'company_id': move.company_id.id,
                'sale_order_id': sale_order.id if sale_order else False,
                'sale_line_id': sale_line.id if sale_line else False,
                'location_id': move.location_dest_id.id,
            })


class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    sale_line_id = fields.Many2one('sale.order.line', string='Sales Order Line')
    qc_result = fields.Selection([
        ('repair', 'Repair'),
        ('scrap', 'Scrap'),
        ('maintenance', 'Maintenance'),
    ], string='QC Result')

    def action_apply_qc_route(self):
        for line in self:
            if not line.qc_result:
                continue
            if line.qc_result == 'scrap':
                dest = self.env['stock.location'].search([
                    ('scrap_location', '=', True),
                    ('company_id', 'in', [line.company_id.id, False]),
                ], limit=1)
            elif line.qc_result == 'maintenance':
                dest = self.env['stock.location'].search([
                    ('is_maintenance_location', '=', True),
                    ('company_id', 'in', [line.company_id.id, False]),
                ], limit=1)
            else:
                dest = self.env['stock.location'].search([
                    ('is_repair_location', '=', True),
                    ('company_id', 'in', [line.company_id.id, False]),
                ], limit=1)

            if dest:
                line.location_dest_id = dest.id
