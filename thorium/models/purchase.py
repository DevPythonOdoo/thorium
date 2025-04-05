# -*- coding: utf-8 -*-
import time

from odoo import fields, models, api, _
from odoo.exceptions import UserError, ValidationError


class PurchaseOrder(models.Model):
    _name = 'purchase.order'
    _inherit = 'purchase.order'
    _description = 'Description'

    state = fields.Selection([
        ('draft', 'Demande de prix'),
        ('sent', 'Envoyé'),
        ('submit', 'Responsable Achat'),
        ('approved', 'DG'),
        ('to_approve', 'A approuver'),
        ('purchase', 'Bon de commande'),
        ('done', 'Bloqué'),
        ('cancel', 'Annulé')
    ], string='Status', readonly=True, index=True, copy=False, default='draft', tracking=True)

    type = fields.Selection(
        string=_('type'),
        selection=[
            ('local', 'local'),
            ('import', 'Import'),
        ], default='local'
    )
    date_of_availability = fields.Datetime(string='Date de mise à disposition', required=False)
    estimated_arrival_date = fields.Datetime(string="Date estimative d'arrivée", required=False)
    validator_id = fields.Many2one(comodel_name="hr.employee", string="Validateur", readonly=True)
    approve_id = fields.Many2one(comodel_name="hr.employee", string="Approbateur", readonly=True)
    date_validation = fields.Datetime(string='Date de validation', required=False, readonly=True, copy=False)
    date_approve = fields.Datetime(string="Date d'approbation", required=False, readonly=True, copy=False)

    def _prepare_picking(self):
        self.ensure_one()
        warehouse = self.picking_type_id.warehouse_id

        # Définir reception_steps en fonction du type d'achat
        if self.type == 'import':
            warehouse.reception_steps = 'three_steps'
        else:
            warehouse.reception_steps = 'one_step'

        # Recherche du type d'opération de réception approprié
        picking_type = self.env['stock.picking.type'].search([
            ('code', '=', 'incoming'),
            ('warehouse_id', '=', warehouse.id),
            ('name', '=', 'Réception Import' if self.type == 'import' else 'Réception Local')
        ], limit=1)

        return {
            'partner_id': self.partner_id.id,
            'picking_type_id': picking_type.id,
            'origin': self.name,
            'location_id': picking_type.default_location_src_id.id,
            'location_dest_id': picking_type.default_location_dest_id.id,
        }

    @api.model
    @api.model_create_multi
    def create(self, vals_list):
        orders = self.env['purchase.order']
        partner_vals_list = []
        for vals in vals_list:
            # Affectation des validateurs
            validators = self.env['expense.validator'].search([('company_id', '=', self.env.company.id)])
            if validators:
                for user in validators:
                    if user.type_validator == 'purchase':
                        vals['validator_id'] = user.user_id.id
                    if user.type_validator == 'dg':
                        vals['approve_id'] = user.user_id.id

            # Génération du numéro de commande
            company_id = vals.get('company_id', self.default_get(['company_id'])['company_id'])
            self_comp = self.with_company(company_id)
            if vals.get('name', 'New') == 'New':
                seq_date = None
                if 'date_order' in vals:
                    seq_date = fields.Datetime.context_timestamp(self, fields.Datetime.to_datetime(vals['date_order']))
                if vals.get('type') == 'import':
                    vals['name'] = self_comp.env['ir.sequence'].next_by_code('purchase.import', sequence_date=seq_date)
                else:
                    vals['name'] = self_comp.env['ir.sequence'].next_by_code('purchase.order', sequence_date=seq_date) or '/'

            # Traitement des valeurs pour les partenaires
            vals, partner_vals = self._write_partner_values(vals)
            partner_vals_list.append(partner_vals)
            orders |= super(PurchaseOrder, self_comp).create(vals)

        # Mise à jour des valeurs partenaires en mode sudo (pour les droits)
        for order, partner_vals in zip(orders, partner_vals_list):
            if partner_vals:
                order.sudo().write(partner_vals)

        return orders

    def action_rfq_send(self):
        '''
        This function opens a window to compose an email, with the edi purchase template message loaded by default
        '''
        self.ensure_one()
        ir_model_data = self.env['ir.model.data']

        # Vérifier si le type est 'local' ou 'import'
        if self.type == 'local':
            template_ref_rfq = 'purchase.email_template_edi_purchase'
            template_ref_done = 'purchase.email_template_edi_purchase_done'
        else:  # Si c'est 'import'
            template_ref_rfq = 'thorium.email_template_edi_purchase_import'
            template_ref_done = 'thorium.email_template_edi_purchase_done_import'

        try:
            if self.env.context.get('send_rfq', False):
                template_id = ir_model_data._xmlid_lookup(template_ref_rfq)[1]
            else:
                template_id = ir_model_data._xmlid_lookup(template_ref_done)[1]
        except ValueError:
            template_id = False

        try:
            compose_form_id = ir_model_data._xmlid_lookup('mail.email_compose_message_wizard_form')[1]
        except ValueError:
            compose_form_id = False

        ctx = dict(self.env.context or {})
        ctx.update({
            'default_model': 'purchase.order',
            'default_res_ids': self.ids,
            'default_template_id': template_id,
            'default_composition_mode': 'comment',
            'default_email_layout_xmlid': "mail.mail_notification_layout_with_responsible_signature",
            'force_email': True,
            'mark_rfq_as_sent': True,
        })

        lang = self.env.context.get('lang')
        if {'default_template_id', 'default_model', 'default_res_id'} <= ctx.keys():
            template = self.env['mail.template'].browse(ctx['default_template_id'])
            if template and template.lang:
                lang = template._render_lang([ctx['default_res_id']])[ctx['default_res_id']]

        self = self.with_context(lang=lang)
        if self.state in ['draft', 'sent']:
            ctx['model_description'] = _('Request for Quotation')
        else:
            ctx['model_description'] = _('Purchase Order')

        return {
            'name': _('Compose Email'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(compose_form_id, 'form')],
            'view_id': compose_form_id,
            'target': 'new',
            'context': ctx,
        }


    def button_action_submit(self):
        for purchase in self:
            if purchase.state == "draft":
                purchase.write({'state': 'submit'})

    def button_confirm(self):
        for order in self:
            if order.state not in ['draft', 'sent', 'submit','approve']:
                continue
            order.order_line._validate_analytic_distribution()
            order._add_supplier_to_product()
            # Deal with double validation process
            if order._approval_allowed():
                order.button_approve()
            else:
                order.write({'state': 'purchase'})
            if order.partner_id not in order.message_partner_ids:
                order.message_subscribe([order.partner_id.id])
        return True

    def button_action_approuve_daf(self):
        check_config = self.env['res.config.settings'].search([], limit=1)
        print(check_config)
        for rec in self :
            if rec.state == "submit":
                if rec.validator_id.user_id.id != self._uid:
                    raise ValidationError(
                        "Vous n'êtes pas autorisé à valider cette commande ! Merci de contacter l'Administrateur en cas d'erreur.")
                if rec.amount_total >= rec.company_id.cash_amount:
                    mail_template = self.env.ref('thorium.email_template_management_dg')
                    mail_template.send_mail(self.id, force_send=True)
                    self.write({'state': 'approved', 'date_validation': time.strftime('%Y-%m-%d %H:%M:%S')})
                rec.button_confirm()
            else:
                for rec in self:
                    rec.button_confirm()

    def action_submit(self):
        return self.send_email()



    def button_confirm_test(self):
        for order in self:
            if order.state != 'approved':
                continue
            if order.approve_id.user_id.id != self._uid:
                raise ValidationError(
                    "Vous n'êtes pas autorisé à approuver cette commande  ! Merci de contacter l'Administrateur en cas d'erreur.")
            order.order_line._validate_analytic_distribution()
            order._add_supplier_to_product()
            # Deal with double validation process
            if order._approval_allowed():
                order.button_approve()
            else:
                order.write({'state': 'purchase', 'date_approve': time.strftime('%Y-%m-%d %H:%M:%S')})
            if order.partner_id not in order.message_partner_ids:
                order.message_subscribe([order.partner_id.id])
        return True




