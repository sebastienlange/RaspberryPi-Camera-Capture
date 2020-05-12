import unittest
import re

import schedule
from mock import patch

import camera_capture

try:
    from picamera import PiCamera
except ImportError:
    from fake_picamera import PiCamera


class TestCameraCaptureMethods(unittest.TestCase):

    def test_config(self):
        config = camera_capture.read_config(None)

        self.assertTrue('camera' in config)
        self.assertTrue('resolution' in config['camera'])

    def test_failure_loading_config_returns_old_config(self):
        old_config = {"name": "old"}
        config = camera_capture.read_config(old_config, "path/does/not/exist")

        self.assertDictEqual(old_config, config)

    def test_take_pictures_jobs_are_scheduled(self):
        config = None
        config = camera_capture.schedule_jobs(camera_capture.read_config(config), config)
        count = config['scheduled_jobs'][3]['count']

        self.assertTrue(any([f'take {count} pictures' in job.tags for job in schedule.jobs]))

        take_picture_jobs = [job for job in schedule.jobs if 'take pictures' in job.tags]
        expected_job_count = sum([len(job['at']) for job in config['scheduled_jobs'] if job['tag'] == 'take pictures'])
        self.assertEqual(len(take_picture_jobs), expected_job_count)

    @patch.object(PiCamera, 'capture')
    @patch('time.sleep', return_value=None)
    def test_take_pictures_calls_camera_capture(self, mock_time_sleep, mock_capture):
        camera_capture.config = camera_capture.read_config(None)
        camera_capture.take_pictures()

        mock_capture.assert_called()


if __name__ == '__main__':
    unittest.main()
