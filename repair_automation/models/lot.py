from odoo import api, fields, models


class StockLot(models.Model):
    _inherit = 'stock.lot'

    maintenance_sale_line_ids = fields.One2many('sale.order.line', 'serial_id', string='Maintenance Sale Lines')

    def _get_maintenance_product(self):
        param_key = 'repair_automation.maintenance_product_id'
        product_id = int(self.env['ir.config_parameter'].sudo().get_param(param_key, default='0') or 0)
        product = self.env['product.product'].browse(product_id)
        if product.exists():
            return product
        return self.env['product.product'].search([
            ('type', '=', 'service'),
            ('sale_ok', '=', True),
            ('default_code', '=', 'MAINTENANCE_SERVICE'),
        ], limit=1)

    def _get_maintenance_template(self):
        template_id = int(self.env['ir.config_parameter'].sudo().get_param(
            'repair_automation.maintanance_quotation_template_id',
            default='0',
        ) or 0)
        return self.env['sale.order.template'].browse(template_id).exists()

    @api.model
    def _get_maintenance_start_fields(self):
        candidates = [
            'maintanance_1_start_date',
            'maintanance_2_start_date',
            'maintenance_1_start_date',
            'maintenance_2_start_date',
        ]
        return [name for name in candidates if name in self._fields]


    def _get_maintenance_partner(self, lot):
        if 'partner_ids' in lot._fields and lot.partner_ids:
            return lot.partner_ids[0].commercial_partner_id
        if 'partner_id' in lot._fields and lot.partner_id:
            return lot.partner_id.commercial_partner_id
        if 'owner_id' in lot._fields and lot.owner_id:
            return lot.owner_id.commercial_partner_id
        return lot.company_id.partner_id

    def _prepare_maintenance_order_values(self, partner, lot):
        return {
            'partner_id': partner.id,
            'company_id': lot.company_id.id,
            'origin': f'Maintenance Trigger {lot.name}',
            'is_maintanance_order': True,
        }

    def _create_lines_from_template(self, order, template, lot):
        sale_line_model = self.env['sale.order.line']
        sequence = 10
        for template_line in template.sale_order_template_line_ids:
            product = template_line.product_id
            if not product:
                continue
            sale_line_model.create({
                'order_id': order.id,
                'name': template_line.name or product.get_product_multiline_description_sale() or product.display_name,
                'product_id': product.id,
                'product_uom_qty': template_line.product_uom_qty or 1.0,
                'product_uom': (template_line.product_uom_id or product.uom_id).id,
                'price_unit': template_line.price_unit,
                'discount': template_line.discount,
                'sequence': sequence,
                'serial_id': lot.id,
            })
            sequence += 1

    def _create_fallback_maintenance_line(self, order, lot, product):
        self.env['sale.order.line'].create({
            'order_id': order.id,
            'product_id': product.id,
            'product_uom_qty': 1.0,
            'name': product.get_product_multiline_description_sale() or product.display_name,
            'serial_id': lot.id,
        })

    @api.model
    def _cron_create_maintenance_quotations(self):
        start_fields = self._get_maintenance_start_fields()
        if not start_fields:
            return

        today = fields.Date.context_today(self)
        lots = self.browse()
        for field_name in start_fields:
            lots |= self.search([(field_name, '=', today)])
        if not lots:
            return

        template = self._get_maintenance_template()
        maintenance_product = self._get_maintenance_product() if not template else self.env['product.product']

        sale_order_model = self.env['sale.order']

        for lot in lots:
            if not lot.product_id:
                continue

            existing_order = sale_order_model.search([
                ('state', 'in', ['draft', 'sent']),
                ('is_maintanance_order', '=', True),
                ('order_line.serial_id', '=', lot.id),
            ], limit=1)
            if existing_order:
                continue

            partner = self._get_maintenance_partner(lot)
            if not partner:
                continue

            order = sale_order_model.create(self._prepare_maintenance_order_values(partner, lot))

            if template:
                self._create_lines_from_template(order, template, lot)
                if not order.order_line and maintenance_product:
                    self._create_fallback_maintenance_line(order, lot, maintenance_product)
            elif maintenance_product:
                self._create_fallback_maintenance_line(order, lot, maintenance_product)
