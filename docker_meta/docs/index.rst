Docker Meta
===========

An automation utility to start several docker containers from YAML_ files.  It
is similar to docker compose.  On top of composing container configuration, it
orchestrates backups and restores of data containers and the execution of
arbitrary commands on those data containers.  New commands can be added easily.


Installation
------------

Install the tool with pip

::

   pip install docker_meta

Usage
-----

The main script is called ``docker_start`` and takes one configuration file
as an argument.  It is based on the docker-py_ package to communicate with
the docker daemon.

The verbosity of the output can be controlled with the flags ``verbose`` and
``debug``.  Set ``debug=True`` in order to get notified about skipped steps and
automatic changes of the configuration.  Increasing the verbosity, creates more
information about the output of the docker-py_ commands.

By default, the configuration files for ``docker_start`` situate in one of
these places referred to as ``$DOCKERSTRA_CONF``:

- ``$HOME/.dockerstra``
- ``PYTHON_INSTALL_DIR/etc/dockerstra``
- ``/etc/dockerstra``

Select a configuration directory explicitly with the option ``-c``.

The directory ``$DOCKERSTRA_CONF`` has the following subdirectories that will
be described in detail:

- :ref:`environments<environments>`
- :ref:`services<services>`
- :ref:`data<services>`
- :ref:`units<units>`

.. _units:

Unit files
``````````

Units are the most important entity in the |project| world.  They define, how
collection of docker containers are created, started, stopped and interact with
each other.  A unit is denoted by the tuple ``UNITNAME/COMMAND`` referring to
its unique *unit name* and a *command*.  Each *command* is either defined by a
configuration file, or exist magically:
If the *command* ``start`` exists, that should describe how to start up the
unit, the commands

- ``stop`` (stops all the containers in the unit)
- ``cleanup`` (removes all containers, that do not have a volume attached) and
- ``purge`` (removes all containers, deletes volumes and removes base images).

are generated automatically, but can be overwritten with explicit command files.

To list all available units, the command

.. code:: bash

   docker_start --list-units

returns a list of all available ``UNITNAME/COMMAND`` tuples.

In order to print out the (potentially automatically created) configuration
file for a unit command, type

.. code:: bash

   docker_start --print-unit UNITNAME/COMMAND

Like all configuration files in |project|, the unit command files written in
the YAML_ format, and consists of two documents (separated with a line
containing the separation marker (``---``).

.. _composition:

Composition document
********************

The first document describes docker containers and their composition, including
the three steps

  1. ``build``,
  2. ``creation``
  3. and ``startup``.


These commands are refer to the docker-py_ commands ``build``,
``create_container`` and ``start``.  So, the YAML_ document is a dictionary,
whose keys are the container names to compose, and the values are another
dictionary specifying the three composition steps.

The values for these composition steps are passed to the corresponding
docker-py_ commands.  If you know this python package, there is no need to
learn a new syntax or commands.

Alternatively, the first document can simply be of the form:

.. code-block:: yaml

   import: other_file.yaml

in which case the container descriptions are read from the file
``other_file.yaml``.

List of commands
****************

The second document describes a list of commands to execute on the previously
defined containers.  The document is a list of dictionaries with only one key
(the container name to execute a command on).  The value of this dictionary is
another dictionary specifying a :ref:`command <commands>` and its arguments.

Example
```````

An example configuration file looks like this:

.. code-block:: yaml

   git_repos:
     build:
       path: data/repositories
       tag: data/repositories
    creation:
       name: git_repos   # this is redundant and could be left out

   gitolite:
     build:
       path: services/gitolite
       tag: mdrohmann/gitolite
     creation:
       volumes_from: git_repos
       volumes: ["/home/git/.ssh"]
     startup:
       port_bindings: {2022: 22}
   ---
   -
     git_repos:
       command: create
   -
     gitolite:
       command: start

.. _commands:

Commands
````````

The following commands can be specified in the list of commands:

build
  builds a new image. This calls `build()` from docker-py_ with the options
  defined in the ``build`` part of the :ref:`composition document
  <composition>`.
create
  creates a new container. This calls `create_container()` from docker-py_ with
  the options defined in the ``creation`` part of the `composition document
  <composition>`_.  If the needed image does not exist, the `build` step is
  executed too.
start
  runs a container. This calls `start()` from docker-py_ with the options
  defined the ``startup`` part of the `composition document <composition>`_.
  If the container has not been created yet, the `create` step is executed too.
  If the container is already running, nothing is done.  Enable the debug mode
  if you want to be notified about skipped steps.

  **Arguments**:
    restart
      If set to ``True``, stops the container before it is started.
      (*Default*: ``False``)
    timeout
      The timeout to wait before the container is stopped, if *restart* is set
      to ``True``.  (*Default*: ``10``)
stop
  stops a running container.

  **Arguments**:
    timeout
      The timeout to wait before the container is stopped. (*Default*: ``10``)
backup
  backs up data from a container to a tar archive.

  **Arguments**:
    backup_dir
      the path on the host, where to create the backup archive.  (*Default*:
      ``'.'``)
    backup_name
      the name of the backup file to create (without the extension).
    source
      the path of the volume in the container to back-up

restore
  restores data from a tar archive into a volume of the container.

  **Arguments**:
    restore_dir
      the path on the host, where the tar archives can be found.  (*Default*:
      ``'.'``)
    restore_name
      the name of the archive to unpack (without the extension).

remove
  removes a container.  The container is stopped before it is removed.

  **Arguments**:
    v
      removes attached volumes with the container (*Default*: ``True``)
    timeout
      time to wait before the container is stopped.  (*Default*: ``10``)

execute
  executes a command either on the file system of the host container or in the
  special container named ``host`` that is only valid for this command.

  **Arguments**:
    run
      a command list to execute
    shell
      whether to execute it in a shell
    binds
      a dictionary of volume binds for the host system


.. _environments:

Environment files
`````````````````

Environment files 

.. _services:

Service and data directories
````````````````````````````

.. _YAML: http://yaml.org
.. _docker-py: http://docker-py.readthedocs.org

.. vim:set et sw=2 ts=8 spell spelllang=en:
