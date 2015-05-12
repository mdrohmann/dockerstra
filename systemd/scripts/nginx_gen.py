#!/usr/bin/env python
import argparse
import logging

import docker_meta
from docker_meta import nginx_gen


def create_parser():
    """
    generates the parser for command line arguments.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '-o', '--output', type=str,
        help='path to nginx configuration')
    parser.add_argument(
        '-r', '--remove', action='store_true',
        help='remove the configurations')
    parser.add_argument(
        'containers', nargs='+',
        help='vhost:container tuples')
    return parser


if __name__ == '__main__':

    log = logging.getLogger(docker_meta.__name__)
    parser = create_parser()
    args = parser.parse_args()

    try:
        nginx_gen.update_configuration(
            args.output, args.containers, remove=args.remove)
    except:
        log.error("Failed to execute nginx_gen.", exc_info=1)

# vim:set ft=python sw=4 et spell spelllang=en:
