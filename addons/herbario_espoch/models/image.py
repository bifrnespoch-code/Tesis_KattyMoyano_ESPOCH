from odoo import models, fields, api
from odoo.exceptions import ValidationError
import base64
import hashlib
import os
from PIL import Image
from io import BytesIO
import json

class HerbarioImage(models.Model):
    _name = 'herbario.image'
    _description = 'Imágenes de Especímenes Botánicos'
    _order = 'display_order asc, id asc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    # Relación con espécimen
    specimen_id = fields.Many2one(
        'herbario.specimen',
        string='Espécimen',
        required=True,
        ondelete='cascade',
        index=True
    )

    # Información del archivo
    filename_original = fields.Char(
        string='Nombre Original',
        required=True,
        help='Nombre original del archivo subido'
    )
    filename_stored = fields.Char(
        string='Nombre Almacenado',
        help='Nombre UUID del archivo almacenado'
    )
    
    # Imagen y datos binarios
    image_data = fields.Binary(
        string='Imagen',
        attachment=True,
        required=True
    )
    thumbnail = fields.Binary(
        string='Miniatura Pequeña',
        compute='_compute_thumbnails',
        store=True,
        readonly=True
    )
    thumbnail_medium = fields.Binary(
        string='Miniatura Mediana',
        compute='_compute_thumbnails',
        store=True,
        readonly=True
    )
    
    # Metadatos del archivo
    file_size = fields.Integer(
        string='Tamaño (bytes)',
        compute='_compute_file_metadata',
        store=True,
        help='Tamaño del archivo en bytes'
    )
    image_width = fields.Integer(
        string='Ancho (px)',
        compute='_compute_file_metadata',
        store=True
    )
    image_height = fields.Integer(
        string='Alto (px)',
        compute='_compute_file_metadata',
        store=True
    )
    mime_type = fields.Char(
        string='Tipo MIME',
        default='image/jpeg',
        help='Tipo MIME del archivo'
    )
    file_hash = fields.Char(
        string='Hash SHA-256',
        compute='_compute_file_hash',
        store=True,
        index=True,
        help='Hash para detección de duplicados'
    )
    
    # Datos EXIF
    exif_data = fields.Text(
        string='Datos EXIF',
        help='Metadatos EXIF extraídos de la imagen (JSON)'
    )
    exif_camera = fields.Char(
        string='Cámara',
        compute='_compute_exif_fields',
        store=True
    )
    exif_date = fields.Datetime(
        string='Fecha de Captura',
        compute='_compute_exif_fields',
        store=True
    )
    
    # Descripción y orden
    description = fields.Char(
        string='Descripción',
        help='Descripción de la imagen (ej: Vista del haz, Detalle de flores)'
    )
    is_primary = fields.Boolean(
        string='Imagen Principal',
        default=False,
        help='Indica si es la imagen principal del espécimen'
    )
    display_order = fields.Integer(
        string='Orden de Visualización',
        default=1,
        help='Orden en que se muestra en la galería'
    )
    
    # Auditoría
    uploaded_by = fields.Many2one(
        'res.users',
        string='Subido Por',
        default=lambda self: self.env.user,
        readonly=True
    )
    uploaded_at = fields.Datetime(
        string='Fecha de Subida',
        default=fields.Datetime.now,
        readonly=True
    )
    deleted_at = fields.Datetime(
        string='Fecha de Eliminación',
        help='Borrado lógico'
    )

    # Campos adicionales
    photographer = fields.Many2one('res.partner', string="Fotógrafo", help="El fotógrafo que tomó la imagen", tracking=True)
    created_at = fields.Datetime(string="Fecha de Creación", default=fields.Datetime.now, readonly=True, help="Fecha y hora en que se creó el registro")
    image_type = fields.Selection([
        ('general', 'General'),
        ('flower', 'Flor'),
        ('fruit', 'Fruto'),
        ('leaf', 'Hoja'),
    ], string="Tipo de Imagen", required=True, default='general', help="Categoría de la imagen")

    # Campos computados
    file_size_human = fields.Char(
        string='Tamaño',
        compute='_compute_file_size_human'
    )
    resolution = fields.Char(
        string='Resolución',
        compute='_compute_resolution'
    )

    @api.depends('image_data')
    def _compute_thumbnails(self):
        for record in self:
            if record.image_data:
                try:
                    image = Image.open(BytesIO(base64.b64decode(record.image_data)))
                    # Generar miniatura pequeña (80x80)
                    image_small = image.copy()
                    image_small.thumbnail((80, 80), Image.Resampling.LANCZOS if hasattr(Image, 'Resampling') else Image.ANTIALIAS)
                    output_small = BytesIO()
                    image_small.save(output_small, format='PNG')
                    record.thumbnail = base64.b64encode(output_small.getvalue())
                    
                    # Generar miniatura mediana (200x200)
                    image_medium = image.copy()
                    image_medium.thumbnail((200, 200), Image.Resampling.LANCZOS if hasattr(Image, 'Resampling') else Image.ANTIALIAS)
                    output_medium = BytesIO()
                    image_medium.save(output_medium, format='PNG')
                    record.thumbnail_medium = base64.b64encode(output_medium.getvalue())
                except Exception as e:
                    record.thumbnail = False
                    record.thumbnail_medium = False
            else:
                record.thumbnail = False
                record.thumbnail_medium = False

    @api.depends('image_data')
    def _compute_file_metadata(self):
        for record in self:
            if record.image_data:
                try:
                    image_bytes = base64.b64decode(record.image_data)
                    record.file_size = len(image_bytes)
                    image_stream = BytesIO(image_bytes)
                    image = Image.open(image_stream)
                    record.image_width = image.width
                    record.image_height = image.height
                except Exception:
                    record.file_size = 0
                    record.image_width = 0
                    record.image_height = 0
            else:
                record.file_size = 0
                record.image_width = 0
                record.image_height = 0

    @api.depends('image_data')
    def _compute_file_hash(self):
        for record in self:
            if record.image_data:
                try:
                    image_bytes = base64.b64decode(record.image_data)
                    record.file_hash = hashlib.sha256(image_bytes).hexdigest()
                except Exception:
                    record.file_hash = False
            else:
                record.file_hash = False

    @api.depends('exif_data')
    def _compute_exif_fields(self):
        for record in self:
            if record.exif_data:
                try:
                    exif = json.loads(record.exif_data)
                    record.exif_camera = exif.get('camera', '')
                    record.exif_date = exif.get('date_taken', False)
                except Exception:
                    record.exif_camera = ''
                    record.exif_date = False
            else:
                record.exif_camera = ''
                record.exif_date = False

    @api.depends('file_size')
    def _compute_file_size_human(self):
        for record in self:
            if record.file_size:
                size = record.file_size
                for unit in ['B', 'KB', 'MB', 'GB']:
                    if size < 1024.0:
                        record.file_size_human = f"{size:.2f} {unit}"
                        break
                    size /= 1024.0
            else:
                record.file_size_human = '0 B'

    @api.depends('image_width', 'image_height')
    def _compute_resolution(self):
        for record in self:
            if record.image_width and record.image_height:
                record.resolution = f"{record.image_width}x{record.image_height}"
            else:
                record.resolution = 'Desconocida'

    @api.constrains('file_hash')
    def _check_duplicate_image(self):
        for record in self:
            if record.file_hash:
                duplicate = self.search([
                    ('id', '!=', record.id),
                    ('specimen_id', '=', record.specimen_id.id),
                    ('file_hash', '=', record.file_hash),
                    ('deleted_at', '=', False)
                ], limit=1)
                if duplicate:
                    raise ValidationError(
                        f'Esta imagen ya existe para este espécimen (subida el {duplicate.uploaded_at}).'
                    )

    @api.model
    def create(self, vals):
        if vals.get('image_data'):
            vals['exif_data'] = self._extract_exif(vals['image_data'])
        if vals.get('specimen_id'):
            existing_images = self.search([('specimen_id', '=', vals['specimen_id']), ('deleted_at', '=', False)])
            if not existing_images:
                vals['is_primary'] = True
        if vals.get('is_primary') and vals.get('specimen_id'):
            self.search([('specimen_id', '=', vals['specimen_id']), ('is_primary', '=', True), ('deleted_at', '=', False)]).write({'is_primary': False})
        record = super(HerbarioImage, self).create(vals)
        self.env['herbario.history.log'].create({
            'specimen_id': record.specimen_id.id,
            'entity_type': 'image',
            'entity_id': record.id,
            'action_type': 'image_added',
            'field_modified': None,
            'old_value': None,
            'new_value': f'Nueva imagen: {record.filename_original}',
            'user_id': self.env.user.id,
            'user_name': self.env.user.name,
        })
        return record

    def write(self, vals):
        if vals.get('is_primary'):
            for record in self:
                self.search([('specimen_id', '=', record.specimen_id.id), ('id', '!=', record.id), ('is_primary', '=', True), ('deleted_at', '=', False)]).write({'is_primary': False})
        return super(HerbarioImage, self).write(vals)

    def unlink(self):
        for record in self:
            record.write({'deleted_at': fields.Datetime.now()})
        return True

    def action_set_as_primary(self):
        self.ensure_one()
        self.search([('specimen_id', '=', self.specimen_id.id), ('id', '!=', self.id), ('is_primary', '=', True), ('deleted_at', '=', False)]).write({'is_primary': False})
        self.write({'is_primary': True})

    def _extract_exif(self, image_data_base64):
        try:
            image_bytes = base64.b64decode(image_data_base64)
            image_stream = BytesIO(image_bytes)
            image = Image.open(image_stream)
            exif_dict = {}
            if hasattr(image, '_getexif') and image._getexif():
                exif = image._getexif()
                from PIL.ExifTags import TAGS
                for tag_id, value in exif.items():
                    tag = TAGS.get(tag_id, tag_id)
                    if tag in ['Make', 'Model', 'DateTime', 'DateTimeOriginal']:
                        exif_dict[tag.lower()] = str(value)
            return json.dumps(exif_dict) if exif_dict else None
        except Exception:
            return None

    def name_get(self):
        result = []
        for record in self:
            name = record.description or record.filename_original
            if record.is_primary:
                name = f"⭐ {name}"
            result.append((record.id, name))
        return result