class PurchaseRequisition(models.Model):
    _inherit = 'purchase.requisition'

    state = fields.Selection(
        selection=[
            ('draft', 'Nouveau'),
            ('submit', 'Confirmé'),
            ('confirmed', 'Sélection des offres'),
            ('done', 'Fait'),
            ('cancel', 'Annulé')
        ],
        string='Status', tracking=True,
        copy=False, default='draft')


    def action_confirm(self):
        super(PurchaseRequisition, self).action_confirm()  # Conserver la logique originale
        self.ensure_one()
        mail_template = self.env.ref('thorium.email_template_submit')
        mail_template.send_mail(self.id, force_send=True)
        # Votre logique...
        self.state = 'confirmed'

    def action_submit(self):
        for rec in self:
            attachments = self.env['ir.attachment'].search([
                ('res_model', '=', rec._name),
                ('res_id', '=', rec.id)
            ])
            if not attachments:
                raise UserError(_("Veuillez ajouter au moins une pièce jointe avant de soumettre cette demande."))
        self.state = 'submit'
        mail_template = self.env.ref('thorium.email_template_draft')
        mail_template.send_mail(self.id, force_send=True)


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    # Redéfinition des champs pour qu'ils utilisent bien notre nouvelle méthode de calcul
    price_subtotal = fields.Monetary(compute='_compute_amount', store=True)
    price_total = fields.Monetary(compute='_compute_amount', store=True)
    price_tax = fields.Monetary(compute='_compute_amount', store=True)

    estimated_cost = fields.Monetary(string='Coût prévisionnel', required=False)
    container_number = fields.Char(string='Numéro de conteneur', required=False)

    @api.depends('product_qty', 'price_unit', 'taxes_id', 'estimated_cost')
    def _compute_amount(self):
        for line in self:
            currency = line.order_id.currency_id or line.company_id.currency_id
            # Calcul du prix de base incluant le coût prévisionnel
            base_price = (line.price_unit * line.product_qty) + (line.estimated_cost or 0.0)
            # Calcul des taxes sur ce montant avec quantité = 1
            taxes = line.taxes_id.compute_all(
                base_price,
                currency,
                1.0,  # Quantité fixée à 1 car base_price est déjà le total
                product=line.product_id,
                partner=line.order_id.partner_id
            )
            # Mise à jour des montants
            line.price_subtotal = taxes['total_excluded']
            line.price_total = taxes['total_included']
            line.price_tax = taxes['total_included'] - taxes['total_excluded']

    def _prepare_base_line_for_taxes_computation(self):
        res = super()._prepare_base_line_for_taxes_computation()
        # On injecte le coût prévisionnel dans le prix unitaire
        if self.estimated_cost:
            # Le montant est global, on le ramène à l’unité
            estimated_unit_cost = self.estimated_cost / self.product_qty if self.product_qty else 0.0
            res['price_unit'] += estimated_unit_cost
        return res
