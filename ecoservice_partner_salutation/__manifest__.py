# Developed by ecodoo GmbH
# See COPYRIGHT and LICENSE files in the root directory of this module for full details.
{
    # App Information
    "name": "Partner Salutation",
    "summary": "Adds a salutation to the partner title.",
    "category": "Base",
    "version": "19.0.1.0.0",
    "license": "OPL-1",
    "application": False,
    "installable": True,
    # Author
    "author": "ecodoo GmbH",
    "website": "https://ecodoo.eu",
    'live_test_url': 'https://www.ecoservice.de/odoo-demo',
    'images': [
        'images/main_screenshot.gif',
    ],
    # Dependencies
    "depends": [
        "contacts",
    ],
    # Data
    "data": [
        'security/ir.model.access.csv',
        'static/src/sql/de.sql',
        'data/res_partner_data.xml',
        'views/res_partner.xml',
        'views/res_partner_title_view.xml',
    ],
}
