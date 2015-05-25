# -*- coding: utf-8 -*-
import argparse
from copy import copy
import logging
import os
import sys
from tempfile import TemporaryFile

import yaml
from jinja2 import (
    Environment, PackageLoader, BaseLoader, ChoiceLoader, FileSystemLoader,
    TemplateNotFound)
from pkg_resources import get_provider, resource_stream

from docker_meta import (
    __name__ as docker_meta_name, __version__ as docker_meta_version)
from docker_meta.utils import deepupdate


log = logging.getLogger(docker_meta_name)


class UnitExtensionLoader(BaseLoader):

    def __init__(self, path):
        self.path = path

    def get_source(self, environment, template):
        path = os.path.join(self.path, template, 'extensions.yaml')
        if not os.path.exists(path):
            raise TemplateNotFound(template)
        mtime = os.path.getmtime(path)
        with file(path) as f:
            source = f.read().decode('utf-8')
        return source, path, lambda: mtime == os.path.getmtime(path)

    def list_templates(self):
        templates = set(
            [p for p in os.listdir(self.path)
             if os.path.exists(os.path.join(p, 'extensions.yaml'))]
        )
        return sorted(templates)


class UnitListCompleter(object):

    def __init__(self, showCommands=True):
        self.showCommands = showCommands

    def complete(self, prefix, parsed_args, **kwargs):
        c = Configuration(parsed_args.configdir)
        return [
            s for s in c.list_units(self.showCommands) if s.startswith(prefix)]


def serviceListCompleter(prefix, parsed_args, **kwargs):
    c = Configuration(parsed_args.configdir)
    return [
        s for s in c.list_services() if s.startswith(prefix)]


