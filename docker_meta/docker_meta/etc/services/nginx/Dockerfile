FROM debian:latest

MAINTAINER "Martin C. Drohmann <mdrohmann@gmail.com>"

RUN apt-key adv --keyserver hkp://pgp.mit.edu:80 --recv-keys 573BFD6B3D8FBC641079A6ABABF5BD827BD9BF62
RUN echo "deb http://nginx.org/packages/mainline/debian/ wheezy nginx" >> /etc/apt/sources.list

ENV NGINX_VERSION 1.9.0-1~wheezy

ENV DEBIAN_FRONTEND noninteractive
RUN echo 'Acquire::http { Proxy "http://192.168.1.137:3142"; };' > /etc/apt/apt.conf.d/02proxy && \
    apt-get update -qq && \
    apt-get install -y ca-certificates nginx=${NGINX_VERSION} && \
    rm -rf /var/lib/apt/lists/*

# forward request and error logs to docker log collector
RUN ln -sf /dev/stdout /var/log/nginx/access.log
RUN ln -sf /dev/stderr /var/log/nginx/error.log

VOLUME ["/var/cache/nginx"]

EXPOSE 80 443

CMD ["nginx", "-g", "daemon off;"]
