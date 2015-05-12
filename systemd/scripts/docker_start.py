#!/usr/bin/env python

import argparse
import logging

import docker

from docker_meta import read_configuration, run_configuration
from docker_meta.logger import configure_logger
import docker_meta


def create_parser():
    parser = argparse.ArgumentParser(
        "docker_start.py")
    parser.add_argument(
        '-V', '--version', action='version',
        version='%(prog)s {}'.format(docker_meta.__version__),
        help='prints the version of the script')
    parser.add_argument(
        '-v', '--verbose', action='count',
        help='verbosity level')
    parser.add_argument(
        '-e', '--environment', type=str, default='',
        help='Filename of YAML file with environment variables')
    parser.add_argument(
        '-d', '--debug', action='store_true',
        help='Output debug information')
    parser.add_argument(
        '-l', '--errfile', default=None,
        help='logfile for errors (deactivates stderr)')
    parser.add_argument(
        '-i', '--infofile', default=None,
        help='logfile for infos (deactivates stdout)')
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

    configure_logger(
        debug=args.debug, verbosity=args.verbose,
        errorfile=args.errfile, infofile=args.infofile)

    # we prefer the following syntax for refactoring purposes.
    log = logging.getLogger(docker_meta.__name__)

    dc = docker.Client(args.daemon)

    try:
        configurations, order_list, config_dir = read_configuration(
            args.configfile, args.environment)

        run_configuration(
            configurations, order_list, config_dir, dc, args.stop_all)
    except:
        log.error("Failed to execute the recipe.", exc_info=1)

# vim:set ft=python sw=4 et spell spelllang=en:
