from odoo import fields, models


class StockLocation(models.Model):
    _inherit = 'stock.location'

    is_repair_location = fields.Boolean(string='Repair Location')
    is_maintenance_location = fields.Boolean(string='Maintenance Location')


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    sale_order_id = fields.Many2one('sale.order', string='Source Sales Order', index=True)
    repair_order_id = fields.Many2one('repair.order', string='Repair Order', index=True)
    lot_id = fields.Many2one('stock.lot', string='Serial Number', index=True)
    qc_source_move_line_id = fields.Many2one('stock.move.line', string='QC Source Move Line', index=True, copy=False)

    def button_validate(self):
        res = super().button_validate()
        self._create_qc_routing_pickings()
        return res

    def _create_qc_routing_pickings(self):
        internal_type_model = self.env['stock.picking.type']
        picking_model = self.env['stock.picking']
        move_model = self.env['stock.move']
        move_line_model = self.env['stock.move.line']

        done_pickings = self.filtered(
            lambda p: p.state == 'done' and p.picking_type_id.code == 'incoming' and p.sale_order_id
        )
        for picking in done_pickings:
            internal_type = internal_type_model.search([
                ('code', '=', 'internal'),
                ('warehouse_id.company_id', '=', picking.company_id.id),
            ], limit=1)
            if not internal_type:
                continue

            qc_lines = picking.move_line_ids.filtered(
                lambda line: line.state == 'done'
                and line.lot_id
                and line.quantity
                and not line.qc_route_picking_id
            )
            for line in qc_lines:
                route_result = line.qc_result or line._infer_qc_result_from_quality_checks()
                if not route_result:
                    continue
                if line.qc_result != route_result:
                    line.qc_result = route_result

                destination = line._get_qc_destination_location(route_result=route_result)
                if not destination or destination == line.location_dest_id:
                    continue

                existing = picking_model.search([
                    ('qc_source_move_line_id', '=', line.id),
                    ('state', '!=', 'cancel'),
                ], limit=1)
                if existing:
                    line.qc_route_picking_id = existing.id
                    continue

                route_picking = picking_model.create({
                    'partner_id': picking.partner_id.id,
                    'origin': f'{picking.name} - QC Route',
                    'picking_type_id': internal_type.id,
                    'location_id': line.location_dest_id.id,
                    'location_dest_id': destination.id,
                    'sale_order_id': picking.sale_order_id.id,
                    'lot_id': line.lot_id.id,
                    'qc_source_move_line_id': line.id,
                })
                route_move = move_model.create({
                    'name': line.product_id.display_name,
                    'product_id': line.product_id.id,
                    'product_uom_qty': line.quantity,
                    'product_uom': line.product_uom_id.id,
                    'picking_id': route_picking.id,
                    'location_id': line.location_dest_id.id,
                    'location_dest_id': destination.id,
                    'sale_line_id': line.sale_line_id.id,
                })
                move_line_model.create({
                    'move_id': route_move.id,
                    'picking_id': route_picking.id,
                    'product_id': line.product_id.id,
                    'product_uom_id': line.product_uom_id.id,
                    'quantity': line.quantity,
                    'location_id': line.location_dest_id.id,
                    'location_dest_id': destination.id,
                    'lot_id': line.lot_id.id,
                    'sale_line_id': line.sale_line_id.id,
                })
                line.qc_route_picking_id = route_picking.id


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
    qc_route_picking_id = fields.Many2one('stock.picking', string='QC Route Picking', copy=False)

    def _infer_qc_result_from_quality_checks(self):
        self.ensure_one()
        if 'quality.check' not in self.env:
            return False
        quality_check_model = self.env['quality.check']
        if 'move_line_id' not in quality_check_model._fields:
            return False

        checks = quality_check_model.search([
            ('move_line_id', '=', self.id),
            ('quality_state', 'in', ['pass', 'fail']),
        ])
        if not checks:
            return False
        if any(check.quality_state == 'fail' for check in checks):
            return 'repair'
        return 'maintenance'

    def _get_qc_destination_location(self, route_result=None):
        self.ensure_one()
        route_result = route_result or self.qc_result
        if not route_result:
            return self.env['stock.location']
        if route_result == 'scrap':
            return self.env['stock.location'].search([
                ('scrap_location', '=', True),
                ('company_id', 'in', [self.company_id.id, False]),
            ], limit=1)
        if route_result == 'maintenance':
            return self.env['stock.location'].search([
                ('is_maintenance_location', '=', True),
                ('company_id', 'in', [self.company_id.id, False]),
            ], limit=1)
        return self.env['stock.location'].search([
            ('is_repair_location', '=', True),
            ('company_id', 'in', [self.company_id.id, False]),
        ], limit=1)

    def action_apply_qc_route(self):
        for line in self:
            dest = line._get_qc_destination_location()
            if dest:
                line.location_dest_id = dest.id
