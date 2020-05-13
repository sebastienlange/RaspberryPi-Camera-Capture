import io
import unittest
from subprocess import CompletedProcess
from unittest import mock
from unittest.mock import Mock
from unittest.mock import patch

import utils


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

    SAMPLE_NEW_FILE = "2020-05-13 07-45-02.jpg"
    RCLONE_SAMPLE_STDOUT_NEW_FILE = f"""2020/05/13 08:13:09 INFO  : Dropbox root 'EnergySuD/RaspberryPi/Pictures': Waiting for checks to finish
2020/05/13 08:13:10 INFO  : {SAMPLE_NEW_FILE}: Copied (new)
2020/05/13 08:13:10 INFO  : Dropbox root 'EnergySuD/RaspberryPi/Pictures': Waiting for transfers to finish
2020/05/13 08:13:10 INFO  : Waiting for deletions to finish
2020/05/13 08:13:10 INFO  :
Transferred:      166.349k / 166.349 kBytes, 100%, 119.121 kBytes/s, ETA 0s
Checks:              2126 / 2126, 100%
Transferred:            1 / 1, 100%
Elapsed time:         1.3s"""

    @patch("subprocess.Popen", return_value=CompletedProcess(None, 0, io.StringIO(RCLONE_SAMPLE_STDOUT_NEW_FILE), ''))
    def test_sync_pictures_new_file_logged(self, patch_run, new_file=SAMPLE_NEW_FILE, sample_rclone_output=RCLONE_SAMPLE_STDOUT_NEW_FILE):
        #with patch('__main__.open', mock.mock_open(read_data=sample_rclone_output), create=True):
        with self.assertLogs(level='INFO') as log:
            utils.sync_files('', '')
            self.assertTrue(any([new_file in log_line for log_line in log.output]))


if __name__ == '__main__':
    unittest.main()
