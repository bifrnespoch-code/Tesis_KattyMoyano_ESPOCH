from odoo import models, fields, api
from odoo.exceptions import ValidationError
import qrcode
from io import BytesIO
import base64
import hashlib

ERROR_CORRECTION_MAP = {
    'L': qrcode.constants.ERROR_CORRECT_L,  # 7%
    'M': qrcode.constants.ERROR_CORRECT_M,  # 15%
    'Q': qrcode.constants.ERROR_CORRECT_Q,  # 25%
    'H': qrcode.constants.ERROR_CORRECT_H,  # 30%
}

class HerbarioQRCode(models.Model):
    _name = 'herbario.qr.code'
    _description = 'Códigos QR de Especímenes'
    _order = 'generated_at desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    
    # Relación con espécimen (uno a uno)
    specimen_id = fields.Many2one(
        'herbario.specimen',
        string='Espécimen',
        required=True,
        ondelete='cascade',
        index=True
    )

    # Datos del QR
    qr_image = fields.Binary(
        string='Imagen QR',
        attachment=True,
        help='Imagen del código QR generada'
    )
    qr_url = fields.Char(
        string='URL del QR',
        required=True,
        help='URL que el QR codifica'
    )
    qr_data = fields.Char(  # Campo agregado para coincidir con la vista
        string='Datos del QR',
        help='Datos adicionales del código QR'
    )
    resolution = fields.Selection([
        ('300', '300x300 px (Pequeño)'),
        ('600', '600x600 px (Mediano)'),
        ('1200', '1200x1200 px (Grande)'),
        ('2400', '2400x2400 px (Muy Grande)')
    ], string='Resolución', default='600', required=True)

    error_correction = fields.Selection([  # Campo agregado para coincidir con la vista
        ('L', 'Bajo'),
        ('M', 'Medio'),
        ('Q', 'Alto'),
        ('H', 'Máximo')
    ], string='Corrección de Errores', default='H')
    box_size = fields.Integer(string='Tamaño de Caja', default=10)  # Campo agregado
    border = fields.Integer(string='Borde', default=4)  # Campo agregado

    # Estadísticas de uso
    download_count = fields.Integer(
        string='Número de Descargas',
        default=0,
        readonly=True
    )
    last_downloaded_at = fields.Datetime(
        string='Última Descarga',
        readonly=True
    )
    scan_count = fields.Integer(
        string='Número de Escaneos',
        default=0,
        readonly=True,
        help='Contador de veces que se escaneó el QR'
    )
    last_scanned_at = fields.Datetime(
        string='Último Escaneo',
        readonly=True
    )

    # Control de versiones
    obsolete = fields.Boolean(
        string='Obsoleto',
        default=False,
        help='Indica si el QR fue regenerado y este quedó obsoleto'
    )
    version = fields.Integer(
        string='Versión',
        default=1,
        readonly=True,
        help='Versión del QR (se incrementa al regenerar)'
    )

    # Auditoría
    generated_by = fields.Many2one(
        'res.users',
        string='Generado Por',
        default=lambda self: self.env.user,
        readonly=True
    )
    generated_at = fields.Datetime(
        string='Fecha de Generación',
        default=fields.Datetime.now,
        readonly=True
    )

    # Campos adicionales para coincidir con la vista
    image_format = fields.Char(string='Formato de Imagen', default='PNG')  # Campo agregado
    file_size_bytes = fields.Integer(string='Tamaño en Bytes', compute='_compute_file_size')  # Campo agregado
    checksum = fields.Char(string='Checksum', compute='_compute_checksum')  # Campo agregado
    scan_log_ids = fields.One2many('herbario.qr.scan.log', 'qr_code_id', string='Historial de Escaneos')

    # Campos computados
    qr_filename = fields.Char(
        string='Nombre de Archivo',
        compute='_compute_qr_filename'
    )

    _sql_constraints = [
        ('specimen_unique', 'UNIQUE(specimen_id, obsolete)', 
         'Solo puede existir un código QR activo por espécimen.')
    ]

    @api.depends('specimen_id.codigo_herbario')
    def _compute_qr_filename(self):
        for record in self:
            if record.specimen_id:
                record.qr_filename = f"QR_{record.specimen_id.codigo_herbario}.png"
            else:
                record.qr_filename = "QR_code.png"

    @api.depends('qr_image')
    def _compute_file_size(self):
        for record in self:
            if record.qr_image:
                record.file_size_bytes = len(base64.b64decode(record.qr_image))
            else:
                record.file_size_bytes = 0

    @api.depends('qr_image')
    def _compute_checksum(self):
        for record in self:
            if record.qr_image:
                image_bytes = base64.b64decode(record.qr_image)
                record.checksum = hashlib.sha256(image_bytes).hexdigest()
            else:
                record.checksum = False

    @api.model
    def generate_qr_for_specimen(self, specimen):
        existing_qr = self.search([('specimen_id', '=', specimen.id), ('obsolete', '=', False)])
        if existing_qr:
            existing_qr.write({'obsolete': True})
            new_version = existing_qr.version + 1
        else:
            new_version = 1
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        qr_url = f"{base_url}/herbario/specimen/{specimen.id}"
        qr_record = self.create({
            'specimen_id': specimen.id,
            'qr_url': qr_url,
            'version': new_version,
            'qr_data': qr_url  # Asumiendo que qr_data es la URL o datos similares
        })
        qr_record._generate_qr_image()
        return qr_record

    def _generate_qr_image(self):
        """Genera la imagen QR"""
        self.ensure_one()
        
        # Convertir el string 'H' al valor correcto
        error_correction_value = ERROR_CORRECTION_MAP.get(
            self.error_correction, 
            qrcode.constants.ERROR_CORRECT_H
        ) if isinstance(self.error_correction, str) else (
            self.error_correction or qrcode.constants.ERROR_CORRECT_H
        )
        
        qr = qrcode.QRCode(
            version=None,
            error_correction=error_correction_value,  # ← Usar el valor convertido
            box_size=self.box_size or 10,
            border=self.border or 4
        )

    def action_regenerate(self):
        self.ensure_one()
        return self.generate_qr_for_specimen(self.specimen_id)

    def action_download(self):
        self.ensure_one()
        self.write({
            'download_count': self.download_count + 1,
            'last_downloaded_at': fields.Datetime.now()
        })
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/herbario.qr.code/{self.id}/qr_image/{self.qr_filename}?download=true',
            'target': 'self',
        }

    def register_scan(self):
        self.ensure_one()
        self.write({
            'scan_count': self.scan_count + 1,
            'last_scanned_at': fields.Datetime.now()
        })

    def action_change_resolution(self):
        self.ensure_one()
        return {
            'name': 'Cambiar Resolución',
            'type': 'ir.actions.act_window',
            'res_model': 'herbario.qr.code',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'new',
            'context': {'form_view_initial_mode': 'edit'}
        }

    def action_print_label(self):  # Método agregado para corregir el error
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': '/report/pdf/herbario.qr.code/%s' % self.id,  # Ajusta al reporte real si existe
            'target': 'new',
        }

    def toggle_obsolete(self):  # Método agregado para corregir el error
        self.ensure_one()
        self.write({'obsolete': not self.obsolete})
    
    def write(self, vals):
        res = super(HerbarioQRCode, self).write(vals)
        if 'resolution' in vals or 'error_correction' in vals or 'box_size' in vals or 'border' in vals:
            for record in self:
                record._generate_qr_image()
        return res

    def name_get(self):
        result = []
        for record in self:
            status = " [OBSOLETO]" if record.obsolete else ""
            name = f"QR v{record.version} - {record.specimen_id.codigo_herbario}{status}"
            result.append((record.id, name))
        return result