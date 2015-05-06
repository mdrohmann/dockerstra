#!/usr/bin/env python

import argparse
import sys

import docker

from docker_meta import read_configuration, run_configuration
import docker_meta


def create_parser():
    parser = argparse.ArgumentParser("docker_start.py")
    parser.add_argument(
        '-v', '--version', action='store_true',
        help='display version information')
    parser.add_argument(
        '-s', '--stop-all', action='store_true',
        help='Stop all the processes that are touched by the configuration')
    parser.add_argument(
        '-H', '--daemon', metavar="DAEMON",
        default='unix://var/run/docker.sock',
        help='socket for daemon connection')
    parser.add_argument(
        'configfile', metavar="CONFIG",
        help='Configuration file in YAML format')
    return parser

if __name__ == "__main__":

    parser = create_parser()
    args = parser.parse_args()

    if args.version:
        print docker_meta.__version__
        sys.exit(0)

    dc = docker.Client(args.daemon)

    configurations, order_list = read_configuration(args.configfile)
    run_configuration(configurations, order_list, dc, args.stop_all)

# vim:set ft=python sw=4 et spell spelllang=en:
