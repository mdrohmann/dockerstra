import OpenSSL
import pytest
from service_identity.exceptions import VerificationError
from twisted.internet import reactor
from twisted.internet.ssl import PrivateCertificate
from twisted.python.modules import getModule
from twisted.web.client import Agent, BrowserLikePolicyForHTTPS
from twisted.web.http_headers import Headers


sslcgit_trustRoot = (
    getModule(__name__).filePath.parent().sibling('certs')
    .child('ssl.cgit.main.pem').getContent()
)
invalid_trustRoot = (
    getModule(__name__).filePath.sibling('invalid.pem').getContent()
)


@pytest.fixture
def url_trustRoot(request):
    return request.param


@pytest.fixture
def agent_call(url_trustRoot):
    url, trustRoot = url_trustRoot
    if trustRoot:
        customPolicy = BrowserLikePolicyForHTTPS(
            PrivateCertificate.loadPEM(trustRoot)
        )
        agent = Agent(reactor, customPolicy)
    else:
        agent = Agent(reactor)

    headers = Headers(
        {'User-Agent': ['Twisted Webbot'],
         'Content-Type': ['text/x-greeting']})

    d = agent.request('HEAD', url, headers=headers)
    return d


# TODO: add a test, where the authentication fails...
@pytest.mark.parametrize(
    'url_trustRoot, expected_header, expect_reject',
    [(('http://cgit.main', None),
      (('HTTP', 1, 1), 200, False), None),
     (('https://ssl.cgit.main', sslcgit_trustRoot),
      (('HTTP', 1, 1), 200, True), None),
     (('https://ssl.cgit.main', invalid_trustRoot),
      (('HTTP', 1, 1), 200, True), OpenSSL.SSL.Error),
     (('http://ssl.cgit.main', None),
      (('HTTP', 1, 1), 301, False), None),
     (('https://cgit.main', sslcgit_trustRoot),
      (('HTTP', 1, 1), 200, True), VerificationError),
     (('https://ssl2.cgit.main', sslcgit_trustRoot),
      (('HTTP', 1, 1), 200, True), VerificationError),
     ],
    ids=[
        'http://cgit.main',
        'https://ssl.cgit.main',
        'https://ssl.cgit.main[invalid]',
        'http://ssl.cgit.main',
        'https://cgit.main',
        'https://ssl2.cgit.main'
    ])
def test_header_responses(
        agent_call, url_trustRoot, expected_header, expect_reject):

    url, trustRoot = url_trustRoot
    version, code, sts = expected_header

    def error(failure):
        if expect_reject:
            assert type(failure.value.reasons[0].value) == expect_reject
        else:
            assert False, "No rejection expected"

    def header_expectations(response):
        assert response.version == version
        assert response.code == code
        sts_header = response.headers.getRawHeaders(
            'strict-transport-security')
        if trustRoot:
            assert sts_header
        else:
            assert sts_header is None
        return response

    agent_call.addCallbacks(header_expectations, error)

    return agent_call


# vim:set ft=python sw=4 et spell spelllang=en:
