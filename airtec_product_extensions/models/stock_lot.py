import base64
import io
import math
import re

from dateutil.relativedelta import relativedelta
from PIL import Image

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

    code_date_1 = fields.Date(string="Date 1")
    code_date_2 = fields.Date(string="Date 2")
    code_date_3 = fields.Date(string="Date 3")
    code_date_4 = fields.Date(string="Date 4")

    maintenance_1_start_date = fields.Date(string="Maintenance 1 Start")
    maintenance_1_end_date = fields.Date(string="Maintenance 1 End")
    maintenance_2_start_date = fields.Date(string="Maintenance 2 Start")
    maintenance_2_end_date = fields.Date(string="Maintenance 2 End")
    maintenance_3_start_date = fields.Date(string="Maintenance 3 Start")
    maintenance_3_end_date = fields.Date(string="Maintenance 3 End")
    maintenance_4_start_date = fields.Date(string="Maintenance 4 Start")
    maintenance_4_end_date = fields.Date(string="Maintenance 4 End")

    @api.model
    def _extract_name_from_payload(self, payload):
        """Extract the serial name from code payload.

        Primary rule: first 5 leading digits (historical AIRTEC payload format).
        Fallback: first 5 non-space chars when leading digits are unavailable.
        """
        if not payload:
            return False

        normalized = payload.strip()
        if not normalized:
            return False

        match = re.match(r"(\d{5})", normalized)
        if match:
            return match.group(1)

        if len(normalized) >= 5:
            return normalized[:5]
        return False

    @api.model
    def _extract_codes_from_payload(self, payload):
        """Extract code_1..code_4 from payload pattern like *6878*5054*0462*3726*."""
        if not payload:
            return {}

        matches = re.findall(r"\*(\d{4})", payload)
        if len(matches) < 4:
            return {}

        return {
            "code_1": matches[0],
            "code_2": matches[1],
            "code_3": matches[2],
            "code_4": matches[3],
        }

    @api.model
    def _build_dates_from_manufacturing_date(self, manufacturing_date):
        if not manufacturing_date:
            return {}

        mfd = fields.Datetime.to_datetime(manufacturing_date).date()
        return {
            "code_date_1": mfd + relativedelta(years=1),
            "code_date_2": mfd + relativedelta(years=2),
            "code_date_3": mfd + relativedelta(years=3),
            "code_date_4": mfd + relativedelta(years=4),
            "maintenance_1_start_date": mfd + relativedelta(years=4, months=6),
            "maintenance_1_end_date": mfd + relativedelta(years=5, months=6),
            "maintenance_2_start_date": mfd + relativedelta(years=9, months=6),
            "maintenance_2_end_date": mfd + relativedelta(years=10, months=6),
            "maintenance_3_start_date": mfd + relativedelta(years=14, months=6),
            "maintenance_3_end_date": mfd + relativedelta(years=15, months=6),
            "maintenance_4_start_date": mfd + relativedelta(years=19, months=6),
            "maintenance_4_end_date": mfd + relativedelta(years=20, months=6),
        }

    @api.onchange("code_payload")
    def _onchange_code_payload_set_fields(self):
        for lot in self:
            derived_name = lot._extract_name_from_payload(lot.code_payload)
            if derived_name:
                lot.name = derived_name

            payload_codes = lot._extract_codes_from_payload(lot.code_payload)
            for field_name, value in payload_codes.items():
                setattr(lot, field_name, value)

    @api.onchange("manufacturing_date")
    def _onchange_manufacturing_date_set_dates(self):
        for lot in self:
            calculated_dates = lot._build_dates_from_manufacturing_date(lot.manufacturing_date)
            for field_name, value in calculated_dates.items():
                if not getattr(lot, field_name):
                    setattr(lot, field_name, value)

    @api.model_create_multi
    def create(self, vals_list):
        prepared_vals_list = []
        for vals in vals_list:
            prepared_vals = dict(vals)

            payload = prepared_vals.get("code_payload")
            if payload:
                if not prepared_vals.get("name"):
                    derived_name = self._extract_name_from_payload(payload)
                    if derived_name:
                        prepared_vals["name"] = derived_name

                payload_codes = self._extract_codes_from_payload(payload)
                for field_name, value in payload_codes.items():
                    if not prepared_vals.get(field_name):
                        prepared_vals[field_name] = value

            if prepared_vals.get("manufacturing_date"):
                calculated_dates = self._build_dates_from_manufacturing_date(prepared_vals["manufacturing_date"])
                for field_name, value in calculated_dates.items():
                    if not prepared_vals.get(field_name):
                        prepared_vals[field_name] = value

            prepared_vals_list.append(prepared_vals)

        return super().create(prepared_vals_list)

    def write(self, vals):
        prepared_vals = dict(vals)

        if prepared_vals.get("code_payload") and "name" not in prepared_vals:
            derived_name = self._extract_name_from_payload(prepared_vals["code_payload"])
            if derived_name:
                prepared_vals["name"] = derived_name

        if prepared_vals.get("code_payload"):
            payload_codes = self._extract_codes_from_payload(prepared_vals["code_payload"])
            for field_name, value in payload_codes.items():
                if field_name not in prepared_vals:
                    prepared_vals[field_name] = value

        if prepared_vals.get("manufacturing_date"):
            calculated_dates = self._build_dates_from_manufacturing_date(prepared_vals["manufacturing_date"])
            # Only fill empty date fields to preserve manually adjusted values.
            for lot in self:
                lot_vals = dict(prepared_vals)
                for field_name, value in calculated_dates.items():
                    if field_name not in lot_vals and not lot[field_name]:
                        lot_vals[field_name] = value
                super(StockLot, lot).write(lot_vals)
            return True

        return super().write(prepared_vals)

    def _get_company_logo_zpl(self, width=120, height=80):
        """Return ZPL ^GFA command for company logo image, or empty string if unavailable."""
        self.ensure_one()
        company = self.company_id or self.env.company
        logo_b64 = company.logo or company.logo_web or company.partner_id.image_1920
        if not logo_b64:
            return ""

        if isinstance(logo_b64, str):
            logo_b64 = logo_b64.strip()
            if "," in logo_b64 and logo_b64.lower().startswith("data:image"):
                logo_b64 = logo_b64.split(",", 1)[1]

        try:
            raw = base64.b64decode(logo_b64)
            image = Image.open(io.BytesIO(raw)).convert("L")
            resampling = getattr(Image, "Resampling", Image)
            image.thumbnail((width, height), resampling.LANCZOS)
            bw_image = image.point(lambda x: 0 if x < 170 else 255, mode="1")

            img_width, img_height = bw_image.size
            bytes_per_row = math.ceil(img_width / 8)
            total_bytes = bytes_per_row * img_height

            pixels = bw_image.load()
            hex_rows = []
            for y in range(img_height):
                row_bytes = []
                for byte_index in range(bytes_per_row):
                    value = 0
                    for bit in range(8):
                        x = byte_index * 8 + bit
                        if x < img_width:
                            pixel = pixels[x, y]
                            if pixel == 0:
                                value |= 1 << (7 - bit)
                    row_bytes.append(f"{value:02X}")
                hex_rows.append("".join(row_bytes))

            data = "".join(hex_rows)
            return f"^FO20,20^GFA,{total_bytes},{total_bytes},{bytes_per_row},{data}^FS"
        except Exception:
            return ""
