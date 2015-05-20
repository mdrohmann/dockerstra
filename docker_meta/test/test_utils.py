import time

import pytest

from docker_meta import utils, utils_spawn


def test_deepupdate():
    init = {'a': {'b': 1}}
    update = {'a': {'c': 2}}
    expect = {'a': {'b': 1, 'c': 2}}

    assert utils.deepupdate(init, update) == expect


def test_recursive_walk(tmpdir):

    tmpdir.chdir()
    tmpdir.ensure('f1')
    tmpdir.join('s1').ensure('f2')
    tmpdir.join('s2').ensure('f3')
    tmpdir.join('s1').join('s3').ensure('f4')

    res = utils.recursive_walk('.')
    assert set(res) == set([
        'f1', 's1/f2', 's2/f3', 's1/s3/f4'])


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
        pytest.mark.skipif('not utils_spawn.has_twisted', True),
    ],
    ids=['subprocess', 'twisted'])
def test_spawn(twisted, out_err_handlers):

    outlist, errlist, outhandler, errhandler = out_err_handlers

    ret = utils_spawn.spawnProcess(
        ['echo hi; sleep 0.1; echo welt; echo foo 1>&2;'
         'sleep 0.1; echo bar;'],
        outhandler, errhandler, shell=True, twisted=twisted)

    def internal(ret):
        assert ret == 0
        assert [o[0] for o in outlist] == ['hi\n', 'welt\n', 'bar\n']
        assert outlist[1][1] > 0.09 and outlist[1][1] < 0.13
        assert outlist[2][1] > 0.19 and outlist[2][1] < 0.23
        if errhandler:
            assert [o[0] for o in errlist] == ['foo\n']
            assert errlist[0][1] > 0.09 and errlist[0][1] < 0.13
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
