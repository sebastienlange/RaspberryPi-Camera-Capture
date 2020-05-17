import io
import os
import tempfile
import unittest
from datetime import datetime, timedelta
from subprocess import CompletedProcess

from mock import patch, ANY, Mock

import keep_alive


def assert_not_called_with(self, *args, **kwargs):
    try:
        self.assert_called_with(*args, **kwargs)
    except AssertionError:
        return
    raise AssertionError('Expected %s to not have been called.' % self._format_mock_call_signature(args, kwargs))


Mock.assert_not_called_with = assert_not_called_with


def is_alive_with_last_activity(minutes_ago):
    with tempfile.NamedTemporaryFile() as jpg_file:
        modification_time = (
                datetime.utcnow() - timedelta(minutes=minutes_ago) - datetime(1970, 1,
                                                                              1)).total_seconds()
        os.utime(jpg_file.name, (modification_time, modification_time))
        keep_alive.isalive(jpg_file.name)


class TestKeepAlive(unittest.TestCase):

    @patch("subprocess.Popen", return_value=CompletedProcess(None, 0, io.StringIO(''), ''))
    def test_reboot_called_when_last_activity_greater_than_max(self, patch_popen):
        is_alive_with_last_activity(minutes_ago=keep_alive.MAX_MINUTES_BEFORE_REBOOT + 1)

        patch_popen.assert_called_with('sudo reboot', shell=ANY, stderr=ANY, stdout=ANY, text=ANY)

    @patch("subprocess.Popen", return_value=CompletedProcess(None, 0, io.StringIO(''), ''))
    def test_reboot_not_called_when_last_activity_smaller_than_max(self, patch_popen):
        is_alive_with_last_activity(minutes_ago=keep_alive.MAX_MINUTES_BEFORE_REBOOT - 1)

        patch_popen.assert_not_called_with('sudo reboot', shell=ANY, stderr=ANY, stdout=ANY, text=ANY)


if __name__ == '__main__':
    unittest.main()
