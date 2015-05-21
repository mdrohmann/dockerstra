# -*- coding: utf-8 -*-
import argparse
import logging
import os
import re
import sys
from cStringIO import StringIO
from tempfile import TemporaryFile

import yaml
from jinja2 import Environment, PackageLoader
from pkg_resources import get_provider, resource_stream

from docker_meta import __name__ as docker_meta_name
from docker_meta import __version__ as docker_meta_version
from docker_meta.utils import deepupdate


log = logging.getLogger(docker_meta_name)


def unitListCompleter(prefix, parsed_args, **kwargs):
    c = Configuration(parsed_args.configdir)
    return [s for s in c.list_units() if s.startswith(prefix)]


def create_parser():
    parser = argparse.ArgumentParser(
        "docker_start.py")

    parser.add_argument(
        '-V', '--version', action='version',
        version='%(prog)s {}'.format(docker_meta_version),
        help='prints the version of the script')
    parser.add_argument(
        '-v', '--verbose', action='count',
        help='verbosity level')
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
        '-c', '--configdir', default=None,
        help='path to the configuration files (default is $HOME/.dockerstra)')
    subparsers = parser.add_subparsers(dest='subparser')
    run_group = subparsers.add_parser('run', help='Run a unit command')
    run_group.add_argument(
        '-e', '--environment', type=str, default='',
        help='Filename of YAML file with environment variables')
    run_group.add_argument(
        '-H', '--daemon', metavar="DAEMON",
        default='unix://var/run/docker.sock',
        help='socket for daemon connection')
    run_group.add_argument(
        'unitcommand', metavar="UNIT/COMMAND",
        help='The unit command to run').completer = unitListCompleter
    run_group.add_argument(
        '--print-only', action='store_true',
        help='Print the parsed unit command file to stdout.')
    list_group = subparsers.add_parser('list', help='list certain things')
    list_group.add_argument(
        '--units', action='store_true',
        help='List available unit files')
    list_group.add_argument(
        '--services', action='store_true',
        help='List available service files')
    return parser


def _substitute_line(pattern, s, environment):
    substituted = False
    for res in reversed(list(pattern.finditer(s))):
        key = res.group()[2:-2].strip()
        value = os.getenv(key, environment.get(key))
        if value:
            substituted = True
            s = s[:res.start()] + value + s[res.end():]
            log.debug(
                "substituting {} with {}:\n{}".format(key, value, s))
        else:
            log.warn(
                "Could not find a substitution for {}:\n{}".format(key, s))

    if substituted:
        s = _substitute_line(pattern, s, environment)

    return s


def environment_substutions(fh, buf, environment={}):
    pattern = re.compile(r'({{[^}]*}})')
    for s in fh.readlines():
        s = _substitute_line(pattern, s, environment)
        buf.write(s)

    buf.seek(0)


def modify_order_list(configurations, order_list, command):
    # return builds, creations and starts:

    def _parse(configurations, order_list):
        builds, creations, starts = [], [], []
        for item in order_list:
            name, order = item.items()[0]
            cmd = order['command']
            if cmd == 'start':
                starts.append(name)
            elif cmd == 'create':
                creations.append(name)
            elif cmd == 'build':
                build_config = configurations[name].get('build', {})
                if build_config.get('tag'):
                    builds.append(name)
        return builds, creations, starts

    builds, creations, starts = _parse(configurations, order_list)
    new_order_list = []

    stop_command = {'command': 'stop', 'timeout': 0}
    if command == 'cleanup':
        remove_order = {'command': 'remove', 'v': False}
    elif command == 'purge':
        remove_order = {'command': 'remove', 'v': True}

    if command == 'restart':
        for started in reversed(starts):
            new_order_list.append(
                {started: {'command': 'start', 'restart': True, 'timeout': 0}})
    if command in ['stop', 'cleanup', 'purge']:
        for started in reversed(starts):
            new_order_list.append({started: stop_command})
    if command in ['cleanup', 'purge']:
        for started in reversed(starts):
            new_order_list.append({started: remove_order})
        for created in reversed(creations):
            new_order_list.append({created: remove_order})

    if command == 'purge':
        for built in reversed(builds):
            new_order_list.append({built: {'command': 'remove_image'}})
    return new_order_list


def read_configuration(configfile, environment={}):
    if isinstance(environment, basestring):
        if environment:
            with open(environment, 'r') as fh:
                environment = yaml.load(fh)
        else:
            environment = {}

    buf = StringIO()
    with open(configfile, 'r') as fh:
        environment_substutions(fh, buf, environment)

    configs = yaml.load_all(buf)
    configs = list(configs)

    order_list = configs[1]
    configurations = configs[0]
    configdir = os.path.abspath(os.path.dirname(configfile))
    if 'import' in configurations:
        imported = {}
        importfiles = configurations.pop('import')
        if isinstance(importfiles, basestring):
            importfiles = [importfiles]

        for importfile in importfiles:
            parent_file = os.path.join(configdir, importfile)
            tmp_imported, _ = read_configuration(
                parent_file, environment)
            imported.update(tmp_imported)

        imported.update(configurations)
        configurations = imported

    return configurations, order_list


def silent_mkdirs(dirs):
    try:
        os.makedirs(dirs)
    except OSError as e:
        if e.errno != 17:
            raise e


def _iswritable(directory):
    try:
        tf = TemporaryFile(dir=directory)
        tf.close()
        return True
    except:
        return False


class Configuration(object):

    valid_basedirs = [
        (os.getenv('HOME', '/invalidchoice'), '.dockerstra',),
        (sys.prefix, os.path.join('etc', 'dockerstra')),
        ('/etc', 'dockerstra')
        ]

    def __init__(self, basedir=None):
        self.basedir = self._guess_basedir(basedir)
        log.debug('Using configuration directory {}'.format(self.basedir))
        self.initialized = self._isinitialized()
        provider = get_provider(docker_meta_name)
        self.provider = provider

    def _isinitialized(self, basedir=None):
        if basedir is None:
            basedir = self.basedir
        return os.path.exists(os.path.join(basedir, 'environments'))

    def _initialize_etc(self):
        path = 'etc'
        rpath = self.basedir

        def _walk(path, rpath):
            for filename in self.provider.resource_listdir(path):
                fullname = os.path.join(path, filename)
                rfullname = os.path.join(rpath, filename)
                if self.provider.resource_isdir(fullname):
                    silent_mkdirs(rfullname)
                    _walk(fullname, rfullname)
                else:
                    with open(rfullname, 'w') as fh:
                        instream = resource_stream(
                            docker_meta_name, fullname)
                        fh.write(instream.read())

        _walk(path, rpath)

    def _initialize_jinja(self):

        env = Environment(
            loader=PackageLoader(
                docker_meta_name,
                package_path='jinja'))
        render_opts = {'home': os.getenv('HOME')}

        for filename in env.list_templates():
            rfullname = os.path.join(self.basedir, filename)
            template = env.get_template(filename)
            silent_mkdirs(os.path.dirname(rfullname))
            with open(rfullname, 'w') as fh:
                fh.write(template.render(conf=render_opts))

    def initialize(self):
        assert not self.initialized

        self._initialize_etc()
        self._initialize_jinja()
        log.debug(
            "Wrote initial data to config directory: {}"
            .format(self.basedir))
        self.initialized = True

    def _guess_basedir(self, basedir=None):
        if basedir:
            if _iswritable(basedir):
                return basedir
            else:
                raise ValueError(
                    "Configuration directory {} does not exist or is not "
                    "write-able"
                    .format(basedir))
        else:
            # first check if initialized configuration exists already!
            for candidate, subdir in self.valid_basedirs:
                basedir = os.path.join(candidate, subdir)
                if self._isinitialized(basedir):
                    return basedir
            # if not, prepare the first write-able candidate for initialization
            for candidate, subdir in self.valid_basedirs:
                if _iswritable(candidate):
                    basedir = os.path.join(candidate, subdir)
                    silent_mkdirs(basedir)
                    return basedir

        raise RuntimeError("No write-able directory found")

    def get_abspath(self, path):
        fullname = os.path.join(self.basedir, path)
        if os.path.exists(fullname):
            return fullname
        else:
            return None

    def get_environment(self):
        environment = {'DOCKERSTRA_CONF': self.basedir}
        env_base_path = self.get_abspath('environments')
        for f in os.listdir(env_base_path):
            filename = os.path.join(env_base_path, f)
            with open(filename, 'r') as fh:
                env = yaml.load(fh)
                environment = deepupdate(environment, env)
        return environment

    def list_units(self):
        units_base_path = self.get_abspath('units')
        res = []
        for f in os.listdir(units_base_path):
            fullf = os.path.join(units_base_path, f)
            if os.path.isdir(fullf):
                fres = set([
                    f + '/' + os.path.splitext(n)[0] for n in os.listdir(
                        os.path.join(units_base_path, f))
                    if os.path.splitext(n)[1] == '.yaml'])
                if (f + '/start') in fres:
                    fres = fres.union(set(
                        [f + '/' + n for n in ['stop', 'cleanup', 'purge']]))
                res += list(fres)
            elif os.path.splitext(f)[1] == '.yaml':
                res.append(os.path.splitext(f)[0])
        return res

    def list_services(self):
        services_base_path = self.get_abspath('services')
        res = []
        for f in os.listdir(services_base_path):
            fullf = os.path.join(services_base_path, f)
            if (os.path.isdir(fullf) and os.path.exists(os.path.join(
                    fullf, 'Dockerfile'))):

                res.append(f)

        return res


# vim:set ft=python sw=4 et spell spelllang=en:
