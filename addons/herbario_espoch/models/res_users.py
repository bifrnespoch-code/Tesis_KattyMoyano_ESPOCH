from odoo import models, fields, api


class ResUsers(models.Model):
    _inherit = 'res.users'

    # Rol específico del herbario
    herbario_role = fields.Selection([
        ('encargado', 'Encargado del Herbario'),
        ('investigador', 'Investigador'),
        ('estudiante', 'Estudiante'),
        ('admin_ti', 'Administrador TI'),
        ('visitante', 'Visitante')
    ], string='Rol en Herbario', default='visitante')

    # Estadísticas de usuario
    specimens_created_count = fields.Integer(
        string='Especímenes Creados',
        compute='_compute_herbario_stats'
    )
    locations_added_count = fields.Integer(
        string='Ubicaciones Agregadas',
        compute='_compute_herbario_stats'
    )
    images_uploaded_count = fields.Integer(
        string='Imágenes Subidas',
        compute='_compute_herbario_stats'
    )
    last_herbario_activity = fields.Datetime(
        string='Última Actividad en Herbario',
        compute='_compute_last_activity'
    )

    # Información adicional
    institution = fields.Char(
        string='Institución',
        help='Institución académica o de investigación'
    )
    research_area = fields.Char(
        string='Área de Investigación',
        help='Área específica de investigación botánica'
    )
    orcid_id = fields.Char(
        string='ORCID ID',
        help='Identificador ORCID del investigador'
    )

    @api.depends('specimens_created_count', 'locations_added_count', 'images_uploaded_count')
    def _compute_herbario_stats(self):
        """Calcula estadísticas de contribuciones al herbario"""
        for user in self:
            # Especímenes creados
            user.specimens_created_count = self.env['herbario.specimen'].search_count([
                ('created_by', '=', user.id)
            ])
            
            # Ubicaciones agregadas
            user.locations_added_count = self.env['herbario.collection.site'].search_count([
                ('created_by', '=', user.id)
            ])
            
            # Imágenes subidas
            user.images_uploaded_count = self.env['herbario.image'].search_count([
                ('uploaded_by', '=', user.id),
                ('deleted_at', '=', False)
            ])

    @api.depends()
    def _compute_last_activity(self):
        """Obtiene la última actividad en el herbario"""
        for user in self:
            last_log = self.env['herbario.history.log'].search([
                ('user_id', '=', user.id)
            ], limit=1, order='timestamp desc')
            
            user.last_herbario_activity = last_log.timestamp if last_log else False

    def action_view_my_specimens(self):
        """Acción para ver mis especímenes"""
        self.ensure_one()
        return {
            'name': 'Mis Especímenes',
            'type': 'ir.actions.act_window',
            'res_model': 'herbario.specimen',
            'view_mode': 'tree,form',
            'domain': [('created_by', '=', self.id)],
            'context': {'default_created_by': self.id}
        }

    def action_view_my_activity(self):
        """Acción para ver mi actividad"""
        self.ensure_one()
        return {
            'name': 'Mi Actividad',
            'type': 'ir.actions.act_window',
            'res_model': 'herbario.history.log',
            'view_mode': 'tree',
            'domain': [('user_id', '=', self.id)],
            'context': {'search_default_group_by_action': 1}
        }