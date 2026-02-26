from odoo import models, fields

class ProductTemplate(models.Model):
    _inherit = "product.template"

    # tag_ids = fields.Many2many(
    #     "product.tag",
    #     "product_tag_rel",
    #     "product_tmpl_id",
    #     "tag_id",
    #     string="Product Tags"
    # )

    atlas_relevant = fields.Boolean(string="ATLAS Relevant")
    intrastat_relevant = fields.Boolean(string="Intrastat Relevant")
    device_label_line_4 = fields.Char(string="Device Label Line 4")
    control_panel_cable_length_mm = fields.Float(string="Control Panel Cable Length (mm)")
    coupling_cable_length_mm = fields.Float(string="Coupling Cable Length (mm)")

    measurement_uom = fields.Selection(
        [
            ("meter", "Meter"),
            ("feet", "Feet"),
            ("hpa", "hPa"),
            ("immed", "Immediate"),
            ("sec", "Seconds"),
        ],
        string="Measurement Unit"
    )
