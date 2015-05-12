#!/usr/bin/env python
import argparse
import logging

import docker_meta
from docker_meta import hosts_gen


def create_parser():
    """
    generates the parser for command line arguments.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '-o', '--hosts', type=str, default='/etc/hosts',
        help='path to hosts file')
    parser.add_argument(
        '-r', '--remove', action='store_true',
        help='remove the hosts')
    parser.add_argument(
        '-c', '--config', type=str,
        help='configfile with scenarios')
    parser.add_argument(
        'scenarios', nargs='+',
        help='the scenarios to add to the hosts file')
    return parser

if __name__ == '__main__':
    parser = create_parser()
    args = parser.parse_args()
    log = logging.getLogger(docker_meta.__name__)

    try:
        available_scenarios = hosts_gen.load_scenarios(args.config)
        hosts_gen.update_hostsfile(
            args.hosts, available_scenarios, args.scenarios,
            remove=args.remove)
    except:
        log.error("Failed to execute hosts_gen.", exc_info=1)

# vim:set ft=python sw=4 et spell spelllang=en:
