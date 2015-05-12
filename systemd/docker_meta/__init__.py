import logging
import os
import re
import time
from cStringIO import StringIO

import utils

import docker
import yaml
from pkg_resources import get_distribution


__all__ = [
    'utils', 'read_configuration',
    'run_configuration', 'DockerContainer',
    '__version__']

__version__ = get_distribution(__name__).version


# logging.getLogger(__name__).addHandler(logging.NullHandler)
log = logging.getLogger(__name__)


def environment_substutions(fh, buf, environment={}):
    pattern = re.compile(r'({{[^}]*}})')
    for s in fh.readlines():
        for res in reversed(list(pattern.finditer(s))):
            key = res.group()[2:-2].strip()
            value = environment.get(key, os.getenv(key))
            if value:
                s = s[:res.start()] + value + s[res.end():]
        buf.write(s)

    buf.seek(0)


def read_configuration(configfile, environment={}):
    if type(environment) == basestring:
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
    if len(configurations) == 1 and 'import' in configurations:
        parent_file = os.path.abspath(
            os.path.join(
                os.path.dirname(configfile), configurations['import']))
        configurations, _ = read_configuration(parent_file)

    return configurations, order_list


def run_configuration(configurations, order_list, dc, stop_all=False):

    for item in order_list:

        name, orders = item.items()[0]
        c = configurations.get(name, {})
        if not c and name != 'host':
            raise RuntimeError(
                "Could not find a configuration for container {}".format(name))
        cmd = orders['command']

        container = DockerContainer(dc, name, **c)

        timeout = orders.pop('timeout', 10)
        wait_time = orders.pop('wait', 0)

        if stop_all:
            cmd = 'stop'
            timeout = 0

        log.info('Executing step {} on {}'.format(cmd, name))
        if cmd == 'build':
            container.build_image()
        elif cmd == 'create':
            container.create()
        elif cmd == 'start':
            restart = orders.pop('restart', False)
            container.start(restart, timeout)
        elif cmd == 'restore':
            restore_dir = os.path.abspath(orders.get('restore_dir', '.'))
            restore_name = orders.get('restore_name', 'backup')
            container.restore(restore_dir, restore_name)
        elif cmd == 'backup':
            backup_dir = os.path.abspath(orders.get('backup_dir', '.'))
            source_dir = orders.get('source', '/')
            backup_name = orders.get('backup_name', 'backup')
            overwrite = orders.get('overwrite', False)
            container.backup(source_dir, backup_dir, backup_name, overwrite)
        elif cmd == 'stop':
            container.stop(timeout)
        elif cmd == 'remove':
            v = orders.pop('v', True)
            container.remove(v, timeout)
        elif cmd == 'execute':
            shell = orders.pop('shell', False)
            binds = orders.pop('binds', {})
            container.execute(orders['run'], shell, binds)
        else:
            raise ValueError(
                "Invalid command {} for container {}".format(cmd, name))

        time.sleep(wait_time)


