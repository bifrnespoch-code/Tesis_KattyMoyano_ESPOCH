from odoo import models, fields, api
from odoo.exceptions import ValidationError
import re


class SpecimenRegistry(models.Model):
    _name = 'herbario.specimen'
    _description = 'Registro de Especímenes Botánicos'
    _order = 'codigo_herbario desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    # Identificación
    codigo_herbario = fields.Char(
        string='Código Herbario',
        required=True,
        index=True,
        copy=False,
        default=lambda self: self._get_next_code(),
        help='Código único CHEP-XXXXXXX'
    )
    numero_cartulina = fields.Integer(
        string='Número de Cartulina',
        index=True,
        help='Número físico de cartulina del herbario'
    )

    # Taxonomía
    nombre_cientifico = fields.Char(
        string='Nombre Científico (Taxón)',
        required=True,
        index=True,
        tracking=True,
        help='Nombre científico completo de la especie'
    )
    familia = fields.Char(
        string='Familia',
        required=True,
        index=True,
        tracking=True
    )
    genero = fields.Char(
        string='Género',
        compute='_compute_genero_especie',
        store=True,
        index=True
    )
    especie = fields.Char(
        string='Especie',
        compute='_compute_genero_especie',
        store=True,
        index=True
    )
    autor_cientifico = fields.Char(
        string='Autor Científico',
        help='Autor de la descripción científica'
    )

    # Identificación y Determinación
    determinado_por = fields.Char(
        string='Determinado Por',
        help='Persona que identificó el espécimen'
    )
    herbario_codigo = fields.Char(
        string='Código Herbario Externo',
        help='Código de herbario externo si aplica'
    )

    # Descripción
    descripcion_especie = fields.Text(
        string='Descripción de la Especie',
        help='Descripción botánica detallada'
    )
    fenologia = fields.Char(
        string='Fenología',
        help='Estado fenológico general (floración, fructificación, etc.)'
    )
    patente_year = fields.Integer(
        string='Año de Patente',
        help='Año de patente o registro oficial'
    )

    # Relaciones
    collection_site_ids = fields.One2many(
        'herbario.collection.site',
        'specimen_id',
        string='Ubicaciones de Recolección'
    )
    image_ids = fields.One2many(
        'herbario.image',
        'specimen_id',
        string='Imágenes'
    )
    qr_code_id = fields.One2many(
        'herbario.qr.code',
        'specimen_id',
        string='Código QR'
    )
    history_log_ids = fields.One2many(
        'herbario.history.log',
        'specimen_id',
        string='Historial de Cambios'
    )

    # Campos Computados
    total_ubicaciones = fields.Integer(
        string='Total de Ubicaciones',
        compute='_compute_total_ubicaciones',
        store=True
    )
    primary_image = fields.Binary(
        string='Imagen Principal',
        compute='_compute_primary_image'
    )
    primary_location = fields.Char(
        string='Ubicación Principal',
        compute='_compute_primary_location'
    )

    # Estado y Auditoría
    status = fields.Selection([
        ('borrador', 'Borrador'),
        ('revision', 'En Revisión'),
        ('activo', 'Activo'),
        ('archivado', 'Archivado'),
        ('eliminado', 'Eliminado')
    ], string='Estado', default='borrador', required=True, index=True, tracking=True)

    # Campos de auditoría
    created_by = fields.Many2one('res.users', string='Creado Por', default=lambda self: self.env.user, readonly=True)
    created_at = fields.Datetime(string='Fecha de Creación', default=fields.Datetime.now, readonly=True)
    updated_by = fields.Many2one('res.users', string='Modificado Por')
    updated_at = fields.Datetime(string='Última Modificación')

    # Campos para el sitio web
    es_publico = fields.Boolean(string='Visible en Web', default=True)

    _sql_constraints = [
        ('codigo_herbario_unique', 'UNIQUE(codigo_herbario)', 'El código de herbario debe ser único.'),
    ]

    @api.model
    def _get_next_code(self):
        """Genera el siguiente código CHEP-XXXXXXX"""
        sequence = self.env['ir.sequence'].next_by_code('herbario.specimen.code') or '0000001'
        return f'CHEP-{sequence}'

    @api.depends('nombre_cientifico')
    def _compute_genero_especie(self):
        """Extrae género y especie del nombre científico"""
        for record in self:
            if record.nombre_cientifico:
                parts = record.nombre_cientifico.split()
                record.genero = parts[0] if len(parts) > 0 else ''
                record.especie = parts[1] if len(parts) > 1 else ''
            else:
                record.genero = ''
                record.especie = ''

    @api.depends('collection_site_ids')
    def _compute_total_ubicaciones(self):
        """Calcula el total de ubicaciones registradas"""
        for record in self:
            record.total_ubicaciones = len(record.collection_site_ids)

    @api.depends('image_ids.is_primary')
    def _compute_primary_image(self):
        """Obtiene la imagen principal"""
        for record in self:
            primary_img = record.image_ids.filtered(lambda img: img.is_primary)
            if primary_img:
                record.primary_image = primary_img[0].image_data
            elif record.image_ids:
                record.primary_image = record.image_ids[0].image_data
            else:
                record.primary_image = False

    @api.depends('collection_site_ids.is_primary')
    def _compute_primary_location(self):
        """Obtiene la ubicación principal"""
        for record in self:
            primary_site = record.collection_site_ids.filtered(lambda site: site.is_primary)
            if primary_site:
                record.primary_location = f"{primary_site[0].localidad}, {primary_site[0].provincia}"
            elif record.collection_site_ids:
                record.primary_location = f"{record.collection_site_ids[0].localidad}, {record.collection_site_ids[0].provincia}"
            else:
                record.primary_location = 'Sin ubicación registrada'

    @api.constrains('nombre_cientifico', 'familia')
    def _check_unique_specimen(self):
        """Evita duplicados por nombre científico + familia"""
        for record in self:
            duplicate = self.search([
                ('id', '!=', record.id),
                ('nombre_cientifico', '=', record.nombre_cientifico),
                ('familia', '=', record.familia)
            ], limit=1)
            if duplicate:
                raise ValidationError(
                    f'Ya existe un espécimen con el nombre científico "{record.nombre_cientifico}" '
                    f'y familia "{record.familia}" (Código: {duplicate.codigo_herbario})'
                )

    def write(self, vals):
        """Override para registrar cambios en el historial"""
        vals['updated_by'] = self.env.user.id
        vals['updated_at'] = fields.Datetime.now()
        
        # Registrar cambios en history_log
        tracked_fields = ['nombre_cientifico', 'familia', 'genero', 'especie', 'status']
        for record in self:
            for field in tracked_fields:
                if field in vals and vals[field] != record[field]:
                    self.env['herbario.history.log'].create({
                        'specimen_id': record.id,
                        'entity_type': 'specimen',
                        'entity_id': record.id,
                        'action_type': 'updated',
                        'field_modified': field,
                        'old_value': str(record[field]) if record[field] else '',
                        'new_value': str(vals[field]) if vals[field] else '',
                        'user_id': self.env.user.id,
                        'user_name': self.env.user.name,
                    })
        
        return super(SpecimenRegistry, self).write(vals)

    @api.model
    def create(self, vals):
        """Override para registrar creación en el historial"""
        if not vals.get('codigo_herbario'):
            vals['codigo_herbario'] = self._get_next_code()
        record = super(SpecimenRegistry, self).create(vals)
        
        # Registrar creación en history_log
        self.env['herbario.history.log'].create({
            'specimen_id': record.id,
            'entity_type': 'specimen',
            'entity_id': record.id,
            'action_type': 'created',
            'field_modified': None,
            'old_value': None,
            'new_value': f'Espécimen creado: {record.nombre_cientifico}',
            'user_id': self.env.user.id,
            'user_name': self.env.user.name,
        })
        
        return record

    def unlink(self):
        """Override para registrar eliminación en el historial"""
        for record in self:
            self.env['herbario.history.log'].create({
                'specimen_id': record.id,
                'entity_type': 'specimen',
                'entity_id': record.id,
                'action_type': 'deleted',
                'field_modified': None,
                'old_value': f'Código: {record.codigo_herbario}',
                'new_value': None,
                'user_id': self.env.user.id,
                'user_name': self.env.user.name,
            })
        return super(SpecimenRegistry, self).unlink()

    def action_generate_qr(self):
        """Acción para generar código QR"""
        self.ensure_one()
        return self.env['herbario.qr.code'].generate_qr_for_specimen(self)

    def action_view_history(self):
        """Acción para ver historial de cambios"""
        self.ensure_one()
        return {
            'name': f'Historial de {self.codigo_herbario}',
            'type': 'ir.actions.act_window',
            'res_model': 'herbario.history.log',
            'view_mode': 'tree',
            'domain': [('specimen_id', '=', self.id)],
            'context': {'default_specimen_id': self.id}
        }

    def name_get(self):
        """Personaliza el nombre mostrado"""
        result = []
        for record in self:
            name = f"{record.codigo_herbario} - {record.nombre_cientifico}"
            result.append((record.id, name))
        return result