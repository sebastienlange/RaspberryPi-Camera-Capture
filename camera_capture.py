import json
import logging
import logging.handlers
import os
import pathlib
import sys

import schedule

from utils import run_command, sync_dropbox

try:
    from picamera import PiCamera
    from picamera import Color
except ImportError:
    from fake_rpi.picamera import PiCamera
    from PIL.ImageEnhance import Color


from time import sleep
from datetime import datetime

APP_NAME = pathlib.Path(__file__).name
LOG_FILE = f'/var/log/EnergySuD/{pathlib.Path(__file__).stem}.log'
PICTURES_PATH = '/home/pi/Pictures/EnergySuD'
CONFIG_FILE = os.path.join(pathlib.Path(__file__).parent.absolute(), pathlib.Path(__file__).stem + '.json')

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.handlers.TimedRotatingFileHandler(LOG_FILE, when='midnight'),
            logging.StreamHandler()
        ]
    )


def read_config(old_config, config_file=CONFIG_FILE):
    try:
        with open(config_file) as json_data_file:
            return json.load(json_data_file)
    except:
        logging.error(sys.exc_info()[1], exc_info=sys.exc_info())
        logging.info('Continuing with old config')
        return old_config


def switch_light(on_or_off):
    # turn on or off the 4 USB ports
    run_command(f"sudo uhubctl -l 1-1 -a {on_or_off}", should_log=False)


def annotate_picture(camera, camera_config):
    camera.annotate_size = 50
    camera.annotate_foreground = Color('black')
    camera.annotate_background = Color('white')
    camera.annotate_text = str({k: v for k, v in camera_config.items() if 'preview' not in k})


def take_pictures(camera_config, n=3, sleep_time=3):
    try:
        with PiCamera() as camera:

            try:
                if camera_config['preview']['light_only_for_pictures']:
                    switch_light("on")
                camera.resolution = tuple(camera_config['resolution'])
                camera.rotation = camera_config['rotation']
                camera.zoom = tuple(camera_config['zoom'])
                camera.brightness = camera_config['brightness']
                camera.saturation = camera_config['saturation']
                camera.contrast = camera_config['contrast']

                if camera_config['preview']['annotate_config_to_pictures']:
                    annotate_picture(camera, camera_config)

                camera.start_preview(fullscreen=False, window=tuple(camera_config['preview']['window']))

                for i in range(n):
                    sleep(sleep_time if i == 0 else 1)
                    fn = f'{PICTURES_PATH}/{datetime.now().strftime("%Y-%m-%d %H-%M-%S")}.jpg'
                    camera.capture(fn, quality=camera_config['quality'])
                    logging.info(f'Saving picture to {fn}')
            except:
                logging.error(sys.exc_info()[1], exc_info=sys.exc_info())

            finally:
                camera.stop_preview()
                if camera_config['preview']['light_only_for_pictures']:
                    switch_light("off")

    except picamera.exc.PiCameraMMALError:
        logging.error(sys.exc_info()[1], exc_info=sys.exc_info())
        run_command('sudo reboot', f'Suspecting PiCamera out of resources => rebooting', thread=True)

    except:
        logging.error(sys.exc_info()[1], exc_info=sys.exc_info())


def initialize(camera_config, old_camera_config):
    if old_camera_config is None:
        logging.info(f'Starting with configuration: {camera_config}')
        switch_light('off' if camera_config['preview']['light_only_for_pictures'] else 'on')
    elif camera_config['preview']['light_only_for_pictures'] != old_camera_config['preview']['light_only_for_pictures']:
        switch_light('off' if camera_config['preview']['light_only_for_pictures'] else 'on')


def schedule_job(job, camera_config):
    try:
        if ('enabled' not in job) or job['enabled']:
            at_times = job['at'] if 'at' in job else None
            at_times = at_times if isinstance(at_times, list) else [at_times]
            for at in at_times:
                scheduled_job = schedule.every(job['interval'] if 'interval' in job else 1)
                scheduled_job = getattr(scheduled_job, job['every'] if 'every' in job else 'hour')
                if at is not None:
                    scheduled_job = getattr(scheduled_job, 'at')(at)

                if 'command' in job:
                    scheduled_job = scheduled_job.do(run_command, job['command'],
                                                     None if 'silent' in job['tag'] else job['tag']).tag(job['tag'])
                elif 'Dropbox' in job['tag']:
                    scheduled_job = scheduled_job.do(sync_dropbox, APP_NAME).tag(job['tag'])
                else:
                    scheduled_job = scheduled_job.do(take_pictures, camera_config).tag(job['tag'])

                if 'execute_once' in job['tag']:
                    scheduled_job.run()
                    schedule.clear(job['tag'])

                if 'silent' not in job['tag']:
                    logging.info(
                        f'Scheduled to {job["tag"]} every {str(job["interval"]) + " " if "interval" in job else ""}{job["every"]}{" at " + at if "at" in job else ""}')
        elif 'command' not in job:
            logging.info(
                f'Job "{job["tag"]}" disabled: will not {job["tag"]} every {str(job["interval"]) + " " if "interval" in job else ""}{job["every"]}{" at " + job["at"] if "at" in job else ""}')

    except:
        logging.error(sys.exc_info()[1], exc_info=sys.exc_info())


def schedule_jobs(new_config, old_config=None):
    initialize(new_config['camera'], None if old_config is None else old_config['camera'])

    for job, old_job in zip(new_config['scheduled_jobs'],
                            [None] * len(new_config['scheduled_jobs']) if old_config is None else old_config[
                                'scheduled_jobs']):
        if job != old_job:
            if old_job is not None:
                logging.info(f'{CONFIG_FILE} changed => cancelling job {job["tag"]}')
                schedule.clear(job["tag"])

            schedule_job(job, new_config['camera'])

    return new_config


if __name__ == "__main__":
    try:
        config = None

        logging.info('')
        logging.info('+' * 80)
        logging.info('')

        while True:
            config = schedule_jobs(read_config(config), config)

            schedule.run_pending()
            sleep(1)

    except:
        logging.critical(sys.exc_info()[1], exc_info=sys.exc_info())

    sys.exit()
