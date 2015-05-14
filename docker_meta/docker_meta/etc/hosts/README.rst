Host containers
===============

Host containers are containers that are pre-configured to run programs in a
certain programming language.  At the moment, the following programming
languages are supported:

+ python

Modes
-----

There are different modes in which the containers can be started:

1. initialization / upgrade
2. daemon / single
3. test
4. bash
5. exec
6. backup / restore

The `initialization` mode creates dependent data containers and fills them
eg., with a virtual development environment.  The user can request execution in
this mode explicitly, but it is also enforced for all other modes, if it has
not been done before.  Similarly, the `upgrade` upgrades this data container,
but in contrast to the `initialization`, its execution is only enforced if the
``UPGRADE`` environment variable is set.

The `daemon` / `single` modes are basically identical.  They execute a script
starting a daemon in the required language or a *single job*-script that is
supposed to return with an exit code after a short amount of time.

The `test` mode runs meaningful tests, that check if the initialization was
successful, and if the `daemon` or `single job`-scripts are expected to
work correctly.

The `bash` mode is mainly for debugging and starts a bash session, that the
user can log in to explore the container.

The `exec` mode is a special mode (TODO: not implemented yet), where an
arbitrary command in the host file system is executed inside the container by a
user with UID and GID compatible to the host user configuration.

.. _usage:

Installation
------------

Install docker_meta with pip:

::

  pip install docker_meta


Usage
-----

The script `host_container` is the entry point to create, initialize and
start the container in any of the above modes.  It has the following synopsis:

.. code:: bash

  host_container [options] language variant mode [command [args ...]]

The command relies on configuration files, that in its most basic version are
found in ``<installdir>/etc/docker_meta/host_container/``.  This directory
should have the following sub-directories:

1. ``language/services/variant``
2. ``language/hosts/variant``
3. ``config`` and optionally ``language/config/variant/``

The script also looks for the same configuration file structure in
``$HOME/.docker_meta/host_container``.

1. The `services` directory includes a Dockerfile for each variant of the
   docker host.
2. The ``hosts`` directory is mounted inside the docker container's ``/data/``
   directory and should include all the necessary scripts, that initialize the
   environment, test and execute daemon or single job scripts.
3. The ``config`` directories include `docker_meta` configuration files,
   describing how the modes are executed.  Probably, you do not have to do
   anything here, and the installed ``host_base_*.yaml`` files are sufficient.


.. vim:set et sw=2 ts=8 spell spelllang=en:
