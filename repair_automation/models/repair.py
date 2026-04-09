from odoo import fields, models


class RepairOrder(models.Model):
    _inherit = 'repair.order'

    sale_order_id = fields.Many2one('sale.order', string='Sales Order', index=True)
    sale_line_id = fields.Many2one('sale.order.line', string='Sales Order Line', index=True)

    _sql_constraints = [
        ('unique_serial_repair', 'unique(lot_id)', 'Only one repair order per serial allowed'),
    ]

    def action_repair_done(self):
        result = super().action_repair_done()
        self._push_repair_costs_to_sale()
        self._create_return_delivery()
        return result

    def _get_or_create_section(self, sale_order, lot):
        section_name = f'[SN: {lot.name} - {lot.product_id.display_name}]'
        section = sale_order.order_line.filtered(
            lambda line: line.display_type == 'line_section' and line.name == section_name
        )[:1]
        if section:
            return section

        sequence = max(sale_order.order_line.mapped('sequence') or [0]) + 1
        return self.env['sale.order.line'].create({
            'order_id': sale_order.id,
            'name': section_name,
            'display_type': 'line_section',
            'sequence': sequence,
        })

    def _push_repair_costs_to_sale(self):
        sale_line_model = self.env['sale.order.line']
        for repair in self:
            sale_order = repair.sale_order_id
            lot = repair.lot_id
            if not sale_order or not lot:
                continue

            section = self._get_or_create_section(sale_order, lot)
            next_sequence = section.sequence + 1
            existing_after = sale_order.order_line.filtered(lambda l: l.sequence > section.sequence)
            if existing_after:
                next_sequence = max(existing_after.mapped('sequence')) + 1

            for line_vals in repair._collect_repair_billable_lines(next_sequence):
                line_vals.update({
                    'order_id': sale_order.id,
                    'serial_id': lot.id,
                    'is_repair_line': True,
                })
                sale_line_model.create(line_vals)
                next_sequence += 1

    def _collect_repair_billable_lines(self, start_sequence):
        self.ensure_one()
        vals_list = []
        sequence = start_sequence

        candidate_fields = [
            'parts_line_ids',
            'fee_line_ids',
            'operation_ids',
            'move_ids',
        ]
        for field_name in candidate_fields:
            if field_name not in self._fields:
                continue
            for item in self[field_name]:
                product = item._fields.get('product_id') and item.product_id
                if not product:
                    continue
                quantity = 1.0
                if item._fields.get('product_uom_qty'):
                    quantity = item.product_uom_qty
                elif item._fields.get('quantity'):
                    quantity = item.quantity
                elif item._fields.get('product_qty'):
                    quantity = item.product_qty

                price_unit = 0.0
                if item._fields.get('price_unit'):
                    price_unit = item.price_unit
                elif item._fields.get('price_subtotal') and quantity:
                    price_unit = item.price_subtotal / quantity
                elif product.lst_price:
                    price_unit = product.lst_price

                vals_list.append({
                    'name': item._fields.get('name') and item.name or product.display_name,
                    'product_id': product.id,
                    'product_uom_qty': quantity,
                    'price_unit': price_unit,
                    'sequence': sequence,
                })
                sequence += 1

        return vals_list

    def _create_return_delivery(self):
        picking_model = self.env['stock.picking']
        for repair in self:
            if not repair.sale_order_id or not repair.lot_id:
                continue

            outgoing_type = self.env['stock.picking.type'].search([
                ('code', '=', 'outgoing'),
                ('warehouse_id.company_id', '=', repair.company_id.id),
            ], limit=1)
            if not outgoing_type:
                continue

            existing = picking_model.search([
                ('repair_order_id', '=', repair.id),
                ('picking_type_id', '=', outgoing_type.id),
                ('state', '!=', 'cancel'),
            ], limit=1)
            if existing:
                continue

            source_location = repair.location_id or outgoing_type.default_location_src_id
            customer_location = repair.sale_order_id.partner_id.property_stock_customer
            picking = picking_model.create({
                'partner_id': repair.sale_order_id.partner_id.id,
                'picking_type_id': outgoing_type.id,
                'origin': repair.name,
                'location_id': source_location.id,
                'location_dest_id': customer_location.id,
                'sale_order_id': repair.sale_order_id.id,
                'repair_order_id': repair.id,
                'lot_id': repair.lot_id.id,
            })

            move = self.env['stock.move'].create({
                'name': repair.product_id.display_name,
                'product_id': repair.product_id.id,
                'product_uom_qty': 1,
                'product_uom': repair.product_uom.id,
                'picking_id': picking.id,
                'location_id': source_location.id,
                'location_dest_id': customer_location.id,
                'sale_line_id': repair.sale_line_id.id,
            })
            self.env['stock.move.line'].create({
                'move_id': move.id,
                'picking_id': picking.id,
                'product_id': repair.product_id.id,
                'product_uom_id': repair.product_uom.id,
                'qty_done': 1,
                'location_id': source_location.id,
                'location_dest_id': customer_location.id,
                'lot_id': repair.lot_id.id,
                'sale_line_id': repair.sale_line_id.id,
            })
