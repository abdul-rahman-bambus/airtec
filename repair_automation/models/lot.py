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

    @api.model
    def _cron_create_maintenance_quotations(self):
        """Create one maintenance quotation per lot when a start date matches today."""
        today = fields.Date.context_today(self)
        lots = self.search([
            '|',
            ('maintanance_1_start_date', '=', today),
            ('maintanance_2_start_date', '=', today),
        ])

        if not lots:
            return

        maintenance_product = self._get_maintenance_product()
        if not maintenance_product:
            return

        sale_order_model = self.env['sale.order']
        sale_line_model = self.env['sale.order.line']

        for lot in lots:
            if not lot.product_id:
                continue

            existing_line = sale_line_model.search([
                ('serial_id', '=', lot.id),
                ('order_id.state', 'in', ['draft', 'sent']),
                ('product_id', '=', maintenance_product.id),
            ], limit=1)
            if existing_line:
                continue

            partner = lot.partner_id or lot.company_id.partner_id
            if not partner:
                continue

            order = sale_order_model.create({
                'partner_id': partner.id,
                'company_id': lot.company_id.id,
                'origin': f'Maintenance Trigger {lot.name}',
            })

            sale_line_model.create({
                'order_id': order.id,
                'product_id': maintenance_product.id,
                'product_uom_qty': 1.0,
                'name': maintenance_product.get_product_multiline_description_sale() or maintenance_product.display_name,
                'serial_id': lot.id,
            })