def create_parser():
    parser = argparse.ArgumentParser(
        "docker_start.py", add_help=True)

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
    # initialization subparser (currently empty)
    subparsers.add_parser(
        'init', help='Initialize the configuration directory')
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
        help='The unit command to run'
    ).completer = UnitListCompleter().complete
    run_group.add_argument(
        '--print-substitutions', action='store_true',
        help='Print the substituted unit command file to stdout.')
    run_group.add_argument(
        '--print-only', action='store_true',
        help='Print the parsed unit command file to stdout.')
    run_group.add_argument(
        'args', nargs=argparse.REMAINDER,
        help='arguments send as command to the docker containers')
    list_group = subparsers.add_parser('list', help='list certain things')
    list_group.add_argument(
        '--units', action='store_true',
        help='List available unit files')
    list_group.add_argument(
        '--services', action='store_true',
        help='List available service files')
    help_group = subparsers.add_parser(
        'help', help='Show help on services or units')
    help_choice = help_group.add_mutually_exclusive_group(required=True)
    help_choice.add_argument(
        '--unit', metavar='UNIT', type=str,
        help='unit for which a help text should be shown'
    ).completer = UnitListCompleter(False).complete
    help_choice.add_argument(
        '--service', metavar='SERVICE', type=str,
        help='service for which a help text should be shown'
    ).completer = serviceListCompleter
    return parser


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
    """
    controls the configuration directory.

    TODO: I also need a control for active environment substitutions of a unit.

    I am ignoring this right now, until the environment substitution feature is
    implemented.
    """

    valid_basedirs = [
        (os.getenv('HOME', '/invalidchoice'), '.dockerstra',),
        (sys.prefix, os.path.join('etc', 'dockerstra')),
        ('/etc', 'dockerstra')
        ]

    def __init__(self, basedir=None, args=[]):
        self.basedir = self._guess_basedir(basedir)
        log.debug('Using configuration directory {}'.format(self.basedir))
        self.initialized = self._isinitialized()
        provider = get_provider(docker_meta_name)
        self.provider = provider
        self._environment = None
        self.args = args

    def update_environment(self, filename):
        self.environment.update(self._get_environment())
        if filename:
            with open(filename, 'r') as fh:
                new_env = yaml.load(fh)
            self.environment.update(new_env)
        self.environment.update({'osenv': os.environ})

    @property
    def environment(self):
        if self._environment:
            return self._environment
        else:
            self._environment = self._get_environment()
            return self._environment

    def get_unit_globals(self, unit):
        candidate = os.path.join(unit, 'globals')
        configfile = self.get_abspath(
            os.path.join('units', '{}.yaml'.format(candidate)))
        if configfile:
            # do an environment substitution without globals first
            buf = self.unit_substitutions(candidate)
            return yaml.load(buf)
        else:
            return None

    def parse_args(self, global_config):
        parser = argparse.ArgumentParser()
        for arg in global_config.get('parser', []):
            k, v = arg.items()[0]
            assert k == 'argument'
            args = [
                a for a in [v.pop('short', None), v.pop('name', None)] if a]
            if v.get('nargs', '') == 'argparse.REMAINDER':
                v['nargs'] = argparse.REMAINDER
            parser.add_argument(*args, **v)
        args = parser.parse_args(self.args)
        return {'args': args.__dict__}

    def unit_substitutions(
            self, unitcommand, global_config=None):

        extra_environment = {}
        loader = FileSystemLoader(
            self.get_abspath(os.path.join('units')))

        if global_config:
            extra_environment = self.parse_args(global_config)

            if 'jinja' in global_config:
                macroloader_path = (
                    global_config['jinja'].get('macroloader_path'))
                if macroloader_path:
                    macroloader = UnitExtensionLoader(macroloader_path)
                    loader = ChoiceLoader([loader, macroloader])
        env = Environment(loader=loader)

        t = env.get_template('{}.yaml'.format(unitcommand))

        extra_environment.update(self.environment)
        if global_config:
            extra_environment.update(global_config.get('environment', {}))
        return t.render(**extra_environment)

    def get_base_command(self, unit, command):
        candidate = self.get_abspath(
            os.path.join('units', unit, '{}.yaml'.format(command)))
        if candidate:
            return '{}/{}'.format(unit, command)
        elif command != 'start':
            return self.get_base_command(unit, 'start')

        raise RuntimeError(
            "No configuration found for unit/command tuple {}/{}!"
            .format(unit, command))

    def modify_order_list(self, configurations, order_list, command):
        # return builds, creations and starts:

        new_configurations = configurations

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
                    {started:
                        {'command': 'start', 'restart': True, 'timeout': 0}})
        if command in ['stop', 'cleanup', 'purge']:
            for started in reversed(starts):
                new_order_list.append({started: copy(stop_command)})
        if command in ['cleanup', 'purge']:
            for started in reversed(starts):
                new_order_list.append({started: copy(remove_order)})
            for created in reversed(creations):
                new_order_list.append({created: copy(remove_order)})

        if command == 'purge':
            for built in reversed(builds):
                new_order_list.append({built: {'command': 'remove_image'}})
        return new_configurations, new_order_list

    def read_unit_configuration(self, unitcommand, print_substitutions=False):
        unit, command = self.split_unit_command(unitcommand)
        unit_globals = self.get_unit_globals(unit)

        candidate = self.get_base_command(unit, command)

        buf = self.unit_substitutions(candidate, unit_globals)
        if print_substitutions:
            return buf

        configs = yaml.load_all(buf)
        configs = list(configs)

        order_list = configs[1]
        configurations = configs[0]
        if 'import' in configurations:
            imported = {}
            importfiles = configurations.pop('import')
            if isinstance(importfiles, basestring):
                importfiles = [importfiles]

            for importfile in importfiles:
                tmp_imported, _ = self.read_unit_configuration(
                    importfile)
                imported.update(tmp_imported)

            imported.update(configurations)
            configurations = imported

        # automatically generate the configurations from the 'start'-command
        if candidate != unitcommand:
            configurations, order_list = self.modify_order_list(
                configurations, order_list, command)

        return configurations, order_list

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

    def _get_environment(self):
        environment = {'DOCKERSTRA_CONF': self.basedir}
        env_base_path = self.get_abspath('environments')
        if env_base_path:
            for f in os.listdir(env_base_path):
                filename = os.path.join(env_base_path, f)
                with open(filename, 'r') as fh:
                    env = yaml.load(fh)
                    environment = deepupdate(environment, env)
        return environment

    def split_unit_command(self, unitcommand):
        return unitcommand.rsplit('/', 1)

    def list_tagged_variants(self, base_config):
        raise NotImplementedError()

    def list_test_variants(self, base_config):
        raise NotImplementedError()

    def list_variants(self, unitcommand):
        unit, command = self.split_unit_command(unitcommand)
        if command == 'test':
            return self.list_test_variants(unit)
        else:
            base_config = self.get_base_command(unit, command)
            if not base_config:
                raise RuntimeError(
                    "Invalid command: No configuration file for {}/{}"
                    .format(unit, command))
            return self.list_tagged_variants(base_config)

    def list_units(self, list_commands=True):
        units_base_path = self.get_abspath('units')
        res = []
        for f in os.listdir(units_base_path):
            fullf = os.path.join(units_base_path, f)
            if os.path.isdir(fullf):
                pre_filtered = [
                    n for n in os.listdir(
                        os.path.join(units_base_path, f))
                    if os.path.splitext(n)[1] == '.yaml']
                fres = set([
                    f + '/' + os.path.splitext(n)[0] for n in pre_filtered])
            elif os.path.splitext(f)[1] == '.yaml':
                fres = set([os.path.splitext(f)[0] + '/start'])

            if list_commands:
                if (f + '/start') in fres:
                    fres.update(set(
                        ['{}/{}'.format(f, n) for n in [
                            'stop', 'restart', 'cleanup', 'purge',
                            'test', 'build', 'create', 'backup', 'restore']]))
                fres.discard('{}/{}'.format(f, 'globals'))
                res += list(fres)
            elif fres:
                res.append(f)
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
