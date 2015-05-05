from io import BytesIO
import os
import time
import uuid

import docker
import pytest

from docker_meta import (
    DockerContainer, run_configuration, read_configuration)

test_dockerfile = '''
FROM busybox:latest

VOLUME ["/data"]

CMD /bin/sh -c 'echo hello world; sleep 10'
    '''


class TestWithDockerDaemon(object):
    cli = None
    uid = None
    testimage = None
    testcontainer = None

    @classmethod
    def setup_class(cls):
        try:
            cls.cli = docker.Client('172.17.42.1:4243')
            assert cls.cli.images()
        except:
            pytest.xfail(
                "Could not connect to a docker daemon.  "
                "Check your configuration!")

    def setup_method(self, _):
        uid = uuid.uuid4()
        self.testimage = 'test/helloworld{}'.format(uid)
        self.testcontainer = 'testcontainer{}'.format(uid)
        self.uid = uid

    def teardown_method(self, _):
        try:
            self.cli.remove_container(self.testcontainer, v=True, force=True)
        except:
            pass
        try:
            self.cli.remove_image(self.testimage, force=True)
        except:
            pass

    def test_container_non_existent(self):
        container = DockerContainer(self.cli, 'test', {})
        with pytest.raises(RuntimeError):
            container.start()

    def test_container_backup_restore(self, tmpdir):
        build_instructions = {
            'fileobj': BytesIO(test_dockerfile.encode('utf-8')),
            'tag': self.testimage,
            }
        container = DockerContainer(
            self.cli, self.testcontainer, {}, {}, build_instructions)
        container.create()

        container.manipulate_volumes(
            command=['touch', '/data/empty_file']
        )

        res = container.manipulate_volumes(
            command=['ls', '/data/'])

        assert res == "empty_file\n"

        container.backup('/data', str(tmpdir), 'backup')

        assert os.path.exists(str(tmpdir.join('backup.tar.gz')))

        container.manipulate_volumes(
            command=['rm', '/data/empty_file']
        )

        res = container.manipulate_volumes(
            command=['ls', '/data/'])

        assert res == ''

        container.restore(str(tmpdir), 'backup')

        res = container.manipulate_volumes(
            command=['ls', '/data/'])

        assert res == "empty_file\n"

    def test_container_creation(self):
        creation = {'image': self.testimage}
        container = DockerContainer(self.cli, self.testcontainer, creation)
        with pytest.raises(RuntimeError):
            container.start()

        assert str(container) == "No id yet"

        build_instructions = {
            'fileobj': BytesIO(test_dockerfile.encode('utf-8')),
            'rm': True,
            'tag': self.testimage,
            }

        container = DockerContainer(
            self.cli, self.testcontainer, {}, {}, build_instructions)
        container.start()

        container.start()
        time.sleep(0.01)
        assert container.is_started()

        assert str(container)

        # delete container and it should work again afterwards...

        container.stop(timeout=0)
        self.cli.remove_container(self.testcontainer, force=True)

        assert not container.get_container()
        container.start()
        assert container.get_container()

        container.start(restart=True, timeout=0)
        time.sleep(0.01)
        assert container.is_started()


def test_container_configuration_fail():

    # There should be more tests...
    with pytest.raises(ValueError):
        run_configuration({'x1': {}}, [{'x1': {'command': 'invalid'}}], None)


def test_container_configuration(monkeypatch):
    events = []
    monkeypatch.setattr(time, 'sleep', lambda x: events.append(x))
    monkeypatch.setattr(
        DockerContainer, 'start',
        lambda self, *args, **kwargs: events.append([self.name, self.startup]))
    monkeypatch.setattr(
        DockerContainer, 'build_image',
        lambda self, *args, **kwargs: events.append([self.name, self.build]))
    monkeypatch.setattr(
        DockerContainer, 'create',
        lambda self, *args, **kwargs: events.append([self.name, self.creation])
    )
    monkeypatch.setattr(
        DockerContainer, 'backup',
        lambda self, *args, **kwargs: events.append([self.name] + list(args))
    )
    monkeypatch.setattr(
        DockerContainer, 'restore',
        lambda self, *args, **kwargs: events.append([self.name] + list(args))
    )

    run_configuration(
        {
            'x1': {'build': 'built'},
            'x2': {'creation': 'created'},
            'x3': {'startup': 'started'},
        },
        [
            {'x3': {
                'command': 'start',
                'wait': 12,
            }},
            {'x2': {
                'command': 'create'
            }},
            {'x1': {
                'command': 'build'
            }},
            {'x1': {
                'command': 'backup',
                'backup_dir': '.',
                'backup_name': 'testbackup',
                'source': '/volume'
            }},
            {'x1': {
                'command': 'restore',
                'restore_dir': '.',
                'restore_name': 'testbackup',
            }},
        ],
        None)

    assert events == [
        ['x3', 'started'], 12, ['x2', 'created'], 0, ['x1', 'built'], 0,
        ['x1', '/volume', os.getcwd(), 'testbackup'], 0,
        ['x1', os.getcwd(), 'testbackup'], 0]


def test_read_configuration(tmpdir):
    testyaml = tmpdir.join('test.yaml')
    testyaml.write("""
x1: abc
---
-
    x1:
        command: start
""")
    configurations, order_list = read_configuration(str(testyaml))
    expect = {'x1': 'abc'}
    assert configurations == expect
    assert order_list == [{'x1': {'command': 'start'}}]

    testyaml2 = tmpdir.join('test2.yaml')
    testyaml2.write("""
import: test.yaml
---
-
    x1:
       command: backup
""")
    configurations, order_list = read_configuration(str(testyaml2))
    assert configurations == expect
    assert order_list == [{'x1': {'command': 'backup'}}]

# vim:set ft=python sw=4 et spell spelllang=en:
