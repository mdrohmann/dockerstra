CGIT server
===========

This docker container starts a cgit_ server.

Configuration
-------------

The service is configured with the ``etc/cgitrc``.  Either leave it as-is, in
which case a homepage for every repository is generated, or configure it
according to the `manual page <http://linux.die.net/man/5/cgitrc>`_.

Dependent images
----------------

The server depends on the following images:

   - data/repositories
   - mdrohmann/cgit

They are built as follows:

::

   cd data/repositories
   sudo docker build --tag=data/repositories .

and

::

   cd services/cgit
   sudo docker build --tag mdrohmann/cgit .

Furthermore, it is recommended to configure the cgitrc
file in a host directory, that we want to call.  The default on my computer
`JUERGEN` is

::

   export CGIT_DATA_DIR=/home/martin/gistin/docker/services/cgit/etc

Usage
-----

1. Create a storage container

   ::

      sudo docker create --name=git_repos data/repositories

2. Create cgitrc file in ``$CGIT_DATA_DIR``.

3. Run the cgit container:

   ::

      sudo docker run -d -P --volumes-from=git_repos \
          -v=${CGIT_DATA_DIR}:/data --name=cgit mdrohmann/cgit

4. Get the port at which the cgit container started with

   ::

      sd inspect --format='{{range $port, $conf := .NetworkSettings.Ports}}'\
      '{{ (index $conf 0).HostPort }}'\
      '{{ end }}' cgit

5. Update the nginx configuration...

.. _cgit: http://git.zx2c4.com/cgit/



