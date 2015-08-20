FROM mdrohmann/python_host_minimal

MAINTAINER "Martin C. Drohmann <mdrohmann@gmail.com>"

USER root

RUN apt-get update -qqy \
 && apt-get -qqy --no-install-recommends install \
     openjdk-7-jre-headless \
     unzip \
     wget \
 && rm -rf /var/lib/apt/lists/* \
 && apt-get clean
 && sed -i 's/\/dev\/urandom/\/dev\/.\/urandom/' ./usr/lib/jvm/java-7-openjdk-amd64/jre/lib/security/java.security

RUN mkdir -p /opt/selenium \
 && wget --no-verbose http://selenium-release.storage.googleapis.com/2.45/selenium-server-standalone-2.45.0.jar -O /opt/selenium/selenium-server-standalone.jar

ENV TZ "US/Pacific"
RUN echo "US/Pacific" | sudo tee /etc/timezone \
  && dpkg-reconfigure --frontend noninteractive tzdata

RUN apt-get update -qqy \
 && apt-get -qqy --no-install-recommends install \
      firefox \
 && rm -rf /var/lib/apt/lists/* \
 && apt-get clean

RUN apt-get update -qq \
 && apt-get install --no-install-recommends -qy \
      fluxbox \
      fonts-ipafont-gothic \
      language-pack-en \
      x11vnc \
      xfonts-100dpi \
      xfonts-75dpi \
      xfonts-cyrillic \
      xfonts-scalable \
      xvfb \
 && rm -rf /var/lib/apt/lists/* \
 && apt-get clean \
 && mkdir -p ~/.vnc
 && x11vnc -storepasswd secret ~/.vnc/passwd

#============================
# Some configuration options
#============================
ENV SCREEN_WIDTH 1360
ENV SCREEN_HEIGHT 1020
ENV SCREEN_DEPTH 24
ENV DISPLAY :99.0

USER python
WORKDIR /home/python

RUN mkdir /home/python/init.d
COPY "numpy.sh" "/home/python/init.d/"

CMD ["/home/python/init.sh"]

# vim: set sw=2 et:
