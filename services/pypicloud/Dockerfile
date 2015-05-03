FROM debian:latest
MAINTAINER "Martin C. Drohmann <mdrohmann@gmail.com>"

# Install packages required
ENV DEBIAN_FRONTEND noninteractive
RUN echo 'Acquire::http { Proxy "http://192.168.1.137:3142"; };' > /etc/apt/apt.conf.d/02proxy && \
    apt-get update -qq && \
    apt-get install -y python-pip python2.7-dev libpq-dev && \
    pip install virtualenv && \
    virtualenv /env && \
    /env/bin/pip install pypicloud uwsgi pastescript flywheel psycopg2 && \
    mkdir -p /var/lib/pypicloud && \
    apt-get clean && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

VOLUME ["/etc"]
COPY my_init.sh /sbin/my_init

# Use baseimage-docker's init system.
CMD ["/sbin/my_init"]
