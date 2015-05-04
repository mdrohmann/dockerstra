Gitolite
========

Runs a gitolite_ server.


Dependent images
----------------

The gitolite server depends on the following images:

   - data/repositories
   - mdrohmann/gitolite

They are built as follows:

::

   cd data/repositories
   sudo docker build --tag=data/repositories .
   sudo docker build --tag=data/repositories:base -f gitolite_base_Dockerfile .

and

::

   cd services/gitolite
   sudo docker build --tag mdrohmann/gitolite .


Usage
-----

1. Create a storage container

   ::

      sudo docker create --name=git_repos data/repositories:base

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

.. _gitolite: http://gitolite.com/gitolite
