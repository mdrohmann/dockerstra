import logging
import os
import re
import time
import uuid
from argparse import Namespace
from io import BytesIO

import pytest
import yaml

import docker_meta
from docker_meta.configurations import (Configuration)
from docker_meta.container import (
    DockerContainer, run_configuration, main_run, main_help, main)
from docker_meta.logger import (
    configure_logger, last_info_line, last_error_line)


test_dockerfile = '''
FROM busybox:latest

VOLUME ["/data"]

CMD /bin/sh -c 'echo hello world; sleep 10'
    '''


configure_logger(test=True, verbosity=1)
log = logging.getLogger(docker_meta.__name__)


def test_main_help(tmpdir, capsys):
    doc = '''
Test
====
'''
    dir1 = tmpdir.join('units').join('test').ensure_dir()
    dir1.join('readme.rst').write(doc)
    dir2 = tmpdir.join('services').join('test').ensure_dir()
    dir2.join('readme.rst').write(doc)
    config = Configuration(str(tmpdir))
    args = Namespace(unit='test', service='test')
    main_help(config, args)
    out, _ = capsys.readouterr()
    assert out == "{}\n{}\n".format(doc, doc)
    args = Namespace(unit='nonexistent', service=None)
    main_help(config, args)
    assert 'Could not find a README file in ' in last_error_line()[0]


@pytest.mark.parametrize('unitcommand,env,error', [
    ('dev_servers/start', True, None),
    ('dev_servers/restart', False, None),
    ('invalid/start', False, RuntimeError),
])
def test_main_run(tmpdir, monkeypatch, unitcommand, env, error, capsys):
    config = Configuration(str(tmpdir))
    config.initialize()
    events = []
    tyaml = tmpdir.join('env2').join('test.yaml').ensure(file=1)
    tyaml.write("""
TEST: 1
""")
    docker_meta.configurations = reload(docker_meta.configurations)
    monkeypatch.setattr(
        docker_meta.container, 'run_configuration',
        lambda *args: events.append(list(args)))
    monkeypatch.setattr(
        docker_meta.container, 'get_docker_client', lambda _: None)

    if env:
        environment = str(tyaml)
    else:
        environment = {}

    for po, ps in [(False, False), (False, True), (True, False)]:
        args = Namespace(
            daemon=None,
            environment=environment,
            unitcommand=unitcommand,
            print_only=po,
            print_substitutions=ps)

        if error:
            with pytest.raises(error):
                main_run(config, args)
            return

        main_run(config, args)

        if po or ps:
            out, _ = capsys.readouterr()
            outlist = list(yaml.load_all(out))
        else:
            outlist = events.pop()[1:3]

        assert 'git_repos' in outlist[0]
        assert outlist[1][0].keys()[0] in ['nginx', 'git_repos', 'cgit']


@pytest.fixture
def test_main_init(tmpdir, monkeypatch):

    args_init = Namespace(
        configdir=str(tmpdir), subparser='init', environment=None)
    main(args_init)

    config = Configuration(str(tmpdir))
    assert config.initialized
    return tmpdir


@pytest.mark.parametrize('subcommand', ['run', 'list', 'help'])
def test_main_other(test_main_init, monkeypatch, subcommand):
    tmpdir = test_main_init
    events = []
    monkeypatch.setattr(
        docker_meta.container, 'main_help',
        lambda *args, **kwargs: events.append('help'))
    monkeypatch.setattr(
        docker_meta.container, 'main_run',
        lambda *args, **kwargs: events.append('run'))
    monkeypatch.setattr(
        docker_meta.container, 'main_list',
        lambda *args, **kwargs: events.append('list'))

    args = Namespace(
        configdir=str(tmpdir), subparser=subcommand)
    main(args)
    assert events.pop() == subcommand


def test_main_fail(tmpdir):
    args = Namespace(
        configdir=str(tmpdir), subparser='run')
    main(args)

    assert last_error_line()[0].endswith(
        "Maybe you need to run the 'init' command")


@pytest.needs_docker_client
class TestWithDockerDaemon(object):
    cli = None
    uid = None
    testimage = None
    testcontainer = None
    testcontainer2 = None

    @classmethod
    def setup_class(cls):
        try:
            cls.cli = pytest.docker_client
            assert cls.cli.images()
        except:
            pytest.xfail(
                "Could not connect to a docker daemon.  "
                "Check your configuration!")

    def setup_method(self, _):
        uid = uuid.uuid4()
        self.testimage = 'test/helloworld{}'.format(uid)
        self.testcontainer = 'testcontainer{}'.format(uid)
        self.testcontainer2 = 'testcontainer2{}'.format(uid)
        self.uid = uid

    def teardown_method(self, _):
        try:
            self.cli.remove_container(self.testcontainer, v=True, force=True)
        except:
            pass
        try:
            self.cli.remove_container(self.testcontainer2, v=True, force=True)
        except:
            pass
        try:
            self.cli.remove_image(self.testimage, force=True)
        except:
            pass

    def build_instructions(self):
        return {
            'fileobj': BytesIO(test_dockerfile.encode('utf-8')),
            'tag': self.testimage,
            }

    def test_container_non_existent(self):
        container = DockerContainer(self.cli, 'test', {})
        with pytest.raises(RuntimeError):
            container.start()

    @pytest.mark.slowtest
    def test_container_backup_fail(self, tmpdir):
        container = DockerContainer(
            self.cli, self.testcontainer,
            creation={'image': 'busybox:latest', 'name': self.testcontainer})
        container.create()
        with pytest.raises(RuntimeError) as e:
            container.backup(None, str(tmpdir), 'backup')
        assert 'No volumes to backup' in str(e.value)

    @pytest.mark.slowtest
    def test_container_backup_restore(self, tmpdir):
        """
        This test also tests the manipulate_volumes() function extensively!
        """
        configure_logger(test=True, verbosity=1, debug=1)
        container = DockerContainer(
            self.cli, self.testcontainer, {}, {}, self.build_instructions())
        container.create()

        def _get_busybox_id():
            pattern = re.compile(
                'busybox container with id (?P<id>[A-Ha-h0-9]*)')
            res = pattern.findall('\n'.join(last_info_line(10)))
            return res[-1]

        with pytest.raises(RuntimeError) as e:
            container.manipulate_volumes(command=['false'])
        assert 'failed with exit code' in str(e.value)

        # check that container is removed after failed run
        assert not self.cli.containers(
            quiet=True, all=True, filters={'id': _get_busybox_id()})

        container.manipulate_volumes(
            command=['touch', '/data/empty_file']
        )
        # check that container is removed after successful run
        assert not self.cli.containers(
            quiet=True, all=True, filters={'id': _get_busybox_id()})

        container.manipulate_volumes(
            command=['ls', '/data/'])

        assert last_info_line(2)[0] == "empty_file"

        container.backup('/data', str(tmpdir), 'backup')

        assert os.path.exists(str(tmpdir.join('backup.tar.gz')))

        container.backup(None, str(tmpdir), 'backup2')

        backup2path = str(tmpdir.join('backup2.tar.gz'))
        assert os.path.exists(backup2path)
        os.system('gunzip {}'.format(backup2path))

        container.manipulate_volumes(
            command=['rm', '/data/empty_file']
        )

        container.manipulate_volumes(
            command=['ls', '/data/'])

        assert last_info_line(2)[0].endswith("Output follows")

        for b, e in [('backup', '.gz'), ('backup2', '')]:
            container.restore(str(tmpdir), b)

            assert os.path.exists(str(tmpdir.join('{}.tar{}'.format(b, e))))

            container.manipulate_volumes(
                command=['ls', '/data/'])

            assert last_info_line(2)[0] == "empty_file"

    @pytest.mark.parametrize(
        'tarname',
        ['backup.tar', 'backup.tar.gz'])
    def test_backup_dont_overwrite(self, tmpdir, tarname):
        tmpdir.join(tarname).write('')
        configure_logger(test=True, verbosity=0)
        container = DockerContainer(self.cli, self.testcontainer)
        with pytest.raises(RuntimeError) as e:
            container.backup('/', str(tmpdir), 'backup')
            assert e.message.startswith('Backup failed')

    @pytest.mark.slowtest
    def test_container_get_image(self):
        configure_logger(test=True, verbosity=1, debug=1)
        container = DockerContainer(
            self.cli, self.testcontainer, {}, {}, self.build_instructions())
        container.build_image()

        container.build_image()
        assert 'already exists. (skipped)' in last_info_line()[0]

        assert container.get_image(self.testimage)
        assert container.get_image('{}:latest'.format(self.testimage))
        assert container.get_image()
        assert not container.get_image('{}:othertag'.format(self.testimage))
        assert not container.get_image('non-existent')

    @pytest.mark.slowtest
    @pytest.needs_internet
    def test_pull_remove(self):
        container = DockerContainer(
            self.cli, self.testcontainer, {'image': 'hello-world'})

        image_exists = container.get_image()

        def _remove_image(container):
            container.remove_image()
            assert not container.get_image()
            # Do it twice to show, that second time returns without error
            container.remove_image()
            assert not container.get_image()

        if image_exists:
            _remove_image(container)

        container.build_image()

        assert container.get_image()

        if not image_exists:
            _remove_image(container)

    @pytest.mark.slowtest
    def test_container_creation_fail(self):
        configure_logger(test=True, verbosity=1, debug=1)
        container = DockerContainer(self.cli, self.testcontainer, {})
        with pytest.raises(RuntimeError) as e:
            container.build_image()
        assert 'No image to pull or build given.' in str(e.value)
        container.stop()
        assert 'Trying to stop container' in last_info_line()[0]

        container.remove()
        assert 'it did not exist.' in last_info_line()[0]

        container = DockerContainer(
            self.cli, self.testcontainer, {'name': self.testcontainer})
        with pytest.raises(RuntimeError) as e:
            container.create()
        assert 'Creation requires a build tag or an image id' in str(e.value)

    @pytest.mark.slowtest
    @pytest.mark.parametrize(
        'with_volumes_from,command,expect_failure',
        [(False, ['echo', 'hello world'], False),
         (False, ['false'], True),
         (True, ['echo', 'hello world'], False)],
        ids=['without_volumes', 'without_volumes_fail', 'with_volumes'])
    def test_container_creation_and_start(
            self, tmpdir, with_volumes_from, command, expect_failure):

        configure_logger(test=True, verbosity=1, debug=1)
        creation = {'image': self.testimage}
        container = DockerContainer(self.cli, self.testcontainer, creation)
        with pytest.raises(RuntimeError) as e:
            container.start()

        assert 'No build instructions for image' in str(e.value)

        assert str(container) == "No id yet"

        build_instructions = {
            'fileobj': BytesIO(test_dockerfile.encode('utf-8')),
            'rm': True,
            'tag': self.testimage,
            }

        datatemps = None
        if with_volumes_from:
            startup = {
                'binds': {str(tmpdir): {'bind': '/data', 'ro': False}},
                'volumes_from': self.testcontainer2,
            }
            datatemps = DockerContainer(
                self.cli, self.testcontainer2,
                {'image': 'busybox', 'volumes': ['/data2']})
            datatemps.create()
        else:
            startup = {}

        container = DockerContainer(
            self.cli, self.testcontainer,
            {'command': command}, startup, build_instructions)

        if expect_failure:
            with pytest.raises(RuntimeError) as e:
                container.start(attach=True)
            assert 'stopped with exit code' in str(e.value)
        else:
            container.start(attach=True)
            assert 'hello world' in last_info_line()[0]

        # Do it twice, to see that there are no errors the second time.
        container.start()

        # Also try to create it, and assert the debug message
        container.create()
        assert 'seems to exist already (skipped)' in last_info_line()[0]

        time.sleep(0.01)
        assert container.is_started()

        assert str(container)

        # delete container and it should work again afterwards...
        container.stop(timeout=0)

        # container has attached volume, that needs to be removed...
        container.remove(v=False)
        if with_volumes_from:
            assert not container.get_container()
            datatemps.remove(v=True)

            # cannot start again, because the volumes_from container is gone.
            with pytest.raises(RuntimeError):
                container.start()
        else:

            # removal is skipped with v==False
            assert container.get_container()

            container.remove(v=True)
            assert not container.get_container()

            container.start()

            assert container.get_container()

            # make sure, that containers with subset of the name are not found
            sub_name_container = DockerContainer(
                self.cli, self.testcontainer[2:-2])
            assert not sub_name_container.get_container()

            container.start(restart=True, timeout=0)
            time.sleep(0.01)
            assert container.is_started()


