from odoo import models, fields, api


class HistoryLog(models.Model):
    _name = 'herbario.history.log'
    _description = 'Historial de Cambios del Herbario'
    _order = 'timestamp desc'
    _rec_name = 'action_type'

    # Entidad modificada
    entity_type = fields.Selection([
        ('specimen', 'Espécimen'),
        ('collection_site', 'Ubicación de Recolección'),
        ('image', 'Imagen'),
        ('qr_code', 'Código QR')
    ], string='Tipo de Entidad', required=True, index=True)
    
    entity_id = fields.Integer(
        string='ID de Entidad',
        required=True,
        index=True
    )
    
    specimen_id = fields.Many2one(
        'herbario.specimen',
        string='Espécimen Relacionado',
        required=True,
        ondelete='cascade',
        index=True,
        help='Espécimen al que pertenece este cambio'
    )

    # Tipo de acción
    action_type = fields.Selection([
        ('created', 'Creado'),
        ('updated', 'Actualizado'),
        ('deleted', 'Eliminado'),
        ('location_added', 'Ubicación Agregada'),
        ('location_updated', 'Ubicación Actualizada'),
        ('location_deleted', 'Ubicación Eliminada'),
        ('image_added', 'Imagen Agregada'),
        ('image_deleted', 'Imagen Eliminada'),
        ('qr_generated', 'QR Generado'),
        ('qr_regenerated', 'QR Regenerado'),
        ('status_changed', 'Estado Cambiado'),
        ('exported', 'Exportado'),
        ('imported', 'Importado')
    ], string='Acción', required=True, index=True)

    # Detalles del cambio
    field_modified = fields.Char(
        string='Campo Modificado',
        help='Nombre del campo que fue modificado'
    )
    old_value = fields.Text(
        string='Valor Anterior'
    )
    new_value = fields.Text(
        string='Valor Nuevo'
    )
    
    # Descripción del cambio
    description = fields.Text(
        string='Descripción',
        compute='_compute_description',
        store=True
    )

    # Información del usuario
    user_id = fields.Many2one(
        'res.users',
        string='Usuario',
        required=True,
        index=True,
        default=lambda self: self.env.user
    )
    user_name = fields.Char(
        string='Nombre del Usuario',
        required=True,
        default=lambda self: self.env.user.name
    )
    
    # Timestamp
    timestamp = fields.Datetime(
        string='Fecha y Hora',
        required=True,
        index=True,
        default=fields.Datetime.now
    )

    # Metadata adicional
    ip_address = fields.Char(
        string='Dirección IP',
        help='IP desde donde se realizó el cambio'
    )
    user_agent = fields.Char(
        string='User Agent',
        help='Navegador/cliente utilizado'
    )

    # Campos computados
    time_ago = fields.Char(
        string='Hace',
        compute='_compute_time_ago'
    )
    change_summary = fields.Char(
        string='Resumen',
        compute='_compute_change_summary'
    )

    @api.depends('action_type', 'field_modified', 'old_value', 'new_value')
    def _compute_description(self):
        """Genera descripción legible del cambio"""
        for record in self:
            if record.action_type == 'created':
                record.description = f"Se creó el registro"
            elif record.action_type == 'updated' and record.field_modified:
                field_label = record._get_field_label(record.field_modified)
                record.description = f"Se modificó {field_label}: '{record.old_value}' → '{record.new_value}'"
            elif record.action_type == 'deleted':
                record.description = f"Se eliminó el registro"
            elif record.action_type in ['location_added', 'image_added']:
                record.description = record.new_value or f"Se agregó {record.entity_type}"
            elif record.action_type == 'qr_generated':
                record.description = "Se generó el código QR"
            else:
                record.description = f"Acción: {dict(self._fields['action_type'].selection).get(record.action_type)}"

    @api.depends('timestamp')
    def _compute_time_ago(self):
        """Calcula tiempo transcurrido desde el cambio"""
        for record in self:
            if record.timestamp:
                now = fields.Datetime.now()
                diff = now - record.timestamp
                
                if diff.days > 365:
                    years = diff.days // 365
                    record.time_ago = f"Hace {years} año{'s' if years > 1 else ''}"
                elif diff.days > 30:
                    months = diff.days // 30
                    record.time_ago = f"Hace {months} mes{'es' if months > 1 else ''}"
                elif diff.days > 0:
                    record.time_ago = f"Hace {diff.days} día{'s' if diff.days > 1 else ''}"
                elif diff.seconds > 3600:
                    hours = diff.seconds // 3600
                    record.time_ago = f"Hace {hours} hora{'s' if hours > 1 else ''}"
                elif diff.seconds > 60:
                    minutes = diff.seconds // 60
                    record.time_ago = f"Hace {minutes} minuto{'s' if minutes > 1 else ''}"
                else:
                    record.time_ago = "Hace unos segundos"
            else:
                record.time_ago = ""

    @api.depends('action_type', 'entity_type', 'user_name')
    def _compute_change_summary(self):
        """Resumen corto del cambio"""
        for record in self:
            action = dict(self._fields['action_type'].selection).get(record.action_type, '')
            entity = dict(self._fields['entity_type'].selection).get(record.entity_type, '')
            record.change_summary = f"{record.user_name}: {action} {entity}"

    def _get_field_label(self, field_name):
        """Obtiene la etiqueta legible del campo"""
        try:
            specimen_model = self.env['herbario.specimen']
            if field_name in specimen_model._fields:
                return specimen_model._fields[field_name].string
        except Exception:
            pass
        return field_name

    @api.model
    def log_action(self, specimen_id, entity_type, entity_id, action_type, 
                   field_modified=None, old_value=None, new_value=None, description=None):
        """
        Método helper para crear logs de manera sencilla
        
        Uso:
        self.env['herbario.history.log'].log_action(
            specimen_id=15,
            entity_type='specimen',
            entity_id=15,
            action_type='updated',
            field_modified='familia',
            old_value='Rosaceae',
            new_value='Asteraceae'
        )
        """
        # Obtener información de la petición si está disponible
        request = self.env.context.get('request')
        ip_address = None
        user_agent = None
        
        if request and hasattr(request, 'httprequest'):
            ip_address = request.httprequest.environ.get('REMOTE_ADDR')
            user_agent = request.httprequest.environ.get('HTTP_USER_AGENT')

        return self.create({
            'specimen_id': specimen_id,
            'entity_type': entity_type,
            'entity_id': entity_id,
            'action_type': action_type,
            'field_modified': field_modified,
            'old_value': str(old_value) if old_value else None,
            'new_value': str(new_value) if new_value else None,
            'user_id': self.env.user.id,
            'user_name': self.env.user.name,
            'ip_address': ip_address,
            'user_agent': user_agent,
        })

    @api.model
    def get_specimen_timeline(self, specimen_id, limit=None):
        """Obtiene línea de tiempo de un espécimen"""
        domain = [('specimen_id', '=', specimen_id)]
        return self.search(domain, limit=limit, order='timestamp desc')

    @api.model
    def get_user_activity(self, user_id, days=30):
        """Obtiene actividad reciente de un usuario"""
        from datetime import datetime, timedelta
        date_from = datetime.now() - timedelta(days=days)
        
        domain = [
            ('user_id', '=', user_id),
            ('timestamp', '>=', date_from)
        ]
        return self.search(domain, order='timestamp desc')

    @api.model
    def get_statistics(self, specimen_id=None):
        """Obtiene estadísticas de cambios"""
        domain = [('specimen_id', '=', specimen_id)] if specimen_id else []
        
        logs = self.search(domain)
        
        stats = {
            'total_changes': len(logs),
            'by_action': {},
            'by_user': {},
            'by_entity': {},
            'most_active_users': []
        }
        
        # Agrupar por acción
        for log in logs:
            action = log.action_type
            stats['by_action'][action] = stats['by_action'].get(action, 0) + 1
        
        # Agrupar por usuario
        for log in logs:
            user = log.user_name
            stats['by_user'][user] = stats['by_user'].get(user, 0) + 1
        
        # Agrupar por tipo de entidad
        for log in logs:
            entity = log.entity_type
            stats['by_entity'][entity] = stats['by_entity'].get(entity, 0) + 1
        
        # Usuarios más activos
        user_activity = sorted(stats['by_user'].items(), key=lambda x: x[1], reverse=True)
        stats['most_active_users'] = user_activity[:5]
        
        return stats

    def action_view_specimen(self):
        """Acción para ver el espécimen relacionado"""
        self.ensure_one()
        return {
            'name': 'Espécimen',
            'type': 'ir.actions.act_window',
            'res_model': 'herbario.specimen',
            'view_mode': 'form',
            'res_id': self.specimen_id.id,
            'target': 'current',
        }

    def name_get(self):
        """Personaliza el nombre mostrado"""
        result = []
        for record in self:
            action = dict(self._fields['action_type'].selection).get(record.action_type, '')
            name = f"{record.timestamp.strftime('%Y-%m-%d %H:%M')} - {action}"
            result.append((record.id, name))
        return result