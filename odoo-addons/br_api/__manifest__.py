{
    'name': 'BR API',
    'version': '17.0.1.0.0',
    'summary': 'REST API + webhooks salientes — autenticación JWT y API Key',
    'author': 'MoP Tech',
    'depends': ['br_service_order', 'br_batisena', 'br_mercadopago'],
    'data': [
        'security/ir.model.access.csv',
        'views/br_api_views.xml',
        'views/br_api_menus.xml',
    ],
    'installable': True,
    'auto_install': False,
}
