# -*- coding: utf-8 -*-
{
    'name': "Thorium",

    'summary': "Short (1 phrase/line) summary of the module's purpose",
    'description': """
        Long description of module's purpose
    """,
    'author': "ADG",
    'website': "https://odoo.adg.ci",
    'category': 'Uncategorized',
    'version': '0.1',

    'depends': ['base', 'purchase', 'purchase_requisition', 'contacts', 'mail', ],
    'data': [
        'security/groups.xml',
        'security/ir.model.access.csv',
        'views/purchase.xml',
        'views/purchase_requisition.xml',
        'views/report_purchaseorder_import.xml',
        'views/report_quotation_import.xml',
        'views/partner_view.xml',
        'views/validator.xml',
        'views/sequence_views.xml',
        'data/purchase_requisition_email.xml',
        'data/email_template_purchase.xml',
        'data/mail_template.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
    'installable': True,
    'application': True,
}
