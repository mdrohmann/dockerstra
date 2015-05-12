import time

import pytest

from docker_meta import utils


@pytest.fixture(
    params=['with_err', 'without_err'])
def out_err_handlers(request):
    start = time.time()
    outlist = []
    errlist = []

    def make_handler(listobj):

        def handler(line):
            listobj.append((line, time.time() - start))

        return handler

    outhandler = make_handler(outlist)
    if request.param == 'with_err':
        errhandler = make_handler(errlist)
    else:
        errhandler = None

    return outlist, errlist, outhandler, errhandler


@pytest.mark.parametrize(
    'twisted', [
        False,
        pytest.mark.skipif('not utils.has_twisted', True),
    ],
    ids=['subprocess', 'twisted'])
def test_spawn(twisted, out_err_handlers):

    outlist, errlist, outhandler, errhandler = out_err_handlers

    ret = utils.spawnProcess(
        ['echo hi; sleep 0.1; echo welt; echo foo 1>&2;'
         'sleep 0.1; echo bar;'],
        outhandler, errhandler, shell=True, twisted=twisted)

    def internal(ret):
        assert ret == 0
        assert [o[0] for o in outlist] == ['hi\n', 'welt\n', 'bar\n']
        assert outlist[1][1] > 0.09 and outlist[1][1] < 0.11
        assert outlist[2][1] > 0.19 and outlist[2][1] < 0.21
        if errhandler:
            assert [o[0] for o in errlist] == ['foo\n']
            assert errlist[0][1] > 0.09 and errlist[0][1] < 0.11
        else:
            assert len(errlist) == 0

    def whatsgoingon(failure):
        assert False, failure

    if twisted:
        ret.addCallbacks(internal, whatsgoingon)
    else:
        internal(ret)

    return ret

# vim:set ft=python sw=4 et spell spelllang=en:
