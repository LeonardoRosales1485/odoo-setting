{
    'name': 'BR Service Order',
    'version': '17.0.1.0.0',
    'summary': 'Órdenes de servicio Botón Rojo — FSM 9 estados',
    'author': 'MoP Tech',
    'depends': ['contacts', 'br_provider_score'],
    'data': [
        'data/br_service_order_data.xml',
        'security/ir.model.access.csv',
        'views/br_service_order_views.xml',
        'views/br_service_order_menus.xml',
    ],
    'installable': True,
    'auto_install': False,
}