FROM fedora:36

MAINTAINER Kathryn Janzen <kathryn.janzen@lightsource.ca>

COPY requirements.txt /
COPY deploy/run-server.sh /run-server.sh
COPY deploy/wait-for-it.sh /wait-for-it.sh
ADD . /dataserver

RUN dnf clean all &&  \
    rm -r /var/cache/dnf  &&  \
    dnf -y update &&  \
    dnf -y install httpd python-pip mod_wsgi postgresql-libs python-psycopg2 mod_xsendfile  libglvnd-glx \
    python-crypto python-memcached mod_ssl python-docutils unzip tar libgfortran hdf5 libquadmath python3-lz4 &&  \
    dnf clean all &&  \
    rpm -ivh /dataserver/deploy/CBFlib-0.9.7-2.fc36.x86_64.rpm &&  \
    python3 -m venv /venv && source /venv/bin/activate && \
    /venv/bin/pip3 install --no-cache-dir --upgrade pip && \
    /venv/bin/pip3 install --no-cache-dir -r /requirements.txt  && \
    mkdir -p /dataserver/local && \
    chmod -v +x /run-server.sh /wait-for-it.sh && \
    /bin/rm -f /etc/httpd/conf.d/ssl.conf && \
    /bin/cp /dataserver/deploy/dataserver.conf /etc/httpd/conf.d/ && \
    sed -i -E 's@#!/usr/bin/env python.*@#!/venv/bin/python3@' /dataserver/manage.py && \
    pip install /dataserver/deploy/pycbf-0.9.6.5-cp310-cp310-linux_x86_64.whl && \
    /dataserver/manage.py collectstatic --noinput && \
    rm -rfv /dataserver/deploy

EXPOSE 80

VOLUME ["/users",  "/archive", "/cache"]
CMD ["/run-server.sh"]

