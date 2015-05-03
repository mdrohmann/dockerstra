FROM debian:latest

ENV LANG en_US.UTF-8

RUN apt-get update -q && \
    apt-get install -qy build-essential \
        git-core \
        libssl-dev \
        lighttpd \
        locales \
        python2.7-minimal \
        python-pygments \
        python-docutils \
    && \
    echo $LANG UTF-8 >> /etc/locale.gen && \
    locale-gen $LANG && \
    git clone https://github.com/zx2c4/cgit.git /tmp/cgit && \
    cd /tmp/cgit && \
    git submodule update --init && \
    make install && \
    cd / && \
    rm -rf /tmp/cgit && \
    ln -s /usr/bin/rst2html /usr/bin/rst2html.py && \
    ln -s /data/cgitrc /etc/cgitrc && \
    apt-get purge -qy --auto-remove build-essential libssl-dev

COPY lighttpd.conf /etc/lighttpd/lighttpd.conf.default
COPY cgitrc /etc/cgitrc.default

COPY start.sh /start.sh

VOLUME ["/data"]
VOLUME ["/repositories"]

EXPOSE 80

CMD ["/start.sh"]
