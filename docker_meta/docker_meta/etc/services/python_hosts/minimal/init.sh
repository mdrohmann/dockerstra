#!/bin/bash

source $HOME/.bashrc

sudo chown python:python /virtualenv
sudo chown -R python:python /data

if ! [ -f /virtualenv/bin/activate ]; then
    virtualenv -p $PYTHON_EXE /virtualenv
fi

source $HOME/.bashrc

if [ -f /data/requirements.txt ]; then
    pip install --upgrade -r /data/requirements.txt
fi

if [ -d "$HOME/init.d" ]; then
    for file in $HOME/init.d/*; do
        source $file
    done
fi

# vim:set et sw=4:
