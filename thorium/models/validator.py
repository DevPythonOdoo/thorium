from odoo import fields, models, api
from odoo.exceptions import ValidationError




class CashValidator(models.Model):
    _name = 'expense.validator'
    _description = 'Expense Validateurs'

    user_id = fields.Many2one(comodel_name="hr.employee", string="Employee", required=True)
    company_id = fields.Many2one('res.company', 'Société', readonly=True, required=True, index=True,
                                 default=lambda self: self.env.company)
    type_validator = fields.Selection(string="Type validation", selection=[
        ('purchase', 'Service Achat'),
        ('daf', 'Direction Administrative et Financière'),
        ('dg', 'Direction Générale'),

    ], required=True)


    @api.model
    def create(self, vals):
        validators = self.search([('company_id', '=', self.env.company.id)])
        if validators:
            for validator in validators:
                if validator.type_validator == vals.get('type_validator'):
                    raise ValidationError(
                        'Vous ne pouvez pas definir le même niveau de validation [%s] une seconde fois de suite' % (
                            validator.type_validator))

        return super(CashValidator, self).create(vals)



class Company(models.Model):
    _inherit = 'res.company'

    cash_amount = fields.Monetary(string='Montant Minimum', default=10000, help="Tout montant d'une fiche superieur ou égale au montant spécifié ici sera soumis à l'approbation du directeur", store=True)

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    cash_amount = fields.Monetary(related='company_id.cash_amount', string="Montant Minimum",
                                  currency_field='company_currency_id', readonly=False, store=True,
                                  help="Tout montant d'une fiche superieur ou égale au montant spécifié ici sera soumis à l'approbation du directeur")
    company_currency_id = fields.Many2one('res.currency', related='company_id.currency_id', string="Company Currency",
                                          readonly=True)