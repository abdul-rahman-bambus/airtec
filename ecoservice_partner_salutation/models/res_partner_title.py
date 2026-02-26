# Developed by ecodoo GmbH
# See COPYRIGHT and LICENSE files in the root directory of this module for full details.

from odoo import fields, models


class PartnerTitle(models.Model):
    _name = 'res.partner.title'
    _order = 'name'
    _description = 'Partner Title'

    name = fields.Char(
        string='Title',
        required=True,
        translate=True
    )
    shortcut = fields.Char(string='Abbreviation', translate=True)

    salutation = fields.Char(
        translate=True,
    )


class Partner(models.Model):
    _inherit = "res.partner"

    title: PartnerTitle = fields.Many2one('res.partner.title')
