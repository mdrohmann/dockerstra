Pypicloud
=========

Runs a pypicloud_ server.

Dependent images
----------------

The pypicloud_ server depends on the following images:

   - data/pypicloud
   - mdrohmann/pypicloud

They are built as follows:

::

   cd data/pypicloud
   sudo docker build --tag=data/pypicloud .

and

::

   cd services/pypicloud
   sudo docker build --tag mdrohmann/pypicloud .


Usage
-----

1. Create a storage container

   ::

      sudo docker create --name=pypi_data data/pypicloud

2. Run the gitolite container and bind it to the pypi_data data container.

   ::

     cd services/pypicloud
     sudo docker run --name pypicloud -v $PWD/pypicloud:/etc/pypicloud \
          -d -p 3031:3031 --volumes-from=data_pypi mdrohmann/pypicloud

3. Update your nginx configuration, by adding the following

   ::

      upstream docker-pypicloud {
        server localhost:3031;
      }

      server {
        server_name pypi-internal pypi-internal.main;
        listen 80;
        listen 443 ssl;

        ssl_certificate /etc/nginx/ssl/nginx.crt;
        ssl_certificate_key /etc/nginx/ssl/nginx.key;

        proxy_set_header Host    $http_host;
        proxy_set_header X-Real-IP $remote_addr;

        client_max_body_size 0;

        chunked_transfer_encoding on;

        location / {
          proxy_pass http://docker-pypicloud;
        }
      }

   The SSL certificate creation is described eg., in this
   `guide <https://devcenter.heroku.com/articles/ssl-certificate-self>`_.

   .. attention::

      Afterwards, the certificate file needs to be installed on the system:

       ::

         cp server.crt \
           /usr/local/share/ca-certificates/pypi-internal.crt
         update-ca-certificates

      See ``man update-ca-certificates`` for details.

4. Every client, that uses the pypi-server, should use pypi configurations from
   this directory:

   ::

      cp .pypirc ~/.pypirc
      cp .pip.conf ~/.pip/pip.conf

5. Upload packages with

   ::

      python setup.py sdist upload -r internal


There are
`alternatives for the pypicloud <https://wiki.python.org/moin/PyPiImplementations>`_.

.. _pypicloud: http://pypicloud.readthedocs.org/en/latest/
