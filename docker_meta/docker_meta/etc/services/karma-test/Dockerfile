FROM selenium/node-firefox-debug

MAINTAINER Martin Drohmann <mdrohmann@gmail.com>

USER root

RUN echo 'Acquire::http::Proxy "http://192.168.1.137:3142";' > /etc/apt/apt.conf.d/02proxy && \
    echo 'Acquire::https::Proxy "false";' >> /etc/apt/apt.conf.d/02proxy && \
    apt-get update -qq && \
    apt-get install --no-install-recommends -qy curl &&
    curl -sL https://deb.nodesource.com/setup | bash - &&
    apt-get install --no-install-recommends -qy nodejs &&
    apt-get remove --autoremove curl &&
    apt-get clean

RUN npm install -g karma

# Add volume to repositories directory
VOLUME /code

COPY entry_point.sh /karma.sh

ENTRYPOINT /karma.sh
