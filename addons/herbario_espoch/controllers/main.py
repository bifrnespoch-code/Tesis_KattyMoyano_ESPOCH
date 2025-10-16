from odoo import http
from odoo.http import request
import json
import base64


class HerbarioController(http.Controller):

    # ==================== PÁGINA PRINCIPAL ====================
    
    @http.route(['/herbario', '/herbario/'], type='http', auth='public', website=True)
    def herbario_home(self, **kw):
        """Página principal del herbario"""
        Specimen = request.env['herbario.specimen'].sudo()
        
        # Estadísticas generales
        total_specimens = Specimen.search_count([('es_publico', '=', True), ('status', '=', 'activo')])
        total_families = len(Specimen.search([('es_publico', '=', True), ('status', '=', 'activo')]).mapped('familia'))
        total_images = request.env['herbario.image'].sudo().search_count([
            ('specimen_id.es_publico', '=', True),
            ('deleted_at', '=', False)
        ])
        
        # Últimos especímenes agregados
        recent_specimens = Specimen.search([
            ('es_publico', '=', True),
            ('status', '=', 'activo')
        ], limit=6, order='created_at desc')
        
        return request.render('herbario_espoch.herbario_home', {
            'total_specimens': total_specimens,
            'total_families': total_families,
            'total_images': total_images,
            'recent_specimens': recent_specimens,
        })

    # ==================== ESTADÍSTICAS ====================
    
    @http.route(['/herbario/estadisticas'], type='http', auth='public', website=True)
    def herbario_stats(self, **kw):
        """Página de estadísticas con gráficos"""
        Specimen = request.env['herbario.specimen'].sudo()
        CollectionSite = request.env['herbario.collection.site'].sudo()
        
        specimens = Specimen.search([('es_publico', '=', True), ('status', '=', 'activo')])
        
        # Estadísticas generales
        stats = {
            'total_specimens': len(specimens),
            'total_families': len(specimens.mapped('familia')),
            'total_genera': len(specimens.mapped('genero')),
            'total_species': len(specimens.mapped('especie')),
            'total_locations': CollectionSite.search_count([('specimen_id.es_publico', '=', True)]),
            'total_images': request.env['herbario.image'].sudo().search_count([
                ('specimen_id.es_publico', '=', True),
                ('deleted_at', '=', False)
            ]),
        }
        
        # Top 10 familias más representadas
        families_data = {}
        for spec in specimens:
            families_data[spec.familia] = families_data.get(spec.familia, 0) + 1
        top_families = sorted(families_data.items(), key=lambda x: x[1], reverse=True)[:10]
        
        # Especímenes por provincia
        locations = CollectionSite.search([('specimen_id.es_publico', '=', True)])
        provinces_data = {}
        for loc in locations:
            provinces_data[loc.provincia] = provinces_data.get(loc.provincia, 0) + 1
        top_provinces = sorted(provinces_data.items(), key=lambda x: x[1], reverse=True)[:10]
        
        # Especímenes por año de recolección
        years_data = {}
        for loc in locations:
            if loc.fecha_recoleccion:
                year = loc.fecha_recoleccion.year
                years_data[year] = years_data.get(year, 0) + 1
        years_sorted = sorted(years_data.items())
        
        # Coordenadas para el mapa
        map_locations = []
        for loc in locations:
            if loc.latitud and loc.longitud:
                map_locations.append({
                    'lat': loc.latitud,
                    'lng': loc.longitud,
                    'name': loc.specimen_id.nombre_cientifico,
                    'locality': loc.localidad,
                    'provincia': loc.provincia,
                })
        
        return request.render('herbario_espoch.herbario_statistics', {
            'stats': stats,
            'top_families': top_families,
            'top_provinces': top_provinces,
            'years_data': years_sorted,
            'map_locations': json.dumps(map_locations),
        })

    # ==================== REPOSITORIO CON FILTROS ====================
    @http.route([
        '/herbario/repositorio',
        '/herbario/repositorio/page/<int:page>'
    ], type='http', auth='public', website=True)
    def herbario_repository(self, page=1, search='', familia='', genero='', 
                           pais='', provincia='', localidad='', colector='', 
                           autor='', sort='', **kwargs):
        """Repositorio con filtros avanzados"""
        
        Specimen = request.env['herbario.specimen'].sudo()
        
        # Construir dominio de búsqueda
        domain = [('es_publico', '=', True), ('status', '=', 'activo')]
        
        if search:
            domain += ['|', '|',
                      ('nombre_cientifico', 'ilike', search),
                      ('familia', 'ilike', search),
                      ('genero', 'ilike', search)]
        
        if familia:
            domain += [('familia', '=', familia)]
        
        if genero:
            domain += [('genero', '=', genero)]
        
        if autor:
            domain += [('autor_cientifico', 'ilike', autor)]
        
        # Filtros de ubicación
        if pais or provincia or localidad or colector:
            site_domain = []
            if pais:
                site_domain.append(('pais', '=', pais))
            if provincia:
                site_domain.append(('provincia', '=', provincia))
            if localidad:
                site_domain.append(('localidad', 'ilike', localidad))
            if colector:
                site_domain.append(('colector', 'ilike', colector))
            
            sites = request.env['herbario.collection.site'].sudo().search(site_domain)
            specimen_ids = sites.mapped('specimen_id').ids
            if specimen_ids:
                domain += [('id', 'in', specimen_ids)]
            else:
                domain += [('id', '=', False)]  # No results
        
        # Ordenamiento
        order = 'id desc'
        if sort == 'date_asc':
            order = 'id asc'
        elif sort == 'name_asc':
            order = 'nombre_cientifico asc'
        elif sort == 'name_desc':
            order = 'nombre_cientifico desc'
        elif sort == 'code_asc':
            order = 'codigo_herbario asc'
        
        # Obtener especímenes
        specimens_count = Specimen.search_count(domain)
        
        # Paginación
        per_page = 12
        pager = request.website.pager(
            url='/herbario/repositorio',
            total=specimens_count,
            page=page,
            step=per_page,
            url_args={'search': search, 'familia': familia, 'genero': genero,
                     'pais': pais, 'provincia': provincia, 'localidad': localidad,
                     'colector': colector, 'autor': autor, 'sort': sort}
        )
        
        specimens = Specimen.search(domain, limit=per_page, offset=pager['offset'], order=order)
        
        # Datos para filtros
        all_specimens = Specimen.search([('es_publico', '=', True), ('status', '=', 'activo')])
        families = sorted(set(all_specimens.mapped('familia')))
        genera = sorted(set(all_specimens.mapped('genero')))
        
        all_sites = request.env['herbario.collection.site'].sudo().search([])
        countries = sorted(set(all_sites.mapped('pais')))
        provinces = sorted(set(all_sites.mapped('provincia')))
        collectors = sorted(set(all_sites.mapped('colector')))
        
        return request.render('herbario_espoch.herbario_repository', {
            'specimens': specimens,
            'total_results': specimens_count,
            'pager': pager,
            'search': search,
            'familia': familia,
            'genero': genero,
            'pais': pais,
            'provincia': provincia,
            'localidad': localidad,
            'colector': colector,
            'autor': autor,
            'sort': sort,
            'families': families,
            'genera': genera,
            'countries': countries,
            'provinces': provinces,
            'collectors': collectors,
        })

    # ==================== GALERÍA ====================
    @http.route([
        '/herbario/galeria',
        '/herbario/galeria/page/<int:page>'
    ], type='http', auth='public', website=True)
    def herbario_gallery(self, page=1, search='', familia='', tipo_imagen='', **kwargs):
        """Galería de imágenes con filtros"""
        
        Image = request.env['herbario.image'].sudo()
        
        # Construir dominio
        domain = [('specimen_id.es_publico', '=', True), ('specimen_id.status', '=', 'activo')]
        
        if search:
            domain += [('specimen_id.nombre_cientifico', 'ilike', search)]
        
        if familia:
            domain += [('specimen_id.familia', '=', familia)]
        
        if tipo_imagen:
            domain += [('image_type', '=', tipo_imagen)]
        
        # Contar imágenes
        images_count = Image.search_count(domain)
        
        # Paginación
        per_page = 20
        pager = request.website.pager(
            url='/herbario/galeria',
            total=images_count,
            page=page,
            step=per_page,
            url_args={'search': search, 'familia': familia, 'tipo_imagen': tipo_imagen}
        )
        
        images = Image.search(domain, limit=per_page, offset=pager['offset'], order='id desc')
        
        # Datos para filtros
        all_specimens = request.env['herbario.specimen'].sudo().search([
            ('es_publico', '=', True), ('status', '=', 'activo')
        ])
        families = sorted(set(all_specimens.mapped('familia')))
        
        return request.render('herbario_espoch.herbario_gallery', {
            'images': images,
            'pager': pager,
            'search': search,
            'familia': familia,
            'tipo_imagen': tipo_imagen,
            'families': families,
        })

    # ==================== DETALLE DE ESPÉCIMEN ====================
    
    @http.route(['/herbario/specimen/<int:specimen_id>'], type='http', auth='public', website=True)
    def herbario_specimen_detail(self, specimen_id, **kw):
        """Página de detalle de un espécimen"""
        Specimen = request.env['herbario.specimen'].sudo()
        specimen = Specimen.browse(specimen_id)
        
        # Verificar que sea público
        if not specimen.exists() or not specimen.es_publico or specimen.status != 'activo':
            return request.redirect('/herbario/repositorio')
        
        # Registrar escaneo del QR si viene de QR
        if kw.get('from_qr'):
            qr_code = specimen.qr_code_id.filtered(lambda qr: not qr.obsolete)
            if qr_code:
                qr_code.register_scan()
        
        # Especímenes relacionados (misma familia)
        related_specimens = Specimen.search([
            ('familia', '=', specimen.familia),
            ('id', '!=', specimen.id),
            ('es_publico', '=', True),
            ('status', '=', 'activo')
        ], limit=4)
        
        return request.render('herbario_espoch.herbario_specimen_detail', {
            'specimen': specimen,
            'related_specimens': related_specimens,
        })

    # ==================== BÚSQUEDA AJAX ====================
    
    @http.route(['/herbario/api/search'], type='json', auth='public', methods=['POST'])
    def herbario_api_search(self, query, limit=10):
        """API de búsqueda para autocompletado"""
        Specimen = request.env['herbario.specimen'].sudo()
        
        domain = [
            ('es_publico', '=', True),
            ('status', '=', 'activo'),
            '|', '|', '|',
            ('nombre_cientifico', 'ilike', query),
            ('familia', 'ilike', query),
            ('genero', 'ilike', query),
            ('especie', 'ilike', query)
        ]
        
        specimens = Specimen.search(domain, limit=limit)
        
        results = []
        for spec in specimens:
            results.append({
                'id': spec.id,
                'nombre_cientifico': spec.nombre_cientifico,
                'familia': spec.familia,
                'codigo': spec.codigo_herbario,
                'url': f'/herbario/specimen/{spec.id}'
            })
        
        return results

    # ==================== ABOUT ====================
    
    @http.route(['/herbario/about'], type='http', auth='public', website=True)
    def herbario_about(self, **kw):
        """Página Acerca de"""
        return request.render('herbario_espoch.herbario_about', {})

    # ==================== EXPORTAR DATOS ====================
    
    @http.route(['/herbario/api/export/<string:format>'], type='http', auth='user', methods=['GET'])
    def herbario_export_data(self, format='csv', familia=None, **kw):
        """Exporta datos del herbario (requiere login)"""
        Specimen = request.env['herbario.specimen'].sudo()
        
        domain = [('es_publico', '=', True), ('status', '=', 'activo')]
        if familia:
            domain.append(('familia', '=', familia))
        
        specimens = Specimen.search(domain, order='codigo_herbario asc')
        
        if format == 'csv':
            return self._export_csv(specimens)
        elif format == 'json':
            return self._export_json(specimens)
        else:
            return request.redirect('/herbario/repositorio')

    def _export_csv(self, specimens):
        """Exporta a CSV"""
        import csv
        from io import StringIO
        
        output = StringIO()
        writer = csv.writer(output)
        
        # Encabezados
        headers = ['Código', 'Nombre Científico', 'Familia', 'Género', 'Especie', 
                  'Autor', 'Determinado Por', 'Descripción']
        writer.writerow(headers)
        
        # Datos
        for spec in specimens:
            writer.writerow([
                spec.codigo_herbario,
                spec.nombre_cientifico,
                spec.familia,
                spec.genero,
                spec.especie,
                spec.autor_cientifico or '',
                spec.determinado_por or '',
                spec.descripcion_especie or ''
            ])
        
        content = output.getvalue()
        output.close()
        
        return request.make_response(
            content,
            headers=[
                ('Content-Type', 'text/csv'),
                ('Content-Disposition', 'attachment; filename=herbario_espoch.csv')
            ]
        )

    def _export_json(self, specimens):
        """Exporta a JSON"""
        data = []
        for spec in specimens:
            data.append({
                'codigo_herbario': spec.codigo_herbario,
                'nombre_cientifico': spec.nombre_cientifico,
                'familia': spec.familia,
                'genero': spec.genero,
                'especie': spec.especie,
                'autor_cientifico': spec.autor_cientifico,
                'determinado_por': spec.determinado_por,
                'descripcion_especie': spec.descripcion_especie,
                'ubicaciones': [{
                    'localidad': loc.localidad,
                    'provincia': loc.provincia,
                    'pais': loc.pais,
                    'latitud': loc.latitud,
                    'longitud': loc.longitud,
                    'colector': loc.colector,
                    'fecha_recoleccion': str(loc.fecha_recoleccion) if loc.fecha_recoleccion else None
                } for loc in spec.collection_site_ids]
            })
        
        return request.make_response(
            json.dumps(data, indent=2),
            headers=[
                ('Content-Type', 'application/json'),
                ('Content-Disposition', 'attachment; filename=herbario_espoch.json')
            ]
        )
    
