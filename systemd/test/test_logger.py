import logging
import sys

import pytest

from docker_meta import DockerContainer
from docker_meta.logger import (
    _get_logger_configuration, configure_logger, test_streams)


def test_log_split():
    configure_logger(test=True)
    log = logging.getLogger('docker_meta')
    log.warn('test')
    log.info('test_info')

    # log debug should be ignored
    log.debug('ignored')

    infos = test_streams['info'].getvalue().split('\n')
    errors = test_streams['errors'].getvalue().split('\n')

    assert len(infos) == 2
    assert len(errors) == 2
    assert infos[0].endswith('INFO: test_info')
    assert errors[0].endswith('WARNING: test_logger.py: test')


def test_log_configuration():
    config = _get_logger_configuration(debug=True)
    assert config['loggers']['docker_meta']['level'] == 'DEBUG'
    assert config['handlers']['info_stream']['stream'] == sys.stdout
    assert config['handlers']['error_stream']['stream'] == sys.stderr

    config = _get_logger_configuration(
        infofile='file.log', errorfile='file.err')
    assert config['handlers']['info_stream']['filename'] == 'file.log'
    assert config['handlers']['error_stream']['filename'] == 'file.err'


@pytest.mark.parametrize('v,expected', [
    (0, 1),
    (1, 4),
    (2, 6),
    (3, 44),
    ], ids=['verbose={}'.format(i) for i in range(4)])
def test_output_filter_pull(v, expected):
    configure_logger(test=True, verbosity=v)
    dc = DockerContainer(None, 'test')
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
    infos = test_streams['info'].getvalue().split('\n')
    assert len(infos) == expected
    if len(infos) > 1:
        assert infos[0].endswith('(bc) a: {}'.format(repr({u"0": 40})))


@pytest.mark.parametrize('v,expected', [
    (0, 1),
    (1, 3),
    (2, 3),
    (3, 3),
    ], ids=['verbose={}'.format(i) for i in range(4)])
def test_output_filter_build_image(v, expected):
    configure_logger(test=True, verbosity=v)
    dc = DockerContainer(None, 'test')
    dc._log_output('', 'build')
    dc._log_output('{"stream": "hello"}', 'build')
    dc._log_output('{"stream": "world"}', 'build')
    dc._log_output({"stream": "world"}, 'build')

    infos = test_streams['info'].getvalue().split('\n')
    assert len(infos) == expected
    if len(infos) > 1:
        assert infos[0].endswith('hello')
        assert infos[1].endswith('world')


@pytest.mark.parametrize('v,expected', [
    (0, 1),
    (1, 4),
    (2, 4),
    (3, 4),
    ], ids=['verbose={}'.format(i) for i in range(4)])
def test_output_filter_create_container(v, expected):
    configure_logger(test=True, verbosity=v)
    dc = DockerContainer(None, 'test')
    dc._log_output('', 'create_container')
    dc._log_output(
        {'Id': 'abc', 'Warnings': None}, 'create_container')
    dc._log_output(
        {'Id': 'def', 'Warnings': 'ohoh'}, 'create_container')

    infos = test_streams['info'].getvalue().split('\n')
    assert len(infos) == expected
    if len(infos) > 1:
        assert infos[0].endswith('Created image with Id abc')
        assert infos[1].endswith('Created image with Id def')
        assert infos[2].endswith('ohoh')

# vim:set ft=python sw=4 et spell spelllang=en:
