# -*- coding: utf-8 -*-
from odoo import fields, models, api


class Partner(models.Model):
    _inherit = 'res.partner'

    supplier_type = fields.Selection(string='Catégorie Fournisseur', selection=[('national', 'National'), ('international', 'International')])
    Expected_reception_period = fields.Integer('Période prévisionnel de réception')
