Apt-cacher-NG
=============

Runs an apt-cacher-ng service.

Depedent images
---------------

The server depends on the following image:

   - mdrohmann/apt-cacher-ng

It is built as follows:

::

   cd services/apt-cacher-ng
   sudo docker build --tag=mdrohmann/apt-cacher-ng .

Usage
-----

1. Run the server like this

   ::

      sudo docker run --name=apt-cacher-ng -d -p 3142:3142 -v /tmp/cache/apt-cacher-ng:/var/cache/apt-cacher-ng mdrohmann/apt-cacher-ng

2. Add the proxy to the apt-get configuration

   ::

      echo 'Acquire::http::Proxy "http://192.168.1.137:3142";' > /etc/apt/apt.conf.d/02proxy
      echo 'Acquire::https::Proxy "false" >> /etc/apt/apt.conf.d/02proxy

   The second line disables the cacher for SSL connections.  As it would not
   really make sense here. :(
