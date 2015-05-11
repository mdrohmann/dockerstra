import time

import pytest

from docker_meta import utils


@pytest.mark.parametrize(
    'twisted', [False, True], ids=['subprocess', 'twisted'])
def test_spawn(twisted):

    start = time.time()
    outlist = []
    errlist = []

    def make_handler(listobj):

        def handler(line):
            listobj.append((line, time.time() - start))

        return handler

    outhandler = make_handler(outlist)
    errhandler = make_handler(errlist)

    ret = utils.spawnProcess(
        ['echo hi; sleep 0.1; echo welt; echo foo 1>&2; sleep 0.1; echo bar;'],
        outhandler, errhandler, shell=True, twisted=twisted)
    assert ret == 0
    assert [o[0] for o in outlist] == ['hi\n', 'welt\n', 'bar\n']
    assert [o[0] for o in errlist] == ['foo\n']
    assert outlist[1][1] > 0.09 and outlist[1][1] < 0.11
    assert outlist[2][1] > 0.19 and outlist[2][1] < 0.21
    assert errlist[0][1] > 0.09 and errlist[0][1] < 0.11

# vim:set ft=python sw=4 et spell spelllang=en:
