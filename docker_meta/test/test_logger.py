import logging
import sys
from StringIO import StringIO

import pytest

import docker_meta.container
from docker_meta.logger import (
    _get_logger_configuration, configure_logger,
    last_info_line, last_error_line, info_lines, error_lines,
    update_logger, reset_logger)


@pytest.fixture
def logger():
    configure_logger(test=True)
    return logging.getLogger(docker_meta.__name__)


def test_multiple_loggers():
    info1 = StringIO()
    info2 = StringIO()
    configure_logger(infofiles=[info1, info2])
    log = logging.getLogger(docker_meta.__name__)
    assert len(log.handlers) == 3
    log.info('test')
    assert len(info1.getvalue().strip().split('\n')) == 1
    assert len(info2.getvalue().strip().split('\n')) == 1


def test_update_logger(logger):
    assert len(logger.handlers) == 2
    logger.info('test')
    assert len(last_info_line(None)) == 1

    update_logger(infofiles=[StringIO(), StringIO()])
    assert len(logger.handlers) == 3

    reset_logger()
    logger.info('test2')
    assert len(last_info_line(None)) == 2


def test_configure_logger_global(logger):
    # reconfiguring with other options...
    configure_logger(test=True, verbosity=2)
    log2 = logging.getLogger(docker_meta.__name__)
    # ... changes all logging instances, because they are global
    assert log2 == logger


def test_configure_logger_debug():
    configure_logger(test=True, debug=True)
    log = logging.getLogger(docker_meta.__name__)
    assert log.level == logging.DEBUG


def test_logger_test_streams(logger):
    logger.info('test')
    assert len(info_lines()) > 0
    logger.error('test')
    assert len(error_lines()) > 0


def test_log_split(logger):
    log = logger
    log.warn('test')
    log.info('test_info')

    # log debug should be ignored
    log.debug('ignored')

    infos = last_info_line(None)
    errors = last_error_line(None)

    assert len(infos) == 1
    assert len(errors) == 1
    assert infos[0].endswith('INFO: test_info')
    assert errors[0].endswith('WARNING: test_logger.py: test')


def test_log_configuration():
    config = _get_logger_configuration(debug=True)
    assert config['loggers']['docker_meta']['level'] == 'DEBUG'
    assert config['handlers']['info_stream']['stream'] == sys.stdout
    assert config['handlers']['error_stream']['stream'] == sys.stderr

    config = _get_logger_configuration(
        infofiles='file.log', errorfiles='file.err')
    assert config['handlers']['info_stream']['filename'] == 'file.log'
    assert config['handlers']['error_stream']['filename'] == 'file.err'


@pytest.mark.parametrize('v,expected', [
    (0, 1),
    (1, 3),
    (2, 5),
    (3, 43),
    ], ids=['verbose={}'.format(i) for i in range(4)])
def test_output_filter_pull(v, expected):
    configure_logger(test=True, verbosity=v)
    dc = docker_meta.container.DockerContainer(None, 'test')
    dc._log_output('', 'pull')
    # ignore lines without status
    dc._log_output('{"id": "ab", "progressDetail": 21}', 'pull')
    for i in range(41):
        dc._log_output(
            '{{"status": "a", "progressDetail": {{"{0}": 40}}, "id": "bc"}}'
            .format(i),
            'pull')
    # different pull command
    dc._log_output('{"id": "cd", "status": "b", "progressDetail": 1}', 'pull')
    # invalid pull commands go through without an error
    dc._log_output({"Id": "cd", "Warnings": 1}, 'pull')
    dc._log_output('{"Id": "cd", "status": "invalid"}', 'pull')
    infos = last_info_line(None)
    assert len(infos) == expected
    if len(infos) > 1:
        assert infos[0].endswith('(bc) a: {}'.format(repr({u"0": 40})))


@pytest.mark.parametrize('v,expected', [
    (0, 1),
    (1, 2),
    (2, 2),
    (3, 2),
    ], ids=['verbose={}'.format(i) for i in range(4)])
def test_output_filter_build_image(v, expected):
    configure_logger(test=True, verbosity=v)
    dc = docker_meta.container.DockerContainer(None, 'test')
    dc._log_output('', 'build')
    dc._log_output('{"stream": "hello"}', 'build')
    dc._log_output('{"stream": "world"}', 'build')
    dc._log_output({"stream": "world"}, 'build')

    infos = last_info_line(None)
    assert len(infos) == expected
    if len(infos) > 1:
        assert infos[0].endswith('hello')
        assert infos[1].endswith('world')


@pytest.mark.parametrize('v,expected', [
    (0, 1),
    (1, 3),
    (2, 3),
    (3, 3),
    ], ids=['verbose={}'.format(i) for i in range(4)])
def test_output_filter_create_container(v, expected):
    configure_logger(test=True, verbosity=v)
    dc = docker_meta.container.DockerContainer(None, 'test')
    dc._log_output('', 'create_container')
    dc._log_output(
        {'Id': 'abc', 'Warnings': None}, 'create_container')
    dc._log_output(
        {'Id': 'def', 'Warnings': 'ohoh'}, 'create_container')

    infos = last_info_line(None)
    assert len(infos) == expected
    if len(infos) > 1:
        assert infos[0].endswith('Created image with Id abc')
        assert infos[1].endswith('Created image with Id def')
        assert infos[2].endswith('ohoh')

# vim:set ft=python sw=4 et spell spelllang=en:
