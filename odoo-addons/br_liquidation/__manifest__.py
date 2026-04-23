{
    'name': 'BR Liquidation',
    'version': '17.0.1.0.0',
    'summary': 'Liquidación semanal de proveedores — cron jueves 18h',
    'author': 'MoP Tech',
    'depends': ['br_service_order', 'br_mercadopago'],
    'data': [
        'security/ir.model.access.csv',
        'data/br_liquidation_cron.xml',
        'views/br_liquidation_views.xml',
        'views/br_liquidation_menus.xml',
    ],
    'installable': True,
    'auto_install': False,
}