def test_container_configuration_fail():

    with pytest.raises(ValueError) as e:
        run_configuration(
            None, {'x1': {'build': 1}}, [{'x1': {'command': 'invalid'}}],
            '.', None)
        assert e.message.startswith('Invalid command invalid')

    with pytest.raises(ValueError) as e:
        run_configuration(
            None, {}, [{'x1': {'command': 'execute'}}], '.', None)
        assert e.message.startswith('Could not find a configuration for')

default_events = [
    ('start', ['x3', False, False, 10]), 12,
    ('create', ['x2']), 0,
    ('build_image', ['x1']), 0,
    ('backup', ['x1', '/volume', os.getcwd(), 'testbackup', False]), 0,
    ('restore', ['x1', os.getcwd(), 'testbackup']), 0,
    ('stop', ['x1', 3]), 0,
    ('remove', ['x1', False, 10]), 0,
    ('backup', ['x2', None, os.getcwd(), 'backup', False]), 0,
    ('restore', ['x2', os.getcwd(), 'backup']), 0,
    ('execute', ['x2', ['rm', '/var/cache'], False, {}]), 0,
    ('execute', ['host', ['echo', 'hallo'], True, {}]), 0,
    ('remove_image', ['x1', False, False]), 0,
    ]


@pytest.mark.parametrize(
    'expected',
    [(default_events),
     ],
    ids=['default'])
