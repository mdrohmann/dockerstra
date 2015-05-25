# -*- coding: utf-8 -*-


def test_manipulate_names_and_tags():
    """
    makes sure, that the container names and tags are manipulated correctly
    if necessary.
    """
    assert False


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
