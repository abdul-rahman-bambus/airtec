from odoo import models, fields

class ProductTag(models.Model):
    _name = "product.tag"
    _description = "Product Tag"
    _order = "name"

    name = fields.Char(required=True)
    color = fields.Integer()
    active = fields.Boolean(default=True)
