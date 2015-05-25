import collections
import datetime
import os


def get_timestamp():
    return datetime.now().strftime('%Y%m%d-%H%M')


def deepupdate(d, u):
    for k, v in u.iteritems():
        if isinstance(v, collections.Mapping):
            r = deepupdate(d.get(k, {}), v)
            d[k] = r
        else:
            d[k] = u[k]
    return d


def recursive_walk(path):
    res = []
    for root, dirs, files in os.walk(path):
        for file in files:
            res.append(os.path.relpath(os.path.join(root, file)))

    return res


# vim:set ft=python sw=4 et spell spelllang=en:
