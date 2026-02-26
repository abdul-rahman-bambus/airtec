from dateutil.relativedelta import relativedelta

from odoo import api, fields, models


class StockLot(models.Model):
    _inherit = "stock.lot"

    code_payload = fields.Char(string="Code Payload")
    code_device = fields.Boolean(string="Code Device")
    manufacturing_date = fields.Datetime(string="Manufacturing Date")

    code_1 = fields.Char(string="Code 1")
    code_2 = fields.Char(string="Code 2")
    code_3 = fields.Char(string="Code 3")
    code_4 = fields.Char(string="Code 4")

    code_date_1 = fields.Date(string="Date 1", compute="_compute_code_dates", store=True)
    code_date_2 = fields.Date(string="Date 2", compute="_compute_code_dates", store=True)
    code_date_3 = fields.Date(string="Date 3", compute="_compute_code_dates", store=True)
    code_date_4 = fields.Date(string="Date 4", compute="_compute_code_dates", store=True)

    maintenance_1_start_date = fields.Date(string="Maintenance 1 Start", compute="_compute_maintenance_dates", store=True)
    maintenance_1_end_date = fields.Date(string="Maintenance 1 End", compute="_compute_maintenance_dates", store=True)
    maintenance_2_start_date = fields.Date(string="Maintenance 2 Start", compute="_compute_maintenance_dates", store=True)
    maintenance_2_end_date = fields.Date(string="Maintenance 2 End", compute="_compute_maintenance_dates", store=True)
    maintenance_3_start_date = fields.Date(string="Maintenance 3 Start", compute="_compute_maintenance_dates", store=True)
    maintenance_3_end_date = fields.Date(string="Maintenance 3 End", compute="_compute_maintenance_dates", store=True)
    maintenance_4_start_date = fields.Date(string="Maintenance 4 Start", compute="_compute_maintenance_dates", store=True)
    maintenance_4_end_date = fields.Date(string="Maintenance 4 End", compute="_compute_maintenance_dates", store=True)

    @api.depends("manufacturing_date")
    def _compute_code_dates(self):
        for lot in self:
            if not lot.manufacturing_date:
                lot.code_date_1 = False
                lot.code_date_2 = False
                lot.code_date_3 = False
                lot.code_date_4 = False
                continue

            manufacturing_date = fields.Datetime.to_datetime(lot.manufacturing_date).date()
            lot.code_date_1 = manufacturing_date + relativedelta(years=1)
            lot.code_date_2 = manufacturing_date + relativedelta(years=2)
            lot.code_date_3 = manufacturing_date + relativedelta(years=3)
            lot.code_date_4 = manufacturing_date + relativedelta(years=4)

    @api.depends("manufacturing_date")
    def _compute_maintenance_dates(self):
        for lot in self:
            if not lot.manufacturing_date:
                lot.maintenance_1_start_date = False
                lot.maintenance_1_end_date = False
                lot.maintenance_2_start_date = False
                lot.maintenance_2_end_date = False
                lot.maintenance_3_start_date = False
                lot.maintenance_3_end_date = False
                lot.maintenance_4_start_date = False
                lot.maintenance_4_end_date = False
                continue

            manufacturing_date = fields.Datetime.to_datetime(lot.manufacturing_date).date()
            lot.maintenance_1_start_date = manufacturing_date + relativedelta(years=4, months=6)
            lot.maintenance_1_end_date = manufacturing_date + relativedelta(years=5, months=6)
            lot.maintenance_2_start_date = manufacturing_date + relativedelta(years=9, months=6)
            lot.maintenance_2_end_date = manufacturing_date + relativedelta(years=10, months=6)
            lot.maintenance_3_start_date = manufacturing_date + relativedelta(years=14, months=6)
            lot.maintenance_3_end_date = manufacturing_date + relativedelta(years=15, months=6)
            lot.maintenance_4_start_date = manufacturing_date + relativedelta(years=19, months=6)
            lot.maintenance_4_end_date = manufacturing_date + relativedelta(years=20, months=6)
