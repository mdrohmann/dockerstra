# -*- coding: utf-8 -*-

import os
from argparse import Namespace
import pytest
from docker_meta.container import (
    main_list)
from docker_meta.configurations import (
    Configuration, create_parser, modify_order_list)
from docker_meta.logger import (
    configure_logger, last_info_line)


@pytest.mark.parametrize('cmdline,expect', [
    ('run -H 172.17.42.1:4243 --print-only unit/start', {
        'subparser': 'run', 'daemon': '172.17.42.1:4243',
        'print_only': True, 'unitcommand': 'unit/start'
        }),
    ('list --units', {
        'subparser': 'list',
        'units': True,
        })])
def test_parser(cmdline, expect):
    parser = create_parser()
    args = parser.parse_args(cmdline.split(' '))
    for k, v in expect.iteritems():
        assert hasattr(args, k)
        assert getattr(args, k) == v


def test_basedir(tmpdir, monkeypatch):
    basedirs = [
        (str(tmpdir.join('unwritable')), 'etc'),
        (str(tmpdir.join('valid')), 'etc'),
        ]

    monkeypatch.setattr(Configuration, 'valid_basedirs', basedirs)

    with pytest.raises(RuntimeError):
        Configuration()

    tmpdir.join('valid').ensure_dir()

    config1 = Configuration()

    assert config1.basedir == os.path.join(basedirs[1][0], 'etc')
    assert tmpdir.join('valid').join('etc').check(dir=1), (
        "configuration directory has not been created!")

    with pytest.raises(ValueError):
        Configuration(basedirs[0][0])

    config3 = Configuration(basedirs[1][0])
    assert config3.basedir == basedirs[1][0]

    toskipdir = tmpdir.join('toskip').ensure_dir()
    basedirs.insert(0, (str(toskipdir), 'etc'))

    config1.initialize()
    config4 = Configuration()
    assert config4.basedir == config1.basedir


@pytest.fixture
def test_init(tmpdir):
    configure_logger(test=True, verbosity=1, debug=1)

    etcdir = tmpdir.join('etc').ensure_dir()
    c = Configuration(str(etcdir))
    assert not c.initialized
    c.initialize()
    assert c.initialized

    assert last_info_line()[0].endswith(
        "Wrote initial data to config directory: {}".format(str(etcdir)))

    assert (etcdir.join("units").join("dev_servers").join("start.yaml")
            .check(file=1))
    assert (
        'BACKUP_DIR: {}/.docker_backup'.format(os.getenv('HOME'))
        in etcdir.join("environments").join("default.yaml").read())

    c2 = Configuration(str(etcdir))
    assert c2.initialized

    return c, etcdir


def test_get_abspath(test_init):
    c, etcdir = test_init

    assert (
        c.get_abspath('services/cgit/Dockerfile')
        == str(etcdir.join('services').join('cgit').join('Dockerfile')))

    assert c.get_abspath('nonexistent') is None


def test_get_environment(test_init):
    c, etcdir = test_init

    etcdir.join('environments').join('extra.yaml').write('''
test: 12
    ''')

    env = c.get_environment()
    assert set(env.keys()) == set(
        ['DOCKERSTRA_CONF', 'DOCKER_HOST', 'BACKUP_DIR', 'test'])


dummy_modify_init_order_list = [
    {'x1_without_build': {'command': 'build'}},
    {'x2_with_build': {'command': 'build'}},
    {'x1_without_build': {'command': 'create'}},
    {'x2_with_build': {'command': 'start'}},
    ]


@pytest.mark.parametrize('init,command,expected', [
    (
        dummy_modify_init_order_list,
        'stop', [{
            'x2_with_build': {'command': 'stop', 'timeout': 0},
            }]
    ), (
        dummy_modify_init_order_list,
        'cleanup', [
            {'x2_with_build': {'command': 'stop', 'timeout': 0}},
            {'x2_with_build': {'command': 'remove', 'v': False}},
            {'x1_without_build': {'command': 'remove', 'v': False}},
        ]
    ), (
        dummy_modify_init_order_list,
        'purge', [
            {'x2_with_build': {'command': 'stop', 'timeout': 0}},
            {'x2_with_build': {'command': 'remove', 'v': True}},
            {'x1_without_build': {'command': 'remove', 'v': True}},
            {'x2_with_build': {'command': 'remove_image'}},
        ]
    ), (
        dummy_modify_init_order_list,
        'restart', [
            {'x2_with_build':
                {'command': 'start', 'restart': True, 'timeout': 0}},
        ]
    ),

    ], ids=['stop', 'cleanup', 'purge', 'restart'])
def test_modify_order_list(init, command, expected):

    configurations = {
        'x1_without_build': {},
        'x2_with_build': {'build': {'tag': 'test'}},
    }
#        'x3': {},
#        'x4': {}}

    assert modify_order_list(configurations, init, command) == expected


def test_list_units(test_init):
    c, etcdir = test_init

    some_units = set([
        'dev_servers/start',
        'dev_servers/backup',
        'dev_servers/restore',
        'dev_servers/stop',
        'dev_servers/cleanup',
        'dev_servers/purge',
        'nginx_server/start',
        'nginx_server/stop',
        'nginx_server/cleanup',
        'nginx_server/purge',
        'selenium/start',
        'selenium/stop',
        'selenium/cleanup',
        'selenium/purge',
        'selenium/firefox',
        'selenium/chrome',
        ])
    assert set(c.list_units()).intersection(some_units) == some_units


@pytest.mark.parametrize(
    'args,expected,notexpected', [
        ({'units': True, 'services': False},
            ['dev_servers/start'],
            ['Available', 'apt-cacher-ng']),
        ({'units': False, 'services': False},
            ['dev_servers/start'],
            ['Available', 'apt-cacher-ng']),
        ({'units': False, 'services': True},
            ['apt-cacher-ng'],
            ['Available', 'dev_servers/start'],
         ),
        ({'units': True, 'services': True},
            [
                'Available units', 'Available services:',
                'dev_servers/start', 'apt-cacher-ng'],
            [],
         ),
    ], ids=[
        'units', 'units-default', 'services', 'both'])
def test_list_main(test_init, capsys, args, expected, notexpected):
    c, etcdir = test_init

    nargs = Namespace(**args)
    main_list(c, nargs)

    out, _ = capsys.readouterr()

    for exp in expected:
        assert exp in out

    for not_exp in notexpected:
        assert not_exp not in out


def test_list_services(test_init):
    c, etcdir = test_init

    some_services = set([
        'apt-cacher-ng',
        'cgit',
        'gitolite',
        'pypicloud'])
    assert set(c.list_services()).intersection(some_services) == some_services

# vim:set ft=python sw=4 et spell spelllang=en:
