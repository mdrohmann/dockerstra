#! /usr/bin/env /bin/bash

NAME=${1:-server}

echo "Generate a new private key"
openssl genrsa -passout pass:x -des3 -out ${NAME}.pass.key 2048

echo "Strip the password"
openssl rsa -passin pass:x -in ${NAME}.pass.key -out ${NAME}.key
rm ${NAME}.pass.key

echo "Generate CSR"
openssl req -nodes -new -key ${NAME}.key -out ${NAME}.csr

echo "Generate self-signed certificate"
openssl x509 -req -days 365 -in ${NAME}.csr -signkey ${NAME}.key -out ${NAME}.crt

echo "Generate PEM file"
cat ${NAME}.key ${NAME}.crt > ${NAME}.pem
