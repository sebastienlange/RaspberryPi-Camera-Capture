import unittest
from subprocess import CompletedProcess
from unittest.mock import patch

import utils


class TestUtils(unittest.TestCase):
    @patch('subprocess.run', return_value=CompletedProcess(None, 0, 'camera_capture.py |', ''))
    def test_code_changed_force_reboot(self, patch_run):

        utils.sync_app()
        patch_run.assert_called_with('sudo reboot', shell=True, text=True, capture_output=True)


if __name__ == '__main__':
    unittest.main()
