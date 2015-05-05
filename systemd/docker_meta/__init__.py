import json
import time
import os

import docker
import yaml

from .dist import Version


version = Version('docker_meta', 0, 2, 0, 'devel')


def read_configuration(configfile):
    with open(configfile, 'r') as fh:
        configs = yaml.load_all(fh)
        configs = list(configs)

    order_list = configs[1]
    configurations = configs[0]
    if len(configurations) == 1 and 'import' in configurations:
        parent_file = os.path.abspath(
            os.path.join(
                os.path.dirname(configfile), configurations['import']))
        configurations, _ = read_configuration(parent_file)

    return configurations, order_list


def run_configuration(configurations, order_list, dc):

    for item in order_list:

        name, orders = item.items()[0]
        c = configurations[name]
        cmd = orders['command']

        container = DockerContainer(dc, name, **c)

        if cmd == 'build':
            container.build_image()
        elif cmd == 'create':
            container.create()
        elif cmd == 'start':
            container.start()
        elif cmd == 'restore':
            restore_dir = os.path.abspath(orders.get('restore_dir', '.'))
            container.restore(restore_dir, orders['restore_name'])
        elif cmd == 'backup':
            backup_dir = os.path.abspath(orders.get('backup_dir', ','))
            container.backup(
                orders['source'], backup_dir, orders['backup_name'])
        else:
            raise ValueError(
                "Invalid command {} for container {}".format(cmd, name))

        wait_time = orders.get('wait', 0)
        time.sleep(wait_time)


class DockerContainer(object):

    def __init__(self, dc, name, creation={}, startup={}, build={}):
        self.dc = dc
        self.name = name
        self.creation = creation
        self.startup = startup
        self.build = build

    def is_started(self):
        res = self.dc.inspect_container(self.get_container())
        return res['State']['Running']

    def get_container(self):
        containers = self.dc.containers(filters={'name': self.name}, all=True)
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
        else:
            try:
                # Create the container ...
                self.create()
                # ... and then start it.
                self.dc.start(container=self.name, **self.startup)
            except Exception as e:
                raise RuntimeError(
                    "Container {} does not exist, and I do not know how to "
                    "create it:\n {}"
                    .format(self.name, e))

    def build_image(self):

        response = ''
        if self.build:
            # set the default to rm==True
            if 'rm' not in self.build:
                self.build['rm'] = True

            response = [line for line in self.dc.build(**self.build)]
        else:
            image = self.creation.get('image')
            tag = self.creation.get('tag', 'latest')
            if image:
                try:
                    for line in self.dc.pull(
                            repository=image, tag=tag, stream=True):
                        response = json.loads(line)
                        print(response.get('progressDetail'))
                except Exception as e:
                    raise RuntimeError(
                        "No build instructions for image {}:\n{}\n{}"
                        .format(image, e, repr(response)))
            else:
                raise RuntimeError("No image to pull or build given.")

        return '\n'.join(response)

    def create(self):
        if (not self.creation) and (not self.build):
            raise RuntimeError("No configuration given")

        self.creation['name'] = self.name
        try:
            self.creation['image'] = self.build.get(
                'tag', self.creation.get('image'))
        except KeyError:
            raise RuntimeError(
                "Creation requires a build tag or an image id.")
        if self.get_container():
            print(
                "Warning: The image {} seems to exist already (skipped)."
                .format(self.creation['image']))
            return None
        try:
            info = self.dc.create_container(**self.creation)
            print "Created container: {}".format(repr(info))
        except docker.errors.APIError as e:
            if 'No such image' in str(e):
                self.build_image()
                self.dc.create_container(**self.creation)
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

        if exit_code != 0:
            stderr = self.dc.logs(info, stdout=False, stderr=True, tail=3)
            raise RuntimeError(
                "Manipulation of volume {} failed with exit code {}:\n{}"
                .format(command, exit_code, stderr))
        return stdout

    def backup(self, source, target_dir, target_name):
        res = self.manipulate_volumes(
            command=[
                'tar', 'cvf', '/backup/{}.tar'.format(target_name), source],
            binds={target_dir: {'bind': '/backup', 'ro': False}})
        os.system('gzip {}.tar'.format(os.path.join(target_dir, target_name)))
        return res

    def restore(self, restore_dir, restore_name):

        archive = '{}.tar'.format(
            os.path.join(restore_dir, restore_name))
        gzipped_archive = '{}.gz'.format(archive)
        gzip = False
        if os.path.exists(gzipped_archive):
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
        self.dc.stop(container, timeout)

# vim:set ft=python sw=4 et spell spelllang=en:
