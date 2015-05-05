#!/usr/bin/env python

import argparse

import docker

from docker_meta import read_configuration, run_configuration


def create_parser():
    parser = argparse.ArgumentParser("docker_start.py")
    parser.add_argument(
        'H', 'daemon', metavar="DAEMON", default='unix://var/run/docker.sock',
        help='socket for daemon connection')
    parser.add_argument(
        'configfile', metavar="CONFIG",
        help='Configuration file in YAML format')

if __name__ == "__main__":

    parser = create_parser()
    args = parser.parse_args()

    dc = docker.Client(args.daemon)

    configurations, order_list = read_configuration(args.configfile)
    run_configuration(configurations, order_list, dc)

# vim:set ft=python sw=4 et spell spelllang=en:
