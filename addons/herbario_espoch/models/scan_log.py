from odoo import models, fields, api

class HerbarioQRScanLog(models.Model):
    _name = 'herbario.qr.scan.log'
    _description = 'Historial de Escaneos de QR'
    _order = 'scanned_at desc'

    qr_code_id = fields.Many2one(
        'herbario.qr.code',
        string='Código QR',
        required=True,
        ondelete='cascade',
        index=True
    )
    scanned_at = fields.Datetime(
        string='Fecha de Escaneo',
        default=fields.Datetime.now,
        readonly=True
    )
    ip_address = fields.Char(
        string='IP Address',
        help='Dirección IP del escaneo'
    )
    user_agent = fields.Char(
        string='User Agent',
        help='Información del navegador o dispositivo'
    )
    location = fields.Char(
        string='Ubicación',
        help='Ubicación aproximada del escaneo'
    )
    # Agrega más campos si necesitas, como user_id o notes