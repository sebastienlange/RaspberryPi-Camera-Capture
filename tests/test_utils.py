import logging
import unittest
from subprocess import CompletedProcess
from unittest.mock import patch

from callee import Contains

import utils

from unittest.mock import Mock


def assert_not_called_with(self, *args, **kwargs):
    try:
        self.assert_called_with(*args, **kwargs)
    except AssertionError:
        return
    raise AssertionError('Expected %s to not have been called.' % self._format_mock_call_signature(args, kwargs))


Mock.assert_not_called_with = assert_not_called_with


class TestUtils(unittest.TestCase):

    GIT_PULL_SAMPLE_STDOUT_UPDATING_FILES = """Fast-forward
 camera_capture.py                        |  4 ++--
 tests.py => tests/test_camera_capture.py |  1 -
 tests/test_utils.py                      | 17 +++++++++++++++++
 utils.py                                 | 15 +++++++--------
 4 files changed, 26 insertions(+), 11 deletions(-)"""

    @patch('subprocess.run', return_value=CompletedProcess(None, 0, GIT_PULL_SAMPLE_STDOUT_UPDATING_FILES, ''))
    def test_code_changed_force_reboot(self, patch_run):
        with self.assertLogs(level='INFO') as log:
            utils.sync_app()

            for line in patch_run.return_value.stdout.splitlines():
                if '.py' in line and '|' in line:
                    self.assertTrue(any([line.strip() in log_line for log_line in log.output]))

            patch_run.assert_called_with('sudo reboot', shell=True, text=True, capture_output=True)

    GIT_PULL_SAMPLE_STDOUT_ALREADY_UPDATED = """Depuis https://github.com/sebastienlange/RaspberryPi-Camera-Capture
 * branch            master     -> FETCH_HEAD
Dj  jour."""

    @patch('subprocess.run', return_value=CompletedProcess(None, 0, GIT_PULL_SAMPLE_STDOUT_ALREADY_UPDATED, ''))
    def test_no_code_changed_no_reboot(self, patch_run):
        utils.sync_app()
        patch_run.assert_not_called_with('sudo reboot', shell=True, text=True, capture_output=True)


if __name__ == '__main__':
    unittest.main()
