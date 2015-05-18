import re

import pytest

from docker_meta import (nginx_gen, DockerContainer)


@pytest.mark.xfail()
@pytest.fixture()
def test_update_configuration(monkeypatch, tmpdir):
    confdir = str(tmpdir)
    containers = ['test.main:test']

    def mocked_run_args(args):
        return ['1.1.1.1', ['80/tcp']]

    monkeypatch.setattr(
        DockerContainer, '_substitute_runtime_args', mocked_run_args)

    nginx_gen.update_configuration(confdir, containers)

    conffile = tmpdir.join('vhost.conf.d').join('test.main.conf')

    assert conffile.check(file=True),  "Configuration file missing"
    contents = conffile.read()
    assert re.search(
        r'upstream test.main {[^}]*server 1.1.1.1:80[^}]*}', contents
    ), "Could not find the upstream section"

    assert re.search(
        r'server_name test.main;[^}]*location / {[^}]'
        '*proxy_pass http://test.main;', contents
    ), "Could not find the server section"

    return tmpdir, containers


def test_remove_configuration(test_update_configuration):
    tmpdir, containers = test_update_configuration

    conffile = tmpdir.join('vhost.conf.d').join('test.main.conf')
    assert conffile.check(file=True)

    nginx_gen.update_configuration(conffile, containers, remove=True)
    assert not conffile.check(file=True), (
        "configuration file has NOT been removed")

# vim:set ft=python sw=4 et spell spelllang=en:
