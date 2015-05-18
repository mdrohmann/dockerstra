# TO_BUILD: docker build -rm -t apt-cacher-ng .
# TO_RUN: docker run -d -p 3142:3142 \
#           -v /tmp/apt-cacher-ng:/var/cache/apt-cacher-ng \
#           apt-cacher-ng

FROM ubuntu:latest
MAINTAINER "Martin C. Drohmann <mdrohmann@gmail.com>"

RUN apt-get update -qq && \
    apt-get install --no-install-recommends -qy apt-cacher-ng

EXPOSE 3142

VOLUME ["/var/cache/apt-cacher-ng"]
VOLUME ["/etc/apt-cacher-ng"]

COPY acng.conf /etc/apt-cacher-ng/acng.conf

CMD /usr/sbin/apt-cacher-ng ForeGround=1 CacheDir=/var/cache/apt-cacher-ng
