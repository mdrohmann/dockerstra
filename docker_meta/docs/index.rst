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

Configuration
-------------

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
Usually, the *command* ``start`` describe how to start up the unit. If it
exists, the following commands are generated automatically:
  - ``build`` builds or pulls all required images,
  - ``create`` creates all containers without starting them,
  - ``stop`` stops all the containers in the unit,
  - ``cleanup`` removes all containers, that do not have a volume attached,
  - ``purge`` removes all containers, deletes volumes and removes base images,
  - ``backup`` backups all volumes attached to the containers in a unit,
  - ``restore`` restores all volumes attached to the containers in a unit,
  - ``test:<variants>`` runs a test of the specified variants ``<variants>``
    (cf. :ref:`unittests` for more information)
    and
  - ``restart`` restarts all containers

Each of these automatically generated containers (except for the
``test<variants>`` scripts can be overwritten by providing explicit
configuration files.

To list all available units, the command

.. code:: bash

   docker_start list --units
returns a list of all available ``UNITNAME/COMMAND`` tuples.

In order to print out the (potentially automatically created) configuration
file for a unit command, type

.. code:: bash

   docker_start run --print-unit UNITNAME/COMMAND

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

   import: unit/other

in which case the container descriptions are read from the file
``unit/other.yaml``.

Links
+++++

TODO: There needs to be a special handling of links and how to name them.  We
want to have a fall-back extra_hosts entry in case, the link to a container is
not available.  In that case, some service should be queried in order to find
out if the container is published on a different instance.

List of orders
**************

The second document describes a list of orders to execute on the previously
defined containers.  The document is a list of dictionaries with only one key
(the container name to execute a command on).  The value of this dictionary is
another dictionary specifying a :ref:`list of orders <orders>` and its arguments.

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

.. _orders:

Orders
``````

The following ``commands`` can be specified in the list of orders:

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
      removes attached volumes with the container (*Default*: ``False``)
    timeout
      time to wait before the container is stopped.  (*Default*: ``10``)

  If the ``v`` argument is unset, the container is **not** removed, if it has
  volumes attached to it, that would otherwise be lost in the docker nirvana.

remove_image
  removes the image associated with the container.

execute
  executes a command either
    1. on the file system of the container,
    2. in a temporary container created from the base image,
    3. inside a running container or even on
    4. the host system.

  For the latter choice, simply run the command in a *virtual container* called
  ``host``.  If an existing container is specified, by default, the command is
  executed on the file system of the container.  If you want to execute the
  command in a temporary container or in a running container, specify the
  ``type`` argument.  If no running container is found, and ``type`` is
  specified as ``in_running``, then ``temporary`` is used as a fall-back.

  **Arguments**:
    run
      a command list to execute
    shell
      whether to execute it in a shell
    binds
      a dictionary of volume binds for the host system
    type
      the execution type (one of ``file_system``, ``temporary``,
      ``in_running``)
tag
  tags an image with an additional tag
commit
  makes an updated image commit from a container
push
  pushes an image to a remote repository


Variants
++++++++

There is one argument that is valid of all commands in the list of orders,
called ``variants``.  This should get a list of strings.  If there are variants
specified in a configuration file, then the ``unit/command`` can be filtered in
the following way ``unit/command:variant1:variant2:...:variantn``.  This
selects only the orders tagged with the specified variant strings.  You could
use this, to define a minimal set of development servers for example.

.. _environments:

Environment files
`````````````````

Environment files define variables that are substituted in unit configuration
files, **before** they are parsed.  This allows to define the configuration
relatively to a directory that is specified in a host specific environment
file, for example.  Some environment variables are added automatically, most
importantly the variable ``{{DOCKERSTRA_CONF}}`` pointing to the base directory
of the configuration file structure.

Environment parametrization
***************************

As a special option, the ``start.yaml`` file can have a third document.  This
document defines a parametrization of the environment, that can be controlled
via the command line of the docker_start.py command.

The third document is simply a list of argparse.add_argument invocations:

.. code::yaml::

 - add_argument:
     name: '--language'
     short: '-l'
     choices: ['python', 'node']
     default: 'python'
     help: 'language of the host container'
 - add_argument:
     name: 'command'
     choices: ['initialize', 'exec', 'host-exec', 'bash', 'daemon', 'single', 'upgrade']
     default: 'initialize'
     help: 'define what to do with the container'
 - add_argument:
     name: 'args'
     nargs: argparse.REMAINDER

.. _services:

Service and data images
```````````````````````

The ``{{DOCKERSTRA_CONF}}`` directory usually has subdirectories ``services``
and ``data``.  A directory ``services/cgit`` eg., defines a service called
``cgit``, and should at least contain a ``Dockerfile`` describing how to
generate an image for this service.  Technically, there is no difference
between ``data`` and ``service`` directories, but data images in general only
contain volumes that can be mounted in a container derived from a service
image.


Updates
*******

If the unit directory has a command ``unit/update``, it should execute a script
to create a temporary container.  As the last order in this list, you can
specify a command called ``tests`` on the virtual container ``host``, with an
argument list called ``tests`` as well.  This list comprises command line
arguments for test runs, that will be executed in this step.  This way, the
``unit/update`` command is only considered successful if all the tests work
after updating the image.  This way, you can make sure, that the tag ``latest``
is only applied if the update worked.

For every ``unit/update`` command, |project| automatically generates a
``unit/upgrade`` command, that re-creates and re-starts all running containers
that depend on the updated image.

.. seealso:: :ref:`variants`

.. _unittests:

Unit tests
``````````

For each unit, tests are automatically generated from the meta information
provided in the configuration files.  The commands for test-cases have the form
``test:variant1:variant2:...:variantn`` If no meta-data are provided, the
following variants are available:

default
  runs unit/start and unit/stop and makes each order a test case.
full
  runs unit/start, unit/stop and unit/purge, and makes each order a test case.

.. note::

 The created containers (and images in case of the full variant) have
 pseudonames, such that hey do not interfere with production containers, unless
 the option ``--production`` is specified in which case the tests are executed
 with the production containers and images.

With meta-information, further variants can be specified.  Every unit should be
configured to provide a test variant called

check
  checking the successful start of daemons or jobs in containers.

The ``test:check`` command can be made available by providing fields ``daemon``
or ``job`` to the composition document.  An example ``daemon`` field

.. code:: yaml

  cgit:
    daemon:
      - GET:
           url: https://cgit.main:443
           status: 200
           re.match: "My personal git repositories"
           cert: ${DOCKERCONF}/cgit.main.pem
      - GET:
           url: http://{{.Network.IPAddress}}(cgit):80
           status: 200
           re.match: "My personal git repsoitories"
  e2e-check:
    start:
      links:
        - ["cgit.main", "nginx_server"]

tests that HTML requests to the two domains https://cgit.main:443 and
http://{{.Network.IPAddress}}(cgit):80  succeed.  Note, that the checks are run
from the special container e2e-check, that might need to add links to running
containers.

An example ``job`` field looks like the following:

.. code:: yaml

   backup:
     job:
       exit_code: 0
       logs:
         - re.match: "Success"

Furthermore, you can define your own test variants by adding them to your composition document:

.. code:: yaml

  python_programme:
    tests:
      pytests:
        execute: make test
        overwrites:
          volumes_from: python3_virtualenv
        extra:
          binds:
            /uploads:
              bind: /uploads
              ro: False
        files: ["coverage_html/", "junit-*.xml"]
        capture_logs: True

This defines a variant ``pytests`` that executes ``make test`` (either in a
container that is especially created for this job, or in an exec_job, if the
container is already running).  The specified files, that are created, are
copied into a data container called ``test_data`` with the directory structure:
``/archives/variant/container/TIMESTAMP/`` and ``/tests/variant/container/``
linking to the latest TIMESTAMP.

.. note::

  This can be combined with environment parsing to generate powerful test
  combinations.  In this case, the variant name should not be allowed to be
  parametrized, or alternatively change the environment???

.. note::

  The ``test_data`` container should also save the configured environment to
  have all the necessary data to reproduce the results.

.. note::

  If a test variant is configured for a container that is not started in the
  unit/start order of commands, it will be started during the test run, and
  removed after it is not needed anymore.

.. _YAML: http://yaml.org
.. _docker-py: http://docker-py.readthedocs.org

Extra scripts
-------------

TODO There is a script available, that updates nginx configuration files based on
the available hosts.  Maybe this should be a separate container, that I simply
restart...  I think that is a better idea.

.. vim:set et sw=2 ts=8 spell spelllang=en:
