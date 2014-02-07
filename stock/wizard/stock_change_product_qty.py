# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp.osv import fields, osv, orm
import openerp.addons.decimal_precision as dp
from openerp.tools.translate import _
from openerp import tools

class stock_change_product_qty(osv.osv_memory):
    _name = "stock.change.product.qty"
    _description = "Change Product Quantity"
    _columns = {
        'product_id' : fields.many2one('product.product', 'Product'),
        'new_quantity': fields.float('New Quantity on Hand', digits_compute=dp.get_precision('Product Unit of Measure'), required=True, help='This quantity is expressed in the Default Unit of Measure of the product.'),
        'lot_id': fields.many2one('stock.production.lot', 'Serial Number', domain="[('product_id','=',product_id)]"),
        'location_id': fields.many2one('stock.location', 'Location', required=True, domain="[('usage', '=', 'internal')]"),
    }

    def default_get(self, cr, uid, fields, context):
        """ To get default values for the object.
         @param self: The object pointer.
         @param cr: A database cursor
         @param uid: ID of the user currently logged in
         @param fields: List of fields for which we want default values
         @param context: A standard dictionary
         @return: A dictionary which of fields with values.
        """
        product_id = context and context.get('active_id', False) or False
        res = super(stock_change_product_qty, self).default_get(cr, uid, fields, context=context)

        if 'new_quantity' in fields:
            res.update({'new_quantity': 1})
        if 'product_id' in fields:
            res.update({'product_id': product_id})
        if 'location_id' in fields:
            try:
                model, location_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'stock', 'stock_location_stock')
                self.pool.get('stock.location').check_access_rule(cr, uid, [location_id], 'read', context=context)
            except (orm.except_orm, ValueError):                
                location_id = False
            res.update({'location_id': location_id})
        return res

    def change_product_qty(self, cr, uid, ids, context=None):
        """ Changes the Product Quantity by making a Physical Inventory.
        @param self: The object pointer.
        @param cr: A database cursor
        @param uid: ID of the user currently logged in
        @param ids: List of IDs selected
        @param context: A standard dictionary
        @return:
        """
        if context is None:
            context = {}

        rec_id = context and context.get('active_id', False)
        assert rec_id, _('Active ID is not set in Context')

        inventory_obj = self.pool.get('stock.inventory')
        inventory_line_obj = self.pool.get('stock.inventory.line')
        prod_obj_pool = self.pool.get('product.product')

        res_original = prod_obj_pool.browse(cr, uid, rec_id, context=context)
        for data in self.browse(cr, uid, ids, context=context):
            if data.new_quantity < 0:
                raise osv.except_osv(_('Warning!'), _('Quantity cannot be negative.'))
            inventory_id = inventory_obj.create(cr , uid, {'name': _('INV: %s') % tools.ustr(res_original.name), 'product_id': rec_id, 'location_id': data.location_id.id, 'lot_id': data.lot_id.id}, context=context)
            line_data ={
                'inventory_id' : inventory_id,
                'product_qty' : data.new_quantity,
                'location_id' : data.location_id.id,
                'product_id' : rec_id,
                'product_uom_id' : res_original.uom_id.id,
                'prod_lot_id' : data.lot_id.id
            }
            inventory_line_obj.create(cr , uid, line_data, context=context)
            inventory_obj.action_done(cr, uid, [inventory_id], context=context)
        return {}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
