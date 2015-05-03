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
