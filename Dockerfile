# Partimos de la imagen oficial de Odoo
FROM odoo:17

# Copiamos tus módulos personalizados al contenedor
COPY ./addons /mnt/extra-addons

# Ajustamos permisos
USER root
RUN chown -R odoo:odoo /mnt/extra-addons
USER odoo
