ARG ODOO_VERSION
# https://github.com/odoo/docker/blob/master/14.0/Dockerfile
FROM odoo:${ODOO_VERSION}
USER root
COPY ./ /mnt/addons
COPY ./odoo.conf /etc/odoo/odoo.conf
RUN mkdir /mnt/addons_ee /mnt/enterprise \
    && pip3 install -r /mnt/addons/requirements.txt
USER odoo
