import json
import logging
import logging.handlers
import os
import pathlib
import sys
import time

import schedule

from utils import run_command, sync_dropbox

try:
    from picamera import PiCamera
    from picamera import Color
except ImportError:
    from fake_picamera import PiCamera
    from PIL.ImageEnhance import Color

from datetime import datetime

APP_NAME = pathlib.Path(__file__).name
LOG_FILE = f'/var/log/EnergySuD/{pathlib.Path(__file__).stem}.log'
PICTURES_PATH = '/home/pi/Pictures/EnergySuD'
CONFIG_FILE = os.path.join(pathlib.Path(__file__).parent.absolute(), pathlib.Path(__file__).stem + '.json')
config = None

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
    camera.annotate_text_size = 14
    camera.annotate_foreground = Color('black')
    camera.annotate_background = Color('white')
    camera.annotate_text = json.dumps({k: v for k, v in camera_config.items() if 'preview' not in k}, indent=4)


def configure_camera(camera, camera_config):
    camera.rotation = camera_config['rotation']
    camera.brightness = camera_config['brightness']
    camera.saturation = camera_config['saturation']
    camera.contrast = camera_config['contrast']
    camera.resolution = tuple(camera_config['resolution'])
    camera.zoom = tuple(camera_config['zoom'])


def take_pictures(n=3, sleep_time=3):
    try:
        camera_config = config['camera']
        light_only_for_pictures = config['light_only_for_pictures']

        with PiCamera() as camera:

            try:
                configure_camera(camera, camera_config)

                if light_only_for_pictures:
                    switch_light("on")

                if config['annotate_config_to_pictures']:
                    annotate_picture(camera, camera_config)

                camera.start_preview(fullscreen=False, window=tuple(camera_config['preview']['window']))

                for i in range(1, n+1):
                    time.sleep(sleep_time if i == 0 else 1)
                    fn = f'{PICTURES_PATH}/{datetime.now().strftime("%Y-%m-%d %H-%M-%S")}.jpg'
                    camera.capture(fn, quality=camera_config['quality'])
                    logging.info(f'Saving picture{" " + str(i) if n>1 else ""} to {fn}')
            except:
                logging.error(sys.exc_info()[1], exc_info=sys.exc_info())

            finally:
                camera.stop_preview()
                if light_only_for_pictures:
                    switch_light("off")
                sync_dropbox()

    except picamera.exc.PiCameraMMALError:
        logging.error(sys.exc_info()[1], exc_info=sys.exc_info())
        run_command('sudo reboot', f'Suspecting PiCamera out of resources => rebooting', thread=True)

    except:
        logging.error(sys.exc_info()[1], exc_info=sys.exc_info())


def initialize(new_config, old_config):
    if old_config is None:
        logging.info(f'Starting with configuration: {new_config}')
        switch_light('off' if new_config['light_only_for_pictures'] else 'on')
    elif new_config['preview']['light_only_for_pictures'] != old_config['light_only_for_pictures']:
        switch_light('off' if new_config['light_only_for_pictures'] else 'on')


def schedule_job(job):
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
                    scheduled_job = scheduled_job.do(sync_dropbox).tag(job['tag'])
                else:
                    scheduled_job = scheduled_job.do(take_pictures, job['count'] if 'count' in job else 1).tag(job['tag'])

                if 'execute_once' in job['tag']:
                    scheduled_job.run()
                    schedule.clear(job['tag'])

                if 'silent' not in job['tag']:
                    job_tag = job['tag']
                    if 'count' in job:
                        job_tag = job_tag.format(count=job['count'])
                    logging.info(
                        f'Scheduled to {job_tag} every {str(job["interval"]) + " " if "interval" in job else ""}{job["every"]}{" at " + at if "at" in job else ""}')
        elif 'command' not in job:
            logging.info(
                f'Job "{job["tag"]}" disabled: will not {job["tag"]} every {str(job["interval"]) + " " if "interval" in job else ""}{job["every"]}{" at " + job["at"] if "at" in job else ""}')

    except:
        logging.error(sys.exc_info()[1], exc_info=sys.exc_info())


def schedule_jobs(new_config, old_config=None):
    initialize(new_config, None if old_config is None else old_config)

    for job, old_job in zip(new_config['scheduled_jobs'],
                            [None] * len(new_config['scheduled_jobs']) if old_config is None else old_config[
                                'scheduled_jobs']):
        if job != old_job:
            if old_job is not None:
                logging.info(f'{CONFIG_FILE} changed => cancelling job {job["tag"]}')
                schedule.clear(job["tag"])

            schedule_job(job)

    return new_config


if __name__ == "__main__":
    try:
        logging.info('')
        logging.info('+' * 80)
        logging.info('')

        while True:
            config = schedule_jobs(read_config(config), config)

            schedule.run_pending()
            time.sleep(1)

    except:
        logging.critical(sys.exc_info()[1], exc_info=sys.exc_info())

    sys.exit()
