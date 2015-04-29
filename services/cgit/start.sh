#! /bin/sh

set -e

[ ! -f /data/lighttpd.conf ] && cp /etc/lighttpd/lighttpd.conf.default /data/lighttpd.conf
[ ! -f /data/cgitrc ] && cp /etc/cgitrc.default /data/cgitrc

# delete cache on every restart
rm -rf /var/cache/cgit

mkdir /var/cache/cgit

lighttpd -Df /data/lighttpd.conf
