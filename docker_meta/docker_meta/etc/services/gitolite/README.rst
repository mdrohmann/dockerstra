Gitolite
========

Runs a gitolite_ server.

Configuration
-------------

No, configuration is necessary.  On its first start, the initial gitolite
repositories including an admin user with a new SSH key are generated, and
re-used in the following.  Refer to the usage information below on how to use
this container after it is started.

Dependent images
----------------

The gitolite server depends on the following images:

   - data/repositories
   - mdrohmann/gitolite

They are built as follows:

::

   cd data/repositories
   sudo docker build --tag=data/repositories .

and

::

   cd services/gitolite
   sudo docker build --tag mdrohmann/gitolite .


Usage
-----

1. Create a storage container

   ::

      sudo docker create --name=git_repos data/repositories

2. Run the gitolite container and bind it to the git_repos data container.

   ::

      sudo docker run -p 2022:22 --volumes-from=git_repos -v /home/git/.ssh \
         --name=gitolite mdrohmann/gitolite

3. Create an entry in your .ssh/config files like this:

   ::

      Host gitolite_local
      HostName localhost
      Port 2022
      User git
      Compression no
      ForwardX11 no

4. Clone the admin repository like this:

   ::

      git clone git@gitolite_local:gitolite-admin

   and add user keys and new repositories.  Easy-peasy...

.. _gitolite: http://gitolite.com/gitolite