def test_container_configuration(monkeypatch, expected):
    events = []
    monkeypatch.setattr(time, 'sleep', lambda x: events.append(x))

    def tuple_command_args(command):
        monkeypatch.setattr(
            DockerContainer, command,
            lambda self, *args, **kwargs: events.append(
                (command, [self.name] + list(args) + kwargs.values()))
        )

    for c in [
            'start', 'create', 'build_image', 'stop', 'remove',
            'backup', 'restore', 'execute', 'remove_image']:
        tuple_command_args(c)

    run_configuration(
        None,
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
            {'x1': {
                'command': 'stop',
                'timeout': 3,
            }},
            {'x1': {
                'command': 'remove',
                'v': False,
            }},
            {'x2': {
                'command': 'backup',
            }},
            {'x2': {
                'command': 'restore',
            }},
            {'x2': {
                'command': 'execute',
                'run': ['rm', '/var/cache'],
            }},
            {'host': {
                'command': 'execute',
                'run': ['echo', 'hallo'],
                'shell': True,
            }},
            {'x1': {
                'command': 'remove_image',
            }},
        ],
        '.',
        None)

    assert events == expected


def test_execute_on_host():
    dc = DockerContainer(None, 'host')
    configure_logger(test=True, verbosity=1)
    with pytest.raises(RuntimeError) as e:
        res = dc.execute(['false'], shell=True)
        assert res > 0
        e.message.endswith('error code {}'.format(res))

    res = dc.execute(
        ['echo -n "hallo "; echo -n foo 1>&2; echo -n welt; echo -n bar 1>&2'],
        shell=True)
    assert res == 0
    assert last_info_line()[0].endswith('hallo welt')
    assert last_error_line()[0].endswith('foobar')

    res = dc.execute(
        ['echo "hallo "; echo foo 1>&2; sleep 0.01;'
         'echo welt; echo bar 1>&2'],
        shell=True)
    assert res == 0
    assert last_info_line()[0].endswith(': welt')
    assert last_error_line()[0].endswith(': bar')


