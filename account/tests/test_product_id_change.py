from openerp.tests.common import TransactionCase

class TestProductIdChange(TransactionCase):
    """Test for product_id_change on account.invoice.line
    """

    def setUp(self):
        super(TestProductIdChange, self).setUp()
        self.line_model = self.registry('account.invoice.line')

    def get_line(self):
        line_id = self.line_model.create(
                self.cr,
                self.uid,
                {
                    'name': 'testline',
                })
        return self.line_model.browse(
                self.cr, self.uid, line_id)


    def get_partner(self):
        partner_id = self.registry('res.partner').search(
                self.cr,
                self.uid,
                [('customer', '=', True)],
                limit=1)[0]

        return self.registry('res.partner').browse(
                self.cr, self.uid, partner_id)

    def get_product(self):
        product_id = self.registry('product.product').search(
                self.cr,
                self.uid,
                [('uom_id', '!=', False)],
                limit=1)[0]
        return self.registry('product.product').browse(
                self.cr, self.uid, product_id)

    def test_random_product(self):
        line = self.get_line()
        product = self.get_product()
        partner = self.get_partner()

        values = line.product_id_change(
                product.id, None,
                partner_id=partner.id)['value']

        self.assertEquals(values['price_unit'], product.list_price)
        self.assertEquals(values['uos_id'], product.uom_id.id)

    def test_with_pricelist(self):
        line = self.get_line()
        product = self.get_product()

        pricelist_id = self.registry('product.pricelist').create(
                self.cr, 
                self.uid,
                {
                    'name': 'testpricelist',
                    'type': self.browse_ref('product.pricelist_type_sale').key,
                    'version_id': [
                        (0, 0, {
                            'name': 'testversion',
                            'items_id': [
                                (0, 0, {
                                    'name': 'testitem',
                                    'product_id': product.id,
                                    'price_discount': .5,
                                    'price_surcharge': 42,
                                    'base': self.browse_ref(
                                        'product.list_price').id,
                                    }),
                                ],
                            }),
                        ],
                })

        partner_id = self.registry('res.partner').create(
                self.cr,
                self.uid,
                {
                    'name': 'testcustomer',
                    'customer': True,
                    'property_product_pricelist':
                        'product.pricelist,%d' % pricelist_id,
                })

        values = line.product_id_change(
                product.id, None,
                partner_id=partner_id)['value']

        self.assertEquals(values['price_unit'], product.list_price * 1.5 + 42)
