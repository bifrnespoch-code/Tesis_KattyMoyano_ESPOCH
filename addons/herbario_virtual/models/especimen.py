from odoo import models, fields, api
class Especimen(models.Model):
    _name = 'herbario.especimen'
    _description = 'Especímen Botánico'
    _order = 'nombre_cientifico'
    nombre_comun = fields.Char(string='Nombre Común', required=True)
    nombre_cientifico = fields.Char(string='Nombre Científico', required=True)
    familia = fields.Char(string='Familia Botánica')
    descripcion = fields.Text(string='Descripción')
    imagen = fields.Binary(string='Imagen del Especímen')
    fecha_coleccion = fields.Date(string='Fecha de Recolección', default=fields.Date.today)
    ubicacion = fields.Char(string='Ubicación de Recolección')
    estado = fields.Selection([
        ('activo', 'Activo'),
        ('archivado', 'Archivado'),
    ], string='Estado', default='activo')
    # Método para mostrar el nombre en la vista de lista
    def name_get(self):
        result = []
        for record in self:
            name = f"{record.nombre_comun} ({record.nombre_cientifico})"
            result.append((record.id, name))
        return result