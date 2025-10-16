from odoo import models, fields, api
from odoo.exceptions import ValidationError


class CollectionSite(models.Model):
    _name = 'herbario.collection.site'
    _description = 'Ubicaciones de Recolección de Especímenes'
    _inherit = ['mail.thread', 'mail.activity.mixin'] 
    _order = 'fecha_recoleccion desc, id desc'

    # Relación con espécimen
    specimen_id = fields.Many2one(
        'herbario.specimen',
        string='Espécimen',
        required=True,
        ondelete='cascade',
        index=True
    )

    # Información de colección
    numero_coleccion = fields.Char(
        string='Número de Colección',
        help='Número de colección del colector'
    )
    colector = fields.Char(
        string='Colector',
        required=True,
        index=True,
        help='Nombre del colector'
    )
    fecha_recoleccion = fields.Date(
        string='Fecha de Recolección',
        required=True,
        index=True,
        default=fields.Date.context_today
    )
    metodo_recoleccion = fields.Char(
        string='Método de Recolección',
        help='Método utilizado para la recolección'
    )

    # Ubicación Geográfica
    pais = fields.Char(
        string='País',
        required=True,
        default='Ecuador'
    )
    provincia = fields.Char(
        string='Provincia',
        required=True,
        index=True
    )
    canton = fields.Char(
        string='Cantón (Lower Political)',
        help='Cantón o división política menor'
    )
    localidad = fields.Text(
        string='Localidad',
        required=True,
        help='Lugar específico de recolección'
    )
    vecindad = fields.Char(
        string='Vecindad',
        help='Vecindad o comunidad cercana'
    )

    # Coordenadas GPS
    latitud = fields.Float(
        string='Latitud',
        digits=(10, 7),
        index=True,
        help='Coordenada GPS latitud (formato decimal)'
    )
    longitud = fields.Float(
        string='Longitud',
        digits=(10, 7),
        index=True,
        help='Coordenada GPS longitud (formato decimal)'
    )
    altitud = fields.Integer(
        string='Altitud (m.s.n.m.)',
        help='Elevación en metros sobre el nivel del mar'
    )
    maps_url = fields.Char(
        string='URL de Google Maps',
        compute='_compute_maps_url',
        store=True,
        help='URL generada automáticamente para Google Maps'
    )

    # Campos de control
    is_primary = fields.Boolean(
        string='Ubicación Principal',
        default=False,
        help='Marca si es la ubicación principal o tipo del espécimen'
    )

    # Auditoría
    created_by = fields.Many2one(
        'res.users',
        string='Registrado Por',
        default=lambda self: self.env.user,
        readonly=True
    )
    created_at = fields.Datetime(
        string='Fecha de Registro',
        default=fields.Datetime.now,
        readonly=True
    )

    # Campo computado para mostrar ubicación completa
    ubicacion_completa = fields.Char(
        string='Ubicación Completa',
        compute='_compute_ubicacion_completa',
        store=True
    )

    @api.depends('localidad', 'provincia', 'pais')
    def _compute_ubicacion_completa(self):
        """Genera una cadena con la ubicación completa"""
        for record in self:
            parts = []
            if record.localidad:
                parts.append(record.localidad)
            if record.canton:
                parts.append(record.canton)
            if record.provincia:
                parts.append(record.provincia)
            if record.pais:
                parts.append(record.pais)
            record.ubicacion_completa = ', '.join(parts)

    @api.depends('latitud', 'longitud')
    def _compute_maps_url(self):
        """Genera URL de Google Maps automáticamente"""
        for record in self:
            if record.latitud and record.longitud:
                record.maps_url = f"https://maps.google.com/?q={record.latitud},{record.longitud}"
            else:
                record.maps_url = False

    @api.constrains('latitud')
    def _check_latitud(self):
        """Valida que la latitud esté en rango válido"""
        for record in self:
            if record.latitud and (record.latitud < -90 or record.latitud > 90):
                raise ValidationError('La latitud debe estar entre -90 y 90 grados.')

    @api.constrains('longitud')
    def _check_longitud(self):
        """Valida que la longitud esté en rango válido"""
        for record in self:
            if record.longitud and (record.longitud < -180 or record.longitud > 180):
                raise ValidationError('La longitud debe estar entre -180 y 180 grados.')

    @api.constrains('altitud')
    def _check_altitud(self):
        """Valida que la altitud sea razonable"""
        for record in self:
            if record.altitud and (record.altitud < -500 or record.altitud > 9000):
                raise ValidationError('La altitud debe estar entre -500 y 9000 m.s.n.m.')

    @api.model
    def create(self, vals):
        """Override para registrar en historial y manejar ubicación principal"""
        # Si es la primera ubicación del espécimen, marcarla como principal
        if vals.get('specimen_id'):
            existing_sites = self.search([('specimen_id', '=', vals['specimen_id'])])
            if not existing_sites:
                vals['is_primary'] = True
        
        # Si se marca como principal, desmarcar las demás
        if vals.get('is_primary') and vals.get('specimen_id'):
            self.search([
                ('specimen_id', '=', vals['specimen_id']),
                ('is_primary', '=', True)
            ]).write({'is_primary': False})
        
        record = super(CollectionSite, self).create(vals)
        
        # Registrar en historial
        self.env['herbario.history.log'].create({
            'specimen_id': record.specimen_id.id,
            'entity_type': 'collection_site',
            'entity_id': record.id,
            'action_type': 'location_added',
            'field_modified': None,
            'old_value': None,
            'new_value': f'Nueva ubicación: {record.ubicacion_completa}',
            'user_id': self.env.user.id,
            'user_name': self.env.user.name,
        })
        
        return record

    def write(self, vals):
        """Override para manejar cambio de ubicación principal"""
        if vals.get('is_primary'):
            for record in self:
                # Desmarcar otras ubicaciones principales del mismo espécimen
                self.search([
                    ('specimen_id', '=', record.specimen_id.id),
                    ('id', '!=', record.id),
                    ('is_primary', '=', True)
                ]).write({'is_primary': False})
        
        return super(CollectionSite, self).write(vals)

    def action_set_as_primary(self):
        """Acción para marcar como ubicación principal"""
        self.ensure_one()
        # Desmarcar otras ubicaciones principales
        self.search([
            ('specimen_id', '=', self.specimen_id.id),
            ('id', '!=', self.id),
            ('is_primary', '=', True)
        ]).write({'is_primary': False})
        # Marcar esta como principal
        self.write({'is_primary': True})

    def action_open_in_maps(self):
        """Acción para abrir en Google Maps"""
        self.ensure_one()
        if self.maps_url:
            return {
                'type': 'ir.actions.act_url',
                'url': self.maps_url,
                'target': 'new',
            }
        else:
            raise ValidationError('Esta ubicación no tiene coordenadas GPS registradas.')

    def name_get(self):
        """Personaliza el nombre mostrado"""
        result = []
        for record in self:
            name = f"{record.localidad}, {record.provincia} ({record.fecha_recoleccion})"
            if record.is_primary:
                name = f"⭐ {name}"
            result.append((record.id, name))
        return result