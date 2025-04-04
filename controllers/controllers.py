# -*- coding: utf-8 -*-
# from odoo import http


# class Thorium(http.Controller):
#     @http.route('/thorium/thorium', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/thorium/thorium/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('thorium.listing', {
#             'root': '/thorium/thorium',
#             'objects': http.request.env['thorium.thorium'].search([]),
#         })

#     @http.route('/thorium/thorium/objects/<model("thorium.thorium"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('thorium.object', {
#             'object': obj
#         })