def test_execute_not_on_host(monkeypatch):
    events = []
    monkeypatch.setattr(
        DockerContainer, 'manipulate_volumes',
        lambda *args, **kwargs: events.append(list(args)))

    dc = DockerContainer(None, 'test')
    dc.execute(['testcommand'])

    assert events[0][1] == ['testcommand']


@pytest.mark.parametrize(
    'container_handle, expected_name',
    [
        ('(image://testimage)', 'testimage'),
        ('(testcontainer)', 'testcontainer'),
        ('', 'test'),
    ], ids=['inspect_image', 'inspect_container', 'inspect_default'])
def test_substitute_run_args(container_handle, expected_name):

    class MockDocker(object):

        def _testdict(self, name):
            return {
                'Name': name,
                'NetworkSettings': {
                    'IPAddress': '172.17.42.1',
                    'Ports': {
                        '80': '8080',
                        '443': '4433',
                    }
                }
            }

        def inspect_image(self, image):
            return self._testdict(image)

        def inspect_container(self, container):
            return self._testdict(container)

    mock_dc = MockDocker()
    dc = DockerContainer(mock_dc, 'test')

    res = dc._substitute_runtime_args([
        "[[ inspect['Name'] ]]" + container_handle,
        "[[inspect['NetworkSettings']['IPAddress'] ]]",
        "[[inspect['NetworkSettings']['Ports'].keys() ]]"
    ])

    assert len(res) == 4
    assert res[0] == expected_name
    assert res[1] == '172.17.42.1'
    assert set(res[2:]) == set(['80', '443'])


@pytest.mark.parametrize('var',
    ['CONFIG_DIR', 'PWD'])
def test_startup_manipulation(tmpdir, var):
    """
    checks that CONFIG_DIR and PWD are replaced correctly for the binds keyword
    """
    with tmpdir.as_cwd():
        os.mkdir(str(tmpdir.join('path')))
        bind_path_host = '${{{}}}/path'.format(var)
        bind_container = {'binds': 'path', 'ro': True}
        startup = {
            'other_key': 'other_value',
            'binds': {bind_path_host: bind_container},
        }
        build = {'path': str(tmpdir)}
        dc = DockerContainer(None, 'test', startup=startup, build=build)
        new_key_expected = str(tmpdir.join('path'))
        assert dc.startup['binds'].keys() == [new_key_expected]
        assert dc.startup['binds'][new_key_expected] == bind_container
        assert 'other_key' in dc.startup
        os.rmdir(str(tmpdir.join('path')))

    # It fails, if the bind directory does not exist...
    with pytest.raises(ValueError):
        dc = DockerContainer(None, 'test', startup=startup, build=build)


def test_creation_manipulation():
    port_bindings = {22: 2222, 44: 4444}
    startup = {'port_bindings': port_bindings}
    ports = [22, 44]

    dc = DockerContainer(None, 'test', startup=startup)
    assert set(dc.creation['ports']) == set(ports)


def test_statistics():
    """
    checks that the runtime statistics (junits) are collected correctly.
    """


def test_unit():
    """
    checks that the unit command works, executing a unit and collecting
    information about it (logs / errors / statistics)
    """

# vim:set ft=python sw=4 et spell spelllang=en:
