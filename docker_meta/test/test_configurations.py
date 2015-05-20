# -*- coding: utf-8 -*-

import os
import pytest
from docker_meta.configurations import Configuration
from docker_meta.logger import (
    configure_logger, last_info_line)


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


def test_list_services(test_init):
    c, etcdir = test_init

    some_services = set([
        'apt-cacher-ng',
        'cgit',
        'gitolite',
        'pypicloud'])
    assert set(c.list_services()).intersection(some_services) == some_services

# vim:set ft=python sw=4 et spell spelllang=en:
