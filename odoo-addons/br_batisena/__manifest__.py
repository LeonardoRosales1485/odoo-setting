{
    'name': 'BR Batiseñal',
    'version': '17.0.1.0.0',
    'summary': 'Cola inteligente de asignación de proveedores',
    'author': 'MoP Tech',
    'depends': ['br_service_order', 'br_provider_score'],
    'data': [
        'security/ir.model.access.csv',
        'views/br_batisena_views.xml',
        'views/br_batisena_menus.xml',
    ],
    'installable': True,
    'auto_install': False,
}
