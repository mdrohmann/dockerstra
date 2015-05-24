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
        }),
    ('init', {
        'subparser': 'init',
        }),
    ('help --unit dev_server', {
        'subparser': 'help',
        'unit': 'dev_server'
        }),
    ],
    ids=['run', 'list', 'init', 'help'])
def test_parser(cmdline, expect):
    parser = create_parser()
    args = parser.parse_args(cmdline.split(' '))
    for k, v in expect.iteritems():
        assert hasattr(args, k)
        assert getattr(args, k) == v


@pytest.mark.parametrize('cmdline', [
    'help',
    'help --unit',
    'help --unit u --service s',
    ])
def test_parser_fail(cmdline):
    parser = create_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(cmdline.split(' '))


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

test_start1 = [
    {'host': {
        'command': 'unit',
        'unit': 'dockerstra/start',
        'args': ['test', 'unit/start' + ":variant", 'tempid']}}
]
test_start2 = [
    {'host': {
        'command': 'unit',
        'unit': 'dockerstra/start',
        'args': ['test', 'unit/start', 'tempid', 'tempid']}}
]

# ATTENTION: The unit/start tagged variants are inherited by the test
# variants!!!!

# QUESTION: Should I put dockerstra in a unit itself???  That would be crazy,
# but would allow me later to easily create tests in a unified way... I
# actually like it!!!, Then, I do not need try_always either, and all the
# testing functionality is out-sourced to the dockerstra container.  I should
# create a separate file for the dockerstra_test container....
test_collection = [
    # We should separate
    # between external and internal tests( internal are software library tests,
    # external are more like end-to-end tests, checking if a docker
    # container is started)
    {'host': {
        'command': 'unit',
        'unit': 'dockerstra/start',
        'args': ['collect_external', 'unit/test', 'tempid']}},   # once we need, once we don't...
    {'host': {
        'command': 'unit',
        'unit': 'dockerstra/start',
        'args': ['collect_internal', 'unit/test']}},
]
test_remove_container1 = [
    {'dockerstra_test': {
        'command': 'unit',
        'args': ['test', 'unit/cleanup', 'tempid']}}
]

test_remove_container2 = [
    {'dockerstra_test': {
        'command': 'unit',
        'args': ['test', 'unit/purge', 'tempid', 'tempid']}}
]
test_configurations1 = {
    'x1_without_build_testid': {},
    'x2_with_build_testid': {'build': {'tag': 'test'}},
}
test_configurations2 = {
    'x1_without_build_testid': {},
    'x2_with_build_testid': {'build': {'tag': 'test_testid'}},
}


@pytest.mark.current
@pytest.mark.parametrize('init,command,expected', [
    (
        dummy_modify_init_order_list,
        'stop', ([{
            'x2_with_build': {'command': 'stop', 'timeout': 0},
            }], None)
    ), (
        dummy_modify_init_order_list,
        'cleanup', ([
            {'x2_with_build': {'command': 'stop', 'timeout': 0}},
            {'x2_with_build': {'command': 'remove', 'v': False}},
            {'x1_without_build': {'command': 'remove', 'v': False}},
        ], None)
    ), (
        dummy_modify_init_order_list,
        'purge', ([
            {'x2_with_build': {'command': 'stop', 'timeout': 0}},
            {'x2_with_build': {'command': 'remove', 'v': True}},
            {'x1_without_build': {'command': 'remove', 'v': True}},
            {'x2_with_build': {'command': 'remove_image'}},
        ], None)
    ), (
        dummy_modify_init_order_list,
        'restart', ([
            {'x2_with_build':
                {'command': 'start', 'restart': True, 'timeout': 0}},
        ], None)
    ), (
        dummy_modify_init_order_list,
        'build', ([{'x2_with_build': {'command': 'build'}}], None)
    ), (
        dummy_modify_init_order_list,
        'create', ([
            {'x1_without_build': {'command': 'create'}},
            {'x2_with_build': {'command': 'create'}},
            ], None)
    ), (
        # TODO: 1. add unit command,
        # 2. add environment substitutions
        # 3. add test_collector unit
        # 4. add unit_name and test_file substitutions
        # 5. add try_always
        dummy_modify_init_order_list,
        'test', (
            test_start1 + test_collection + test_remove_container1,
            {})
    ), (
        dummy_modify_init_order_list,
        'test:full', (
            test_start2 + test_collection + test_remove_container2,
            {})
    ), (
        dummy_modify_init_order_list,
        'test:production', (
            test_collection, {})
    ), (
        dummy_modify_init_order_list,
        'backup', (
            {'x1_without_build': {
                'command': 'backup',
                'backup_dir': '{{BACKUPDIR}}/{{TIMESTAMP}}',
                'backup_name': 'x1_without_build'
            }},
            {'x2_with_build': {
                'command': 'backup',
                'backup_dir': '{{BACKUPDIR}}/{{TIMESTAMP}}',
                'backup_name': 'x2_with_build'
            }}, None)
    ), (
        dummy_modify_init_order_list,
        'restore', (
            {'x1_without_build': {
                'command': 'restore',
                'restore_dir': '{{BACKUPDIR}}/{{TIMESTAMP}}',
                'restore_name': 'x1_without_build'
            }},
            {'x2_with_build': {
                'command': 'restore',
                'restore_dir': '{{BACKUPDIR}}/{{TIMESTAMP}}',
                'restore_name': 'x2_with_build'
            }}, None)
    )
    ],
    ids=[
        'stop', 'cleanup', 'purge', 'restart', 'build', 'create',
        'test', 'testfull', 'testproduction', 'backup', 'restore',
    ])
def test_modify_order_list(init, command, expected):

    configurations = {
        'x1_without_build': {},
        'x2_with_build': {'build': {'tag': 'test'}},
    }

    new_configurations, new_order = modify_order_list(
        configurations, init, command)

    expected_order, expected_configurations = expected
    if expected_configurations:
        assert new_configurations == expected_configurations
    else:
        assert new_configurations == configurations

    assert new_order == expected_order


def test_list_units(test_init):
    c, etcdir = test_init

    some_units = set([
        'dev_servers',
        'nginx_server',
        'selenium',
        ])
    assert set(c.list_units(False)).intersection(some_units) == some_units


# - add_argument:
#     name: '--language'
#     short: '-l'
#     choices: ['python', 'node']
#     default: 'python'
#     help: 'language of the host container'
# - add_argument:
#     name: 'command'
#     choices: ['initialize', 'exec', 'host-exec', 'bash', 'daemon', 'single',
#     'upgrade']
#     default: 'initialize'
#     help: 'define what to do with the container'
# - add_argument:
#     name: 'args'
#     nargs: argparse.REMAINDER
def test_environment_argparser(test_init):
    """
    checks that the environment argparser is initialized from an environment
    """
    pass


def test_list_variants_complex(test_init):
    """
    checks that the variants are shown correctly for a combination of test and
    tagged variant definitions.
    """


@pytest.mark.current
def test_list_variants(test_init):
    c, etcdir = test_init

    testvariants = set(
        ['dev_servers/test:{}'.format(n)
         for n in ['full', 'start_stop', 'production']])

    assert c.list_variants('dev_servers/test') == testvariants


@pytest.mark.current
def test_list_unit_commands(test_init):
    c, etcdir = test_init

    # check that all of these are available
    dev_server_units = set([
        'dev_servers/start',
        'dev_servers/backup',
        'dev_servers/restore',
        'dev_servers/stop',
        'dev_servers/cleanup',
        'dev_servers/purge',
        'dev_servers/restart',
        'dev_servers/build',
        'dev_servers/create',
        'dev_servers/test',
        ])

    some_units = dev_server_units.union(set([
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
        ]))

    found_dev_server_units = [
        u for u in c.list_units() if u.startswith('dev_servers/')]
    assert set(found_dev_server_units) == dev_server_units
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
