{
    'name': 'Herbario Prueba',
    'version': '1.0',
    'summary': 'Gestión de un herbario virtual para especímenes de plantas',
    'description': """
        Módulo para registrar y gestionar especímenes botánicos en un herbario digital.
        Incluye campos para nombre científico, descripción, imagen y ubicación.
    """,
    'author': 'Tu Nombre',
    #'website': 'https://ejemplo.com',
    'category': 'Herramientas',
    'depends': ['base'],  # Depende solo de módulos base de Odoo
    'data': [
        'security/ir.model.access.csv',
        'views/especimen_views.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
