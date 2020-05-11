import importlib.util
import numpy as np

try:
    from picamera import PiCamera
except ImportError:
    from fake_rpi.picamera import PiCamera

import unittest
import camera_capture
import logging
import schedule

from unittest import mock
from unittest.mock import MagicMock


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

        self.assertTrue(any(['take pictures' in job.tags for job in schedule.jobs]))

        take_picture_jobs = [job for job in schedule.jobs if 'take pictures' in job.tags]
        expected_job_count = sum([len(job['at']) for job in config['scheduled_jobs'] if job['tag'] == 'take pictures'])
        self.assertEqual(len(take_picture_jobs), expected_job_count)

    def test_take_pictures_does_camera_capture(self):
        camera = PiCamera()
        camera.capture = MagicMock()

        config = camera_capture.read_config(None)
        camera_capture.take_pictures(config)

        camera.capture.assert_called()


if __name__ == '__main__':
    unittest.main()
