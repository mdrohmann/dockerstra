# -*- coding: utf-8 -*-
import logging
import os
import sys
from tempfile import TemporaryFile

import yaml
from jinja2 import Environment, PackageLoader
from pkg_resources import get_provider, resource_stream

import docker_meta
from docker_meta.utils import deepupdate


log = logging.getLogger(docker_meta.__name__)


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
        provider = get_provider(docker_meta.__name__)
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
                            docker_meta.__name__, fullname)
                        fh.write(instream.read())

        _walk(path, rpath)

    def _initialize_jinja(self):

        env = Environment(
            loader=PackageLoader(
                docker_meta.__name__,
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
