{
    'name': 'BR MercadoPago',
    'version': '17.0.1.0.6',
    'summary': 'Pagos MercadoPago — escrow authorize/capture + split 85/15 + cobrador efectivo',
    'author': 'MoP Tech',
    'depends': ['br_service_order'],
    'data': [
        # 'data/mp_config_data.xml',
        'security/ir.model.access.csv',
        'data/mp_payment_fee_config_data.xml',
        # 'views/mp_config_views.xml',
        'views/mp_payment_fee_config_views.xml',
        'views/br_payment_views.xml',
        'views/br_payment_menus.xml',
    ],
    'installable': True,
    'auto_install': False,
}
