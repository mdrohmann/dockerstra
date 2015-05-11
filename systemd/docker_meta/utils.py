try:
    from twisted.internet import protocol, reactor, defer
    has_twisted = True
except:
    has_twisted = False

try:
    import subprocess32 as subprocess
except:
    import subprocess
import select


if has_twisted:

    class SpawnProtocol(protocol.ProcessProtocol):

        def __init__(self, outhandler, errhandler, kill_reactor=True):
            self.outhandler = outhandler
            self.errhandler = errhandler
            self.returncode = None
            self.deferred = defer.Deferred()
            self.kill_reactor = kill_reactor

        def errReceived(self, data):
            if self.errhandler:
                self.errhandler(data)

        def outReceived(self, data):
            self.outhandler(data)

        def processEnded(self, reason):
            self.returncode = reason.value.exitCode
            if self.kill_reactor:
                reactor.stop()
            else:
                self.deferred.callback(self.returncode)


def spawnProcess(
        run_args, outhandler, errhandler=None, shell=True, twisted=False):
    if twisted:
        if shell:
            run_args = ['/bin/bash', '-c'] + run_args

        if not has_twisted:
            raise RuntimeError(
                "Twisted is not installed.  Please install or use subprocess")

        sp = SpawnProtocol(outhandler, errhandler, kill_reactor=True)
        reactor.spawnProcess(sp, run_args[0], run_args)
        return sp.deferred
    else:
        stderr = subprocess.PIPE
        if errhandler is None:
            stderr = None

        p = subprocess.Popen(
            run_args,
            stdout=subprocess.PIPE, stderr=stderr,
            shell=shell)
        sel_list = [p.stdout]
        if errhandler:
            sel_list.append(p.stderr)
        while p.poll() is None:
            res = select.select(sel_list, [], [], 2)[0]
            for out in res:
                line = out.readline()
                if line:
                    if out == p.stdout:
                        outhandler(line)
                    else:
                        errhandler(line)
        # theoretically, we could have missed the final output...
        orest = p.stdout.read()
        if orest:
            outhandler(orest)
        if errhandler:
            erest = p.stderr.read()
            if erest:
                errhandler(erest)
        p.communicate()

        return p.returncode

# vim:set ft=python sw=4 et spell spelllang=en:
