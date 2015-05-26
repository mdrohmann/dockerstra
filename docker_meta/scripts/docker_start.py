#!/usr/bin/env python
# PYTHON_ARGCOMPLETE_OK
import logging

import argcomplete

from docker_meta.logger import configure_logger
import docker_meta.configurations


if __name__ == "__main__":

    parser = docker_meta.configurations.create_parser()
    argcomplete.autocomplete(parser)
    args = parser.parse_args()

    configure_logger(
        debug=args.debug, verbosity=args.verbose,
        errorfiles=args.errfile, infofiles=args.infofile)

    # we prefer the following syntax for refactoring purposes.
    log = logging.getLogger(docker_meta.__name__)

    from docker_meta import container
    container.main(args)


# vim:set ft=python sw=4 et spell spelllang=en:
