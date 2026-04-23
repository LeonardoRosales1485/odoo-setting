{
    'name': 'BR Subscription',
    'version': '17.0.1.0.0',
    'summary': 'Servicios recurrentes mensuales/anuales con auto-orden',
    'author': 'MoP Tech',
    'depends': ['br_service_order', 'br_batisena'],
    'data': [
        'security/ir.model.access.csv',
        'data/br_subscription_cron.xml',
        'views/br_subscription_views.xml',
        'views/br_subscription_menus.xml',
    ],
    'installable': True,
    'auto_install': False,
}
