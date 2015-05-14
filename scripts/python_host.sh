#!/bin/bash

VE=$1
VARIANT=$2

if [ "$VARIANT" ]; then
  PYTHONHOST_VARIANT=python_host_$VARIANT
else
  PYTHONHOST_VARIANT=python_host
fi

echo VIRTUALENV="${VE:-minimal}" docker_start.py -H 172.17.42.1:4243 -dvv -e ~/gistin/docker/systemd/configfiles/juergen_environment.yaml ~/gistin/docker/systemd/configfiles/source_hosts/${PYTHONHOST_VARIANT}.yaml
VIRTUALENV="${VE:-minimal}" docker_start.py -H 172.17.42.1:4243 -dvv -e ~/gistin/docker/systemd/configfiles/juergen_environment.yaml ~/gistin/docker/systemd/configfiles/source_hosts/${PYTHONHOST_VARIANT}.yaml
