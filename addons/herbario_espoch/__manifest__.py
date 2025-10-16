{
    'name': 'Herbario ESPOCH - Sistema Integral',
    'version': '1.0.0',
    'sequence': 10,
    'category': 'Education',
    'summary': 'Sistema de Gestión Integral de Registros Botánicos e Imágenes del Herbario ESPOCH',
    'description': """
        Sistema Completo de Gestión del Herbario ESPOCH
        ================================================
        
        Características principales:
        * Gestión completa de especímenes botánicos
        * Múltiples ubicaciones de recolección por espécimen
        * Galería de imágenes con EXIF
        * Generación automática de códigos QR
        * Sistema de auditoría completo
        * Búsqueda y filtros avanzados
        * Mapas de geolocalización
        * Estadísticas y reportes
        * Portal web público
        
        Desarrollado por: Katty Alexandra Moyano Ramos
        Director: Ing. Cristian Alexis García Pumagualle
        Institución: ESPOCH
    """,
    'author': 'Katty Alexandra Moyano Ramos',
    'website': 'https://www.espoch.edu.ec',
    'depends': ['base', 'web', 'website', 'mail'],
    'data': [
        # Seguridad
        'security/herbario_security.xml',
        'security/ir.model.access.csv',
        
        # Datos base
        'data/sequence_data.xml',
        
        # Reportes
        'reports/specimen_report.xml',
        
        # Vistas Backend
        'views/specimen_views.xml',
        'views/collection_site_views.xml',
        'views/image_views.xml',
        'views/qr_code_views.xml',
        'views/history_log_views.xml',
        'views/herbario_menus.xml',
        
        # Vistas Website
        'views/website_templates.xml',
        'views/website_menus.xml',
              
    ],
    'assets': {
        'web.assets_backend': [
            'herbario_espoch/static/src/css/herbario_backend.css',
            #'herbario_espoch/static/src/js/map_widget.js',
        ],
        'web.assets_frontend': [
            'herbario_espoch/static/src/css/herbario_frontend.css',
            'herbario_espoch/static/src/js/filters.js',
            'herbario_espoch/static/src/js/gallery.js',
            'herbario_espoch/static/src/js/maps.js',
        ],
    },
    'images': ['static/description/banner.png'],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}