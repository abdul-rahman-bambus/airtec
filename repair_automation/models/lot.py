import logging

from odoo import api, fields, models


_logger = logging.getLogger(__name__)


class StockLot(models.Model):
    _inherit = 'stock.lot'

    maintenance_sale_line_ids = fields.One2many('sale.order.line', 'serial_id', string='Maintenance Sale Lines')

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
        return (lot.company_id or self.env.company).partner_id

    def _is_lot_in_customer_location(self, lot):
        if 'location_id' in lot._fields and lot.location_id:
            return lot.location_id.usage == 'customer'
        quant_ids = lot.quant_ids.filtered(lambda q: q.location_id.usage == 'customer' and q.quantity > 0)
        return bool(quant_ids)

    def _prepare_maintenance_order_values(self, partner, lot, template):
        company = lot.company_id or self.env.company
        return {
            'partner_id': partner.id,
            'company_id': company.id,
            'origin': f'Maintenance Trigger {lot.name}',
            'is_maintanance_order': True,
            'sale_order_template_id': template.id,
        }

    def _resolve_maintenance_window(self, lot, today):
        if 'maintanance_1_start_date' in lot._fields and lot.maintanance_1_start_date == today:
            return 'maintanance_1'
        if 'maintenance_1_start_date' in lot._fields and lot.maintenance_1_start_date == today:
            return 'maintanance_1'
        if 'maintanance_2_start_date' in lot._fields and lot.maintanance_2_start_date == today:
            return 'maintanance_2'
        if 'maintenance_2_start_date' in lot._fields and lot.maintenance_2_start_date == today:
            return 'maintanance_2'
        return False

    def _select_template_for_window(self, window_flag, company):
        domain = [
            ('is_maintanance_quotation', '=', True),
            (window_flag, '=', True),
            ('company_id', 'in', [company.id, False]),
        ]
        templates = self.env['sale.order.template'].search(domain, order='id asc')
        if not templates:
            _logger.warning('No maintenance template found for window %s and company %s', window_flag, company.display_name)
            return self.env['sale.order.template']
        if len(templates) > 1:
            _logger.warning(
                'Multiple maintenance templates found for window %s. Using template %s (id=%s).',
                window_flag,
                templates[0].name,
                templates[0].id,
            )
        return templates[0]


    def _get_or_create_serial_section(self, order, lot):
        section_name = f"[SN: {lot.name} - {lot.product_id.display_name}]"
        existing = order.order_line.filtered(lambda l: l.display_type == 'line_section' and l.name == section_name)[:1]
        if existing:
            return existing
        sequence = max(order.order_line.mapped('sequence') or [0]) + 1
        return self.env['sale.order.line'].create({
            'order_id': order.id,
            'display_type': 'line_section',
            'name': section_name,
            'sequence': sequence,
        })

    def _create_lines_from_template(self, order, template, lot):
        sale_line_model = self.env['sale.order.line']
        section_line = self._get_or_create_serial_section(order, lot)
        sequence = section_line.sequence + 1
        for template_line in template.sale_order_template_line_ids:
            product = template_line.product_id
            if not product:
                continue
            price_unit = 0.0
            if 'price_unit' in template_line._fields:
                price_unit = template_line.price_unit
            elif 'price' in template_line._fields:
                price_unit = template_line.price
            elif 'list_price' in template_line._fields:
                price_unit = template_line.list_price
            elif product.lst_price:
                price_unit = product.lst_price

            discount = template_line.discount if 'discount' in template_line._fields else 0.0

            sale_line_model.create({
                'order_id': order.id,
                'name': template_line.name or product.get_product_multiline_description_sale() or product.display_name,
                'product_id': product.id,
                'product_uom_qty': template_line.product_uom_qty or 1.0,
                'product_uom_id': (template_line.product_uom_id or product.uom_id).id,
                'price_unit': price_unit,
                'discount': discount,
                'sequence': sequence,
                'serial_id': lot.id,
            })
            sequence += 1

    @api.model
    def _cron_create_maintenance_quotations(self):
        start_fields = self._get_maintenance_start_fields()
        if not start_fields:
            return

        today = fields.Date.context_today(self)
        lots = self.browse()
        for field_name in start_fields:
            field_domain = [(field_name, '=', today)]
            if 'location_id' in self._fields:
                field_domain.append(('location_id.usage', '=', 'customer'))
            lots |= self.search(field_domain)

        if not lots:
            return

        sale_order_model = self.env['sale.order']

        for lot in lots:
            if not lot.product_id or not self._is_lot_in_customer_location(lot):
                continue

            maintenance_window = self._resolve_maintenance_window(lot, today)
            if not maintenance_window:
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
                _logger.warning('Skipping lot %s because no partner is resolvable.', lot.name)
                continue

            template = self._select_template_for_window(maintenance_window, lot.company_id or self.env.company)
            if not template:
                _logger.warning('Skipping lot %s because no template is configured for %s.', lot.name, maintenance_window)
                continue
            if not template.sale_order_template_line_ids:
                _logger.warning('Skipping lot %s because selected template %s has no lines.', lot.name, template.name)
                continue

            order = sale_order_model.create(self._prepare_maintenance_order_values(partner, lot, template))
            self._create_lines_from_template(order, template, lot)
