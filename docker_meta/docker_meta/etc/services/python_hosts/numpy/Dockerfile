FROM mdrohmann/python_host_minimal

MAINTAINER "Martin C. Drohmann <mdrohmann@gmail.com>"

USER root

RUN apt-get update -qq \
 && apt-get install --no-install-recommends -qy \
      gfortran \
      libatlas-dev \
      liblapack-dev
 && rm -rf /var/lib/apt/lists/* \
 && apt-get clean

USER python
WORKDIR /home/python

RUN mkdir /home/python/init.d
COPY "numpy.sh" "/home/python/init.d/"

CMD ["/home/python/init.sh"]

# vim: set sw=2 et:
