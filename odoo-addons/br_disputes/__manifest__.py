{
    'name': 'BR Disputes',
    'version': '17.0.1.0.0',
    'summary': 'Disputas con SLA 48h — bloqueo de pago + escalada automática',
    'author': 'MoP Tech',
    'depends': ['br_service_order', 'br_mercadopago'],
    'data': [
        'security/ir.model.access.csv',
        'data/br_disputes_cron.xml',
        'views/br_dispute_views.xml',
        'views/br_dispute_menus.xml',
    ],
    'installable': True,
    'auto_install': False,
}
