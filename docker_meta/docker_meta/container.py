# -*- coding: utf-8 -*-
import json
import logging
import os
import re
import time

import docker
import yaml

import docker_meta.utils_spawn
from docker_meta.configurations import (
    read_configuration, Configuration, modify_order_list)


log = logging.getLogger(docker_meta.__name__)


def get_docker_client(daemon):
    return docker.Client(daemon)


def _check_for_and_print_readme(root, directory):
    readme_options = [
        'README.rst',
        'readme.rst',
        'README',
        'README.md',
        'readme.md',
    ]

    base = os.path.join(root, directory)

    for candidate in readme_options:
        fp = os.path.join(base, candidate)
        if os.path.exists(fp):
            break

    if os.path.exists(fp):
        with open(fp, 'r') as fh:
            print fh.read()
    else:
        log.warn('Could not find a README file in {}'.format(base))


def main_help(config, args):

    if args.unit:
        _check_for_and_print_readme(
            config.get_abspath('units'), args.unit)
    if args.service:
        _check_for_and_print_readme(
            config.get_abspath('services'), args.service)


def main_run(config, args):

    dc = get_docker_client(args.daemon)

    environment = config.get_environment()

    if args.environment:
        with open(args.environment, 'r') as fh:
            new_env = yaml.load(fh)
            environment.update(new_env)

    # transform the unitcommand to a configfile here
    unit, command = config.split_unit_command(args.unitcommand)
    configfile = config.get_abspath(
        os.path.join('units', unit, '{}.yaml'.format(command)))
    if configfile:
        configurations, order_list = read_configuration(
            configfile, environment)
    else:
        configfile = config.get_abspath(
            os.path.join('units', unit, 'start.yaml'))
        if configfile:
            configurations, order_list = read_configuration(
                configfile, environment)
            configurations, order_list = modify_order_list(
                configurations, order_list, command)
        else:
            raise RuntimeError(
                "Could not create a configuration for unit/command tuple {}!"
                .format(args.unitcommand))

    if args.print_only:
        print yaml.safe_dump_all([configurations, order_list])
    else:
        run_configuration(
            config, configurations, order_list, dc, args.unitcommand)


def _list_out(print_titles, title, list):
    if print_titles:
        print(title)
        print('=' * len(title))
    print '\n'.join(list)
    if print_titles:
        print('')


def main_list(config, args):
    if not (args.units or args.services):
        args.units = True

    print_titles = False
    if args.units and args.services:
        print_titles = True

    if args.units:
        _list_out(print_titles, 'Available units:', config.list_units())
    if args.services:
        _list_out(print_titles, 'Available services:', config.list_services())


def main(args):

    try:
        config = Configuration(args.configdir)

        if args.subparser == 'init':
            config.initialize()
        else:
            if not config.initialized:
                raise RuntimeError(
                    "Could not find an initialized configuration directory.  "
                    "Maybe you need to run the 'init' command"
                )
        if args.subparser == 'run':
            main_run(config, args)
        elif args.subparser == 'help':
            main_help(config, args)
        elif args.subparser == 'list':
            main_list(config, args)

    except:
        log.error("Failed to execute the recipe.", exc_info=1)


