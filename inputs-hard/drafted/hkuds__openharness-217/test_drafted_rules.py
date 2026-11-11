import os
import subprocess
from unittest import mock
import pytest
from hypothesis import given, strategies as st
from openharness.auth.flows import DeviceCodeFlow
PLATFORMS = ['Windows', 'Darwin', 'Linux']

class _Proc:
    returncode = 0

    def wait(self, timeout=None):
        return 0

def _run(plat, url, startfile_side_effect=None):
    """Call _try_open_browser on a faked platform; return (result, popen_mock, startfile_mock)."""
    popen = mock.Mock(return_value=_Proc())
    startfile = mock.Mock(side_effect=startfile_side_effect)
    with mock.patch('platform.system', return_value=plat), mock.patch.object(subprocess, 'Popen', popen), mock.patch.object(os, 'startfile', startfile, create=True):
        result = DeviceCodeFlow._try_open_browser(url)
    return (result, popen, startfile)

def _shell_used(popen):
    return any((c.kwargs.get('shell') for c in popen.call_args_list))

def test_windows_opens_url_verbatim_with_startfile():
    """On Windows, a valid http(s) URL is passed unchanged to os.startfile and True is returned."""
    url = 'https://github.com/login/device&calc.exe|x^y'
    result, popen, startfile = _run('Windows', url)
    assert result is True
    startfile.assert_called_once_with(url)
    assert popen.call_count == 0

def test_windows_startfile_oserror_returns_false():
    """On Windows, if os.startfile raises OSError, _try_open_browser returns False."""
    result, _, _ = _run('Windows', 'https://github.com/login/device', startfile_side_effect=OSError('boom'))
    assert result is False

def test_windows_startfile_unavailable_returns_false():
    """On Windows, if os.startfile is unavailable, _try_open_browser returns False."""
    popen = mock.Mock(return_value=_Proc())
    with mock.patch('platform.system', return_value='Windows'), mock.patch.object(subprocess, 'Popen', popen):
        if hasattr(os, 'startfile'):
            with mock.patch.object(os, 'startfile', side_effect=AttributeError('x')):
                result = DeviceCodeFlow._try_open_browser('https://github.com/login/device')
        else:
            result = DeviceCodeFlow._try_open_browser('https://github.com/login/device')
    assert result is False
    assert not _shell_used(popen)

def test_macos_opens_with_argv_list_without_shell():
    """On macOS, a valid URL is opened via an argv list ['open', url] without a shell."""
    url = 'https://github.com/login/device'
    result, popen, _ = _run('Darwin', url)
    assert result is True
    assert popen.call_args.args[0] == ['open', url]
    assert not _shell_used(popen)

def test_linux_opens_with_argv_list_without_shell():
    """On Linux, a valid URL is opened via an argv list ['xdg-open', url] without a shell."""
    url = 'https://github.com/login/device'
    result, popen, _ = _run('Linux', url)
    assert result is True
    assert popen.call_args.args[0] == ['xdg-open', url]
    assert not _shell_used(popen)

@pytest.mark.parametrize('plat', PLATFORMS)
@pytest.mark.parametrize('url', ['file:///etc/passwd', 'javascript:alert(1)', 'calc.exe', 'ftp://example.com/x', ''])
def test_non_http_or_empty_url_is_rejected_on_all_platforms(plat, url):
    """A non-http(s) or empty URL returns False on every platform and launches nothing."""
    result, popen, startfile = _run(plat, url)
    assert result is False
    assert popen.call_count == 0
    assert startfile.call_count == 0

@pytest.mark.parametrize('plat', PLATFORMS)
@pytest.mark.parametrize('scheme', ['http', 'https'])
def test_http_and_https_urls_are_accepted(plat, scheme):
    """An http or https URL is accepted and opened on every platform."""
    result, popen, startfile = _run(plat, f'{scheme}://example.com/device')
    assert result is True
    assert popen.call_count + startfile.call_count == 1

@given(url=st.text(max_size=60).filter(lambda s: not s.lower().startswith(('http://', 'https://'))), plat=st.sampled_from(PLATFORMS))
def test_property_non_http_urls_never_reach_a_launcher(url, plat):
    """For any URL that is not http(s), no launcher is invoked and False is returned."""
    result, popen, startfile = _run(plat, url)
    assert result is False
    assert popen.call_count == 0
    assert startfile.call_count == 0