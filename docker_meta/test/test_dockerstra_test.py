# -*- coding: utf-8 -*-

import pytest
from docker_meta.test_runner import (
    SuiteFactory, Suite, SingleCase, SetupTeardownCase, DaemonCase)
from docker_meta.container import DockerContainer
from docker_meta.configurations import Configuration
from docker_meta.logger import configure_logger


configure_logger(verbosity=0, test=1)


class TestRunning(object):
    """
    all tests in here are based on a dummy configuration of Suites with test
    cases.
    """

    setup_case = SetupTeardownCase(
        DockerContainer(None, 'container1'),
        'start', {})

    daemon_case = DaemonCase('daemon_container', 'port_open', {
        'url': 'localhost:1234',
        'status': 200,
        'match': 'happy to talk to you'
        })

    junit_case = SingleCase('container1', 'default_test', {
        'unitcommand': 'unit/start',
        'args': ['test', 'default'],
        'gather_files': ['junit-*.xml', 'coverage_html/*'],
        })

    single_case = SingleCase('container1', 'check_python_version', {
        'args': ['single', 'python', '-mcertifi'],
        'match': 'Python 2\.7\.[1-9]*',
        })

    all_cases = [
        setup_case,
        daemon_case,
        junit_case,
        single_case,
    ]

    suite = Suite('dummy', all_cases)

    def test_run_suite(self):
        self.suite.run_all()


class TestConfiguration(object):
    """
    all tests in here, are based on a dummy scenario.  I will try not to use
    the docker.Client, but instead monkeypatch it...
    """

    @staticmethod
    def _get_container_keys(tempid):
        keys = ['container1', 'daemon_container']
        if tempid:
            return ('{}_{}'.format(n, tempid) for n in keys)
        else:
            return keys

    @classmethod
    def get_order_list(cls, tempid):
        k1, k2 = cls._get_container_keys(tempid)
        order_list = [{
            k1: {
                'command': 'create'}
            }, {
            k1: {
                'command': 'start'}
            }, {
            k2: {
                'command': 'start'}
            }, {
            k1: {
                'command': 'stop'}
            }
        ]
        return order_list

    def get_purge_orders(cls, tempid):
        k1, k2 = cls._get_container_keys(tempid)
        order_list = [{
            k1: {
                'command': 'stop'}}, {
            k1: {
                'command': 'remove'}}, {
            k1: {
                'command': 'remove_image'}}, {
            k2: {
                'command': 'stop'}}, {
            k2: {
                'command': 'remove'}},
            ]
        return order_list

    @classmethod
    def get_configurations(cls, tempid, tag_tempid=False):
        k1, k2 = cls._get_container_keys(tempid)
        configurations = {
            k1: {
                'build': {
                    'tag': 'some_tag_{}'.format(tag_tempid and tempid or ''),
                },
                'jobs': {
                    'default_test': {
                        'args': ['unit/start', 'test', 'default'],
                        'gather_files': ['junit-*.xml', 'coverage_html/*'],
                    },
                    'check_python_version': {
                        'args':
                            ['unit/start', 'single', 'python', '--version'],
                        'match': 'Python 2\.7\.[1-9]*'
                    },
                    'check_for_certifi': {
                        'args': ['unit/start', 'single', 'python' '-mcertifi'],
                        'exit_code': 0,
                    },
                },
            },
            k2: {
                'daemon': {
                    'port_open': {
                        'type': 'GET',
                        'url':
                            '[[.NetworkSettings.IPAddress]](daemon_container)',
                        'status': 200,
                        'match': 'happy to talk to you',
                    },
                    'dns_resolution': {
                        'type': 'GET',
                        'url': 'http://daemon_container.local',
                        'status': 200,
                    },
                    'ssl_request': {
                        'type': 'GET',
                        'url': 'https://daemon_container.local',
                        'status': 304,
                        'error_match': 'self-signed certificate',
                    },
                },
                'jobs': {
                    'e2e_test': {
                        'args': ['unit/start:e2e'],
                        'type': 'junit',
                        'gather_files': ['junit-*.xml'],
                        },
                },
            },
        }
        return configurations

    @classmethod
    def monkey_read_configuration(cls, config):
        tempid = config.environment.get('tempid', None)
        return (
            f(tempid) for f in [cls.get_configurations, cls.get_order_list])

    @pytest.fixture()
    def dummy_config(self, tmpdir, monkeypatch):
        monkeypatch.setattr(
            Configuration, 'read_unit_configuration',
            lambda cinst, *args: self.monkey_read_configuration(cinst))

        config = Configuration(str(tmpdir))
        return config

    @pytest.fixture()
    def suite_factory(self, dummy_config):
        suite_factory = SuiteFactory('unit/test', dummy_config, None)
        return suite_factory

    def test_tempid(self, suite_factory):
        tempid = suite_factory.tempid()
        assert len(tempid) == 10
        assert suite_factory.tempid(True) == 'unit/test_{}'.format(tempid)

    def test_environment_injection(self, suite_factory, dummy_config):
        """
        makes sure, that the tempid is injected in the environment of the
        called units...
        """
        configurations_pre = list(dummy_config.read_unit_configuration())[0]
        tempid_container = 'container1_{}'.format(suite_factory.tempid())
        assert 'container1' in configurations_pre
        assert tempid_container not in configurations_pre

        suite_factory.inject_tempid()
        configurations_pre = list(dummy_config.read_unit_configuration())[0]
        assert 'container1' not in configurations_pre
        assert tempid_container in configurations_pre

    def test_collect_cases(self, suite_factory, monkeypatch):
        tempid = suite_factory.tempid()
        monkeypatch.setattr(
            Configuration, 'modify_order_list',
            lambda *args: (
                self.get_configurations(tempid, False),
                self.get_purge_orders(tempid)))

        suite_factory.collect_cases()
        suites = suite_factory.suites
        assert len(suites) == 5

    @pytest.mark.parametrize(
        'use_tempid, tag_tempid, num_cases', [
            (True, True, 5),
            (True, False, 4),
            (False, True, 0),
            ], ids=['with_tempids', 'build_without_tempid', 'no_tempids'])
    def test_collect_teardown(
            self, suite_factory, dummy_config, monkeypatch,
            use_tempid, tag_tempid, num_cases):

        if use_tempid:
            tempid = suite_factory.tempid()
        else:
            tempid = None
        monkeypatch.setattr(
            Configuration, 'modify_order_list',
            lambda *args: (
                self.get_configurations(tempid, tag_tempid),
                self.get_purge_orders(tempid)))
        configurations, order_list = dummy_config.read_unit_configuration(
            'unit/start')
        suite_factory.collect_teardown(configurations, order_list)

        suites = suite_factory.suites
        assert len(suites) == 1
        cases = suites[0].cases
        assert len(cases) == num_cases
        for case in cases:
            assert type(case) == SetupTeardownCase

    def test_collect_setup(self, suite_factory, dummy_config):
        configurations, order_list = dummy_config.read_unit_configuration(
            'unit/start')
        suite_factory.collect_setup(configurations, order_list)

        suites = suite_factory.suites
        assert len(suites) == 1
        cases = suites[0].cases
        assert len(cases) == 3
        for case in cases:
            assert type(case) == SetupTeardownCase
            case_config = case.as_dict()
            if case_config['cmd'] == 'start':
                assert not case_config['startup']['tty']
                assert not case_config['startup']['stdin_open']
                assert case_config['orders']['attach']

    @pytest.mark.parametrize(
        'f,num_suites,num_cases,cls,container,names', [
            (SuiteFactory.collect_single_jobs, 2, 3,
                SingleCase,
                'container1', [
                    'default_test',
                    'check_python_version',
                    'check_for_certifi']),
            (SuiteFactory.collect_daemon_requests, 1, 3,
                DaemonCase,
                'daemon_container',
                [
                    'port_open',
                    'dns_resolution',
                    'ssl_request']),
            ], ids=['jobs', 'daemons'])
    def test_collect_jobs(
            self, suite_factory, dummy_config,
            f, num_suites, num_cases, cls, container, names):

        configurations, order_list = dummy_config.read_unit_configuration(
            'unit/start')
        f(suite_factory, configurations)

        suites = suite_factory.suites
        assert len(suites) == num_suites

        # test only one configuration
        cases = [s for s in suites if s.name.startswith(container)][0].cases
        assert len(cases) == num_cases

        for case in cases:
            assert type(case) == cls

        casedicts = [case.as_dict() for case in cases]
        names = [c['testcase_name'] for c in casedicts]
        assert (set(names) == set(names))


def test_junit_generation():
    """
    checks that the junit generation works.
    Maybe, this is done in test_container/test_statistics()???
    """
    assert False


#   backup:
#     job:
#       args: []
#       exit_code: 0
#       logs:
#         - re.match: "Success"
def test_collect_external_tests_jobs():
    """
    checks that the collection of external job tests work
    """
    assert False

#   e2e-check:
#     start:
#       links:
#         - ["cgit.main", "nginx_server"]
#
# tests that HTML requests to the two domains https://cgit.main:443 and
# http://{{.Network.IPAddress}}(cgit):80  succeed.  Note, that the checks are
# run from the special container e2e-check, that might need to add links to
# running containers.

# cgit:
#   daemon:
#     - GET:
#          url: https://cgit.main:443
#          status: 200
#          re.match: "My personal git repositories"
#          cert: ${DOCKERCONF}/cgit.main.pem
#     - GET:
#          url: http://{{.Network.IPAddress}}(cgit):80
#          status: 200
#          re.match: "My personal git repsoitories"


def test_collect_external_tests_daemon():
    """
    checks that the collection of the external tests, works
    """
    assert False


def test_run_external_tests_daemon():
    """
    checks that the external tests work with dummy containers...

    makes a GET request, a HEAD request and done.
    """


def test_run_external_tests_jobs():
    """
    check that the external tests work with dummy jobs...

    runs a /bin/true and a /bin/false container and done.
    """


#  python_programme:
#    tests:
#      pytests:
#        execute: make test
#        overwrites:
#          volumes_from: python3_virtualenv
#        extra:
#          binds:
#            /uploads:
#              bind: /uploads
#              ro: False
#        files: ["coverage_html/", "junit-*.xml"]
#        capture_logs: True
#
def collect_internal_jobs():
    """
    checks that the collection of internal jobs is done correctly
    """


def test_run_internal_jobs():
    """
    runs a single internal test job and shows that it gathers the necessary
    information...
    """

# vim:set ft=python sw=4 et spell spelllang=en:
