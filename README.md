# Dockerstra

Orchestrating docker containers, to do in an automated manner.

## Motivation

I wanted to play around with docker containers, and finally convert all my
development environment into docker containers - including the collection of
test results, creating production-like configurations and the deployment on an
a remote machine.  I love the concept, but it turned out to be a little too
much work for a side project.  I believe that docker is great, but it takes a
while untile the overhead of creating a container for every package that you
want to use, pays off.

My conclusion is, that now I am cherry-picking the containers I want to use,
and do not care so much about automation of it.  Especially as right now it is
not clear, how the dockerization of database containers is supposed to work...
At least, the last time I checked...

## What works out of the box

You can install the package, which should install a `docker_start.py` script on your computer.  Running the command

    docker_start.py run dev_servers/start

should build, create and start a pypicloud, cgit, gitolite and apt-cacher-ng
server. It probably needs some tweaking.  But feel free to try it out.

Also, there are some documented docker build files in the
docker_meta/docker_meta/etc/services/ folder.