class DockerContainer(object):

    def __init__(self, dc, name, creation={}, startup={}, build={}):
        self.dc = dc
        self.name = name
        self.creation = creation
        self.startup = startup
        self.build = build
        self._update_start_config()
        self._update_creation_config()
        log.debug("Initialized docker container {}".format(name))

    def _update_start_config(self):
        if 'binds' in self.startup:
            binds = self.startup['binds']
            nbinds = {}
            for fro, to in binds.iteritems():
                if 'path' not in self.build:
                    raise ValueError(
                        "The path key needs to be specified for ${{PWD}} "
                        "replacement in startup configuration of {name}"
                        .format(name=self.name))
                nfro = fro.replace(
                    '${PWD}', os.path.abspath(self.build['path']))
                nbinds[nfro] = to
            self.startup['binds'] = nbinds

    def _update_creation_config(self):
        if 'port_bindings' in self.startup:
            ports = self.startup['port_bindings'].keys()
            cports = set(self.creation.pop('ports', []) + ports)
            self.creation['ports'] = list(cports)

    def is_started(self):
        res = self.dc.inspect_container(self.get_container())
        return res['State']['Running']

    def get_image(self, name=None):
        if name is None:
            name = self.creation.get('image', self.build.get('tag', None))
        name_split = name.rsplit(':', 1)
        images = self.dc.images(name_split[0])
        if len(images) == 1:
            if len(name_split) == 2 and name not in images[0]['RepoTags']:
                return {}
            else:
                return images[0]
        elif len(images) == 0:
            return {}
        else:
            raise RuntimeError("This should not happen!")

    def get_container(self):
        containers = self.dc.containers(
            filters={'name': "^/{}$".format(self.name)}, all=True)
        if len(containers) == 1:
            return containers[0]
        elif len(containers) == 0:
            return {}
        else:
            raise RuntimeError("This should not happen!")

    def __str__(self):
        return self.get_container().get('Id', 'No id yet')

    def start(self, restart=False, timeout=10):
        container = self.get_container()
        if container:
            if restart or not self.is_started():
                self.dc.restart(container, timeout)
                log.info("Started container {}".format(self.name))
            else:
                log.debug(
                    "Container {} is already started. (skipped)  "
                    "Add 'restart=True' to arguments to restart container."
                    .format(self.name))
        else:
            try:
                log.debug(
                    "Cannot start the container {}.  Trying to create it."
                    .format(self.name))
                # Create the container ...
                self.create()
                # ... and then start it.
                self.dc.start(container=self.name, **self.startup)
                log.info("Started container {}".format(self.name))
            except Exception as e:
                raise RuntimeError(
                    "Container {} does not exist, and I do not know how to "
                    "create it:\n {}"
                    .format(self.name, e))

    def build_image(self):
        imjson = self.get_image()
        if imjson:
            log.debug(
                "Image {} already exists. (skipped)"
                .format(imjson['RepoTags'][0]))
            return None
        if self.build:
            # set the default to rm==True
            if 'rm' not in self.build:
                log.debug(
                    "Setting build flag 'rm' to True in container {}"
                    .format(self.name))
                self.build['rm'] = True

            for line in self.dc.build(**self.build):
                log.info(line, extra={'type': 'output', 'cmd': 'build'})
            log.info(
                "Successfully built the image {}"
                .format(self.build.get(
                    'tag', 'for container {}'.format(self.name))))
        else:
            image = self.creation.get('image')
            tag = self.creation.get('tag', 'latest')
            if image:
                try:
                    for line in self.dc.pull(
                            repository=image, tag=tag, stream=True):
                        log.info(line, extra={'type': 'output', 'cmd': 'pull'})
                        # print(response.get('progressDetail'))
                    log.info(
                        "Successfully pulled the image {}".format(image))
                except Exception as e:
                    raise RuntimeError(
                        "No build instructions for image {}:\n{}"
                        .format(image, e))
            else:
                raise RuntimeError("No image to pull or build given.")

    def _log_output(self, line, command):
        log.info(line, extra={'type': 'output', 'cmd': command, 'dc': self})

    def inspect(self):
        return self.dc.inspect_container(self.name)

    def _substitute_run_args(self, args):
        new_args = []
        pattern = re.compile(
            '^{{(?P<formula>.*)}}(\((?P<container>[^)]*)\))?$')
        for arg in args:
            res = pattern.match(arg.strip())
            if res:
                gd = res.groupdict()
                if gd['container']:
                    if gd['container'].startswith('image://'):
                        inspect = self.dc.inspect_image(gd['container'][8:])
                    else:
                        inspect = self.dc.inspect_container(gd['container'])
                else:
                    inspect = self.dc.inspect_container(self.name)

                new_arg = eval(res.groups()[0], {}, {'inspect': inspect})
            else:
                new_arg = arg

            if type(new_arg) == list:
                new_args += new_arg
            else:
                new_args.append(new_arg)
        return new_args

    def execute(self, run_args, shell=False, binds={}):
        self._substitute_run_args(run_args)

        if self.name == 'host':

            ret = utils.spawnProcess(
                run_args,
                outhandler=lambda data: self._log_output(data, 'execute'),
                errhandler=log.error,
                shell=shell)
            if ret != 0:
                raise RuntimeError(
                    "Execution of {} failed with error code {}"
                    .format(' '.join(run_args), ret))
            return ret
        else:
            self.manipulate_volumes(run_args, binds)

    def create(self):
        if (not self.creation) and (not self.build):
            raise RuntimeError(
                "No configuration to create the container given.")

        self.creation['name'] = self.name
        try:
            self.creation['image'] = self.build.get(
                'tag', self.creation.get('image'))
            log.debug(
                "set creation fields for 'name' and 'image' to {name} and "
                "{image}".format(**(self.creation)))
        except KeyError:
            raise RuntimeError(
                "Creation requires a build tag or an image id.")
        if self.get_container():
            log.debug(
                "The container {} seems to exist already (skipped)."
                .format(self.name))
            return None
        try:
            self._log_output(
                self.dc.create_container(**self.creation), 'create_container')
            log.info("Successfully created the container {}".format(self.name))
        except docker.errors.APIError as e:
            if 'No such image' in str(e):
                log.debug(
                    "The image {} to create the container {} did not exist.  "
                    "Trying to build it..."
                    .format(self.creation["image"], self.name))
                self.build_image()
                self.dc.create_container(**self.creation)
                log.info(
                    "Successfully created the container {}."
                    .format(self.name))
            else:
                raise e

    def manipulate_volumes(self, command, binds={}):
        info = self.dc.create_container(
            'busybox:latest',
            detach=False,
            command=command)

        self.dc.start(
            info,
            volumes_from=self.name,
            binds=binds)

        exit_code = self.dc.wait(info)

        stdout = self.dc.logs(info)

        self.dc.remove_container(info)

        info = (
            'Executing command {} on container {}.  Output follows\n{}'
            .format(command, self.name, stdout))
        self._log_output(info, 'manipulate_volumes')

        if exit_code != 0:
            stderr = self.dc.logs(info, stdout=False, stderr=True, tail=3)
            raise RuntimeError(
                "Manipulation of volume {} failed with exit code {}:\n{}"
                .format(command, exit_code, stderr))

        log.info(
            "Successfully executed command {} in container {}."
            .format(command, self.name))

    def backup(self, source, target_dir, target_name, overwrite=False):
        targetfile = os.path.join(target_dir, '{}.tar'.format(target_name))
        gzipped_target_file = '{}.gz'.format(targetfile)
        if not overwrite and (
                os.path.exists(targetfile)
                or os.path.exists(gzipped_target_file)):
            raise RuntimeError(
                "Backup failed: The target {} exists already in directory {}. "
                "Add 'overwrite=True' to orders to overwrite"
                .format(target_name, target_dir))

        log.info(
            "Backup of container {}: {} -> {}/{}"
            .format(self.name, source, target_dir, target_name))
        res = self.manipulate_volumes(
            command=[
                'tar', 'cvf', '/backup/{}.tar'.format(target_name), source],
            binds={target_dir: {'bind': '/backup', 'ro': False}})
        os.system('gzip {}.tar'.format(os.path.join(target_dir, target_name)))
        return res

    def restore(self, restore_dir, restore_name):
        log.info(
            "Restoring container {} from {}/{}"
            .format(self.name, restore_dir, restore_name))

        archive = '{}.tar'.format(
            os.path.join(restore_dir, restore_name))
        gzipped_archive = '{}.gz'.format(archive)
        gzip = False
        if os.path.exists(gzipped_archive):
            log.debug(
                'unzipping the tar archive {} first'.format(gzipped_archive))
            os.system('gunzip {}'.format(gzipped_archive))
            gzip = True
        res = self.manipulate_volumes(
            command=[
                'tar', 'xf', '/backup/{}.tar'.format(restore_name)],
            binds={restore_dir: {'bind': '/backup', 'ro': True}})
        if gzip:
            os.system('gzip {}'.format(archive))

        return res

    def stop(self, timeout=10):
        container = self.get_container()
        if self.is_started():
            self.dc.stop(container, timeout)
            log.info("Successfully stopped container {}".format(self.name))
        else:
            log.debug(
                "Not stopping container {} as it was not running"
                .format(self.name))

    def remove(self, v=True, timeout=10):
        self.stop(timeout)
        container = self.get_container()
        if container:
            self.dc.remove_container(container, v)
            log.info("Successfully removed container {}".format(self.name))
        else:
            log.debug(
                "Not removing container {} as it did not exist."
                .format(self.name))

# vim:set ft=python sw=4 et spell spelllang=en:
