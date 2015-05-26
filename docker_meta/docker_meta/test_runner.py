# -*- coding: utf-8 -*-

import hashlib
import logging
import platform
import time
import traceback
from cStringIO import StringIO

from junit_xml import TestCase, TestSuite
from docker_meta import __name__ as docker_meta_name
from docker_meta.utils import get_timestamp
from docker_meta.container import (prepare_job, run_job)
from docker_meta import logger

log = logging.getLogger(docker_meta_name)


class CaseBase(object):
    """
    base class for testrunner cases representing one or more test cases.
    """

    def __init__(self, name, parent, classname=None):
        self.parent = parent
        self.name = name
        self.classname = classname

    def _update_logger(self, stdout, stderr):
        logger.configure_logger(stdout, stderr, verbosity=2)

    def as_dict(self):
        """
        formats the case as a dictionary.

        This way we can create a full blown test configuration and fix it in a
        configuration file... (Kind of like pickling!!!)
        """
        return {
            'testcase_name': self.name,
            'testcase_class': self.classname,
        }

    def run_test(self):
        """
        runs the actual test.  This needs to be implemented in the derived
        class.
        """

        raise NotImplementedError(
            "Please implement this in your derived class.")

    def _run_unit_test(self, args):
        envs = self.parent.compute_environment_injections()

        args = self.create_unit_call(self)
        args.environment = envs

        main_run(args)

    def run_case(self, case):
        """
        runs a single test case and returns a junit_xml.TestCase object with
        the results
        """

        failure = None
        stdout, stderr = StringIO(), StringIO()

        start = time.time()
        try:
            self.run_test(stdout, stderr)
        except Exception as e:
            failure = (
                "FAILURE: {}".format(str(e)),
                traceback.format_exc(3))
        except SystemExit as e:
            failure = (
                "FAILURE: test return with error code: {}\n{}"
                .format(e.error_code, str(e)),
                traceback.format_exc(3))
        end = time.time()
        elapsed = (end - start)

        res = TestCase(
            self.name, self.classname, elapsed_sec=elapsed,
            stdout=stdout.getvalue(), stderr=stderr.getvalue())
        if failure:
            res.add_failure_info(*failure)

        return res


class DaemonCase(CaseBase):
    """
    a test case for a simple daemon request.
    """

    def __init__(self, container, name, config):
        self.container_name = container
        self.config = config
        CaseBase.__init__(self, name, 'daemon')

    def as_dict(self):
        config = CaseBase.as_dict(self)
        config.update({
            'container_name': self.container_name,
            'request_config': self.config
        })
        return config

    def run_test(self):
        self.do_request(self.command.keys()[0], self.command.values()[0])


class SingleCase(CaseBase):
    """
    a test case for default single job
    """

    def __init__(self, container, name, config):
        self.container_name = container
        self.config = config

        CaseBase.__init__(self, name, 'single')

    def as_dict(self):
        config = CaseBase.as_dict(self)
        config.update({
            'container_name': self.container_name,
            'request_config': self.config
        })
        return config

    def run_test(self):
        raise NotImplementedError()


class SetupTeardownCase(CaseBase):
    """
    a test case for the setup phase.
    """

    def __init__(self, container, cmd, orders, typename='setup'):
        name = ':'.join([container.name, cmd])
        CaseBase.__init__(self, name, typename)
        self.cmd = cmd
        self.container = container
        self.orders = orders
        self.fix_startup()

    def run_test(self, stdout, stderr):
        self._update_logger(stdout, stderr)

        run_job(self.cmd, self.container, self.orders)

    def as_dict(self):
        config = CaseBase.as_dict(self)
        config.update({
            'cmd': self.cmd,
            'orders': self.orders,
            'startup': self.container.startup,
            'creation': self.container.creation,
            'build': self.container.build,
        })
        return config

    def fix_startup(self):
        if self.cmd == 'start':
            # make non-interactive and attach to output:
            self.container.startup['tty'] = False
            self.container.startup['stdin_open'] = False
            self.orders['attach'] = True


class JunitCase(CaseBase):
    """
    a test case for a script that produces a junit file itself eg., a pytest
    run
    """

    def __init__(self, name):
        self.cases = self.collect()
        CaseBase.__init__(self, name, 'junit')

    def run_test(self):
        raise NotImplementedError()


class SuiteFactory(object):

    def __init__(self, unitcommand, config, dc):
        self.config = config
        self.dc = dc
        self.unitcommand = unitcommand
        self.unit, _, self.modes = config.split_unit_command(
            unitcommand)
        self._digest = None
        self.suites = []
        self._jsuites = []

    def collect_setup(self, configurations, order_list, typename='setup'):

        cases = []
        for item in order_list:
            name, orders = item.items()[0]
            cmd, container = prepare_job(
                name, self.dc, self.unitcommand, self.config,
                orders, configurations)

            # filter the clean-up phase, we will remove everything tagged with
            # a tempid and stop the rest.
            if cmd in ['stop', 'remove', 'remove_image']:
                log.warn(
                    "Are you sure, that you want to execute a {} order "
                    "in the test-scenario?".format(cmd))

            case = SetupTeardownCase(container, cmd, orders, 'typename')
            cases.append(case)

        self.suites.append(Suite(self.unitcommand, cases))

    def create_cleanup(self, configurations, order_list):
        """
        creates the cleanup - list of orders for the test runs
        """

        new_configurations, new_order_list = (
            self.config.modify_order_list(configurations, order_list, 'purge'))

        def _filter(item):
            name, orders = item.items()[0]
            cmd = orders['command']
            if cmd == 'remove_image':
                build_config = new_configurations[name].get('build', {})
                if build_config.get('tag').endswith(self.tempid()):
                    return True
            else:
                if name.endswith(self.tempid()):
                    return True

            return False

        res_order_list = [item for item in new_order_list if _filter(item)]
        self.collect_setup(new_configurations, res_order_list)

    def collect_daemon_requests(self, configurations):
        self._collect_job(configurations, 'daemon', DaemonCase)

    def collect_single_jobs(self, configurations):
        self._collect_job(configurations, 'jobs', SingleCase)

    def _collect_job(self, configurations, key, cls):
        for container, config in configurations.items():
            if key in config:
                cases = []
                for test_name, test_config in config[key].items():
                    cases.append(cls(container, test_name, test_config))

                suite = Suite('{}_{}'.format(container, key), cases)
                self.suites.append(suite)

    def collect_cases(self):
        """
        make a suite for every daemon or job entry you can find, and for
        every unit/script execution, that is necessary.

        Later, the globals selection might have some meta information, that
        allows to specify more ridiculous setup and teardown configurations,
        right now we simply do unit/start and unit/cleanup (everything that
        is tagged with the tempid is removed)

        Right now this should do, as we can start special end-to-end
        containers for external testing, that cannot be done by the
        dockerstra.test_runner.
        """

        self.inject_tempid()
        configurations, order_list = self.config.read_unit_configuration(
            self.unitcommand)

        self.collect_setup(configurations, order_list)

        self.collect_daemon_requests(configurations)

        self.collect_single_jobs(configurations)

        self.create_cleanup(configurations, order_list)

    def inject_tempid(self):
        self.config.update_environment(
            {'tempid': self.tempid()})

    def output_xml(self, filename):
        if not self._jsuites:
            raise RuntimeError(
                "You need to call run_all() before printing the results")

        with open(filename, 'w') as fh:
            TestSuite.to_file(
                fh, self._jsuites, prettyprint=False, encoding='utf-8')

    def tempid(self, long=False):
        if not self._digest:
            self._digest = hashlib.md5(self.unitcommand).hexdigest()[0:10]
        if long:
            return '{}_{}'.format(self.unitcommand, self._digest)
        else:
            return self._digest

    def run_all(self):
        # create the runs:
        timestamp = get_timestamp()

        for suiten, suite in enumerate(self.suites):
            rescases = suite.run_all()

            jsuite = TestSuite(
                self.name,
                rescases, hostname=platform.node(),
                id='_'.join([self.tempid(long=True), suiten]),
                timestamp=timestamp)
            self._jsuites.append(jsuite)


class Suite(object):
    """
    handles the jobs to execute, and outputs their information.
    """

    def __init__(self, name, cases):
        self.name = name
        self.cases = cases

    def run(self):
        rescases = []
        for case in self.cases:
            res = self.run_case(case)
            rescases.append(res)
        return rescases


# vim:set ft=python sw=4 et spell spelllang=en:
