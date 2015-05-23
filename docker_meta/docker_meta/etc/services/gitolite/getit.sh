#!/usr/bin/env sh

REPO=https://raw.githubusercontent.com/miracle2k/dockerfiles/master

for file in Dockerfile init.sh
do
   curl $REPO/gitolite/$file > $file
done

chmod 755 init.sh
