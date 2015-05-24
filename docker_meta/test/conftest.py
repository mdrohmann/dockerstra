# -*- coding: utf-8 -*-

import pytest
import urllib2

from docker_meta.container import get_docker_client


def internet_on():
    try:
        urllib2.urlopen('http://216.58.216.174', timeout=1)
        return True
    except urllib2.URLError:
        pass
    return False


def docker_on():
    try:
        cli = get_docker_client('http://172.17.42.1:4243')
        if cli.ping():
            return cli
    except:
        pass
    return None


def pytest_namespace():
    has_internet = internet_on()
    docker_client = docker_on()
    return {
        'needs_internet': pytest.mark.skipif(
            not has_internet, reason="test requires internet connection"),
        'needs_docker_client': pytest.mark.skipif(
            not docker_client,
            reason="test requires a connection to a docker daemon"),
        'docker_client': docker_client
    }

# vim:set ft=python sw=4 et spell spelllang=en:
