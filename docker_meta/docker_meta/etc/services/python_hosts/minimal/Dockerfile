FROM debian:latest

MAINTAINER "Martin C. Drohmann <mdrohmann@gmail.com>"

ENV LANG en_US.UTF-8
ENV LC_ALL en_US.UTF-8

ENV DEBIAN_FRONTEND noninteractive
RUN echo 'Acquire::http { Proxy "http://192.168.1.137:3142"; };' > /etc/apt/apt.conf.d/02proxy \
 && apt-get update -q \
 && apt-get install --no-install-recommends -qy \
        adduser \
        build-essential \
        ca-certificates \
        git-core \
        libffi-dev \
        locales \
        make \
        python-dev \
        python2.7-minimal \
        python-pip \
        python-virtualenv \
        sudo \
 && echo $LANG UTF-8 >> /etc/locale.gen \
 && locale-gen $LANG \
 && rm -rf /var/lib/apt/lists/* \
 && apt-get clean

RUN adduser --uid 1000 --group --system --shell /bin/bash python

#RUN echo 'python ALL=NOPASSWD: /bin/chown python\:python *, /bin/chown -R python\:python *' > /etc/sudoers.d/chown \
# && chmod 0440 /etc/sudoers.d/chown
RUN echo 'python ALL=NOPASSWD: ALL' > /etc/sudoers.d/python \
 && chmod 0440 /etc/sudoers.d/python

COPY pypi-internal.pem /etc/ssl/private/
RUN update-ca-certificates

USER python
WORKDIR /home/python

COPY bashrc /home/python/.bashrc
COPY init.sh /home/python/init.sh

CMD ["/home/python/init.sh"]
