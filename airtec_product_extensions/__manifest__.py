{
    "name": "Airtec Product Extensions",
    "version": "19.0.1.0.0",
    "category": "Product",
    "summary": "Product tags and Airtec-specific product fields",
    "author": "Airtec",
    "depends": ["product", "sale", "purchase", "stock"],
    "data": [
        #"security/ir.model.access.csv",
        #"views/product_tag_view.xml",
        "views/product_template_view.xml",
        "views/stock_lot_view.xml",
        "report/stock_lot_zpl_report.xml"
    ],
    "installable": True,
    "application": False
}