class DockerContainer(object):

    def __init__(
            self, dc, name, creation={}, startup={}, build={},
            global_config=Configuration(), unitname='unknown/unknown'):

        self.dc = dc
        self.unitname = unitname   # TODO: this has been added to the signature
        self.name = name
        self.creation = creation
        self.startup = startup
        self.build = build
        self.global_config = global_config
        self._update_start_config()
        self._update_creation_config()
        log.debug("Initialized docker container {}".format(name))

    def _buildpath(self):
        buildpath = self.build.get('path')
        if buildpath:
            return self.global_config.get_abspath(buildpath)
        else:
            return os.getcwd()

    def _path_substitutions(self, fro):
        """
        substitutes container-specific environment variables.

        The only possible environment variable is ${CONFIG_DIR} at the moment.
        It is substituted with the containers build path.  If the build path is
        not specified, our fall-back is the current directory.
        """
        config_dir = self._buildpath()

        nfro = fro.replace('${CONFIG_DIR}', config_dir)
        if nfro != fro:
            log.debug(
                'Replaced ${{CONFIG_DIR}} in {} with {}.'
                .format(fro, config_dir))
        return nfro

    def _update_start_config(self):
        if 'binds' in self.startup:
            binds = self.startup['binds']
            nbinds = {}
            for fro, to in binds.iteritems():
                nfro = self._path_substitutions(fro)
                nbinds[nfro] = to
                if not os.path.exists(nfro):
                    raise ValueError(
                        "The path {} to bind to, does not exist, maybe you "
                        "started in the wrong directory?".format(nfro))
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
        if name is None:
            return {}
        name_split = name.rsplit(':', 1)
        images = self.dc.images(name_split[0])
        if len(images) == 1:
            if len(name_split) == 2 and name not in images[0]['RepoTags']:
                return {}
            else:
                return images[0]
        else:  # len(images) == 0:
            return {}

    def get_container(self):
        containers = self.dc.containers(
            filters={'name': "^/{}$".format(self.name)}, all=True)
        if len(containers) == 1:
            return containers[0]
        else:  # len(containers) == 0:
            return {}

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
                    last_line = json.loads(line)
                    if 'error' in last_line:
                        raise RuntimeError(last_line['error'])
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

    def _substitute_runtime_args(self, args):
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
        self._substitute_runtime_args(run_args)

        if self.name == 'host':

            cwd = self._buildpath()
            ret = docker_meta.utils_spawn.spawnProcess(
                run_args,
                outhandler=lambda data: self._log_output(data, 'execute'),
                errhandler=lambda data: log.error(data.strip()),
                cwd=cwd,
                shell=shell)
            if ret != 0:
                raise RuntimeError(
                    "Execution of {} failed with error code {} (cwd={})"
                    .format(' '.join(run_args), ret, cwd))
            return ret
        else:
            self.manipulate_volumes(run_args, binds)

    def create(self):
        if (not self.creation) and (not self.build):
            raise RuntimeError(
                "No configuration to create the container given.")

        self.creation['name'] = self.name
        self.creation['image'] = self.build.get(
            'tag', self.creation.get('image'))
        if not self.creation['image']:
            raise RuntimeError(
                "Creation requires a build tag or an image id.")
        log.debug(
            "set creation fields for 'name' and 'image' to {name} and "
            "{image}".format(**(self.creation)))
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

        log.debug(
            'manipulate_volumes created a busybox container with id {}.'
            .format(info['Id']))

        self.dc.start(
            info,
            volumes_from=self.name,
            binds=binds)

        exit_code = self.dc.wait(info)

        stdout = self.dc.logs(info)

        info_line = (
            'Executing command {} on file system of container {}.  '
            'Output follows\n{}'
            .format(command, self.name, stdout))
        self._log_output(info_line, 'manipulate_volumes')

        if exit_code != 0:
            stderr = self.dc.logs(info, stdout=False, stderr=True, tail=3)

        self.dc.remove_container(info)

        if exit_code != 0:
            raise RuntimeError(
                "Manipulation of volume {} failed with exit code {}:\n{}"
                .format(command, exit_code, stderr))

        log.info(
            "Successfully executed command {} in container {}."
            .format(command, self.name))

    def backup(self, source, target_dir, target_name, overwrite=False):
        target_dir = self._path_substitutions(target_dir)
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
        restore_dir = self._path_substitutions(restore_dir)
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
        if not container:
            log.debug(
                "Trying to stop container {}, but it has not been created. "
                "(skipping)"
                .format(self.name))
            return
        if self.is_started():
            self.dc.stop(container, timeout)
            log.info("Successfully stopped container {}".format(self.name))
        else:
            log.debug(
                "Not stopping container {} as it was not running"
                .format(self.name))

    def remove_image(self, force=False, noprune=False):
        image = self.get_image()
        if image:
            self.dc.remove_image(image, force, noprune)
            log.info("Successfully removed the image {}".format(image))
        else:
            log.debug(
                "Trying to remove image {}. But it does not exist. (Skipping)"
                .format(image))

    def remove(self, v=True, timeout=10):
        self.stop(timeout)
        container = self.get_container()
        if container:
            if not v:
                inspect = self.dc.inspect_container(self.name)
                binds = set([
                    n.split(':')[1] for n in (
                        inspect['HostConfig']['Binds'] or [])])
                volumes_from = inspect['HostConfig']['VolumesFrom'] or []
                fvolumes = []
                for vf in volumes_from:
                    finspect = self.dc.inspect_container(vf)
                    fvolumes += finspect['Volumes'].keys()
                volumes = set(inspect['Volumes'].keys())
                if volumes.difference(binds.union(set(fvolumes))):
                    log.info(
                        "Not removing container {} as it has volumes attached "
                        "to it."
                        .format(self.name))
                    return

            self.dc.remove_container(container, v)
            log.info("Successfully removed container {}".format(self.name))
        else:
            log.debug(
                "Not removing container {} as it did not exist."
                .format(self.name))


def run_configuration(
        global_config, configurations, order_list, dc,
        unitcommand='unknown/unknown'):

    for item in order_list:

        name, orders = item.items()[0]
        c = configurations.get(name, {})
        if not c and name != 'host':
            raise ValueError(
                "Could not find a configuration for container {}".format(name))
        cmd = orders['command']

        container = DockerContainer(
            dc, name, global_config=global_config, unitname=unitcommand, **c)

        timeout = orders.pop('timeout', 10)
        wait_time = orders.pop('wait', 0)

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
        elif cmd == 'remove_image':
            force = orders.pop('force', False)
            noprune = orders.pop('noprune', False)
            container.remove_image(force, noprune)
        elif cmd == 'remove':
            v = orders.pop('v', False)
            container.remove(v, timeout)
        elif cmd == 'execute':
            shell = orders.pop('shell', False)
            binds = orders.pop('binds', {})
            container.execute(orders['run'], shell, binds)
        else:
            raise ValueError(
                "Invalid command {} for container {}".format(cmd, name))

        time.sleep(wait_time)


# vim:set ft=python sw=4 et spell spelllang=en:
