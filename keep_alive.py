import glob
import logging
import os
import pathlib
import sys
from datetime import datetime, timedelta
from time import sleep

import schedule

import camera_capture
from utils import run_command, sync_all_files

LOG_FILE = f'/var/log/EnergySuD/{pathlib.Path(__file__).stem}.log'

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.handlers.TimedRotatingFileHandler(LOG_FILE, when='midnight'),
            logging.StreamHandler()
        ]
    )


def isalive():
    try:
        run_command("echo $(hostname) is hosted on $(hostname -I | cut -d' ' -f1) through router $(curl --silent api.ipify.org)")
        run_command("echo $(hostname) core temperature is $(/opt/vc/bin/vcgencmd measure_temp | grep 'temp=' | sed 's/^.*=//')")

        list_of_files = glob.glob(os.path.join(camera_capture.PICTURES_PATH, '*.jpg'))
        latest_file = max(list_of_files, key=os.path.getctime)
        log_file_dt = datetime.fromtimestamp(os.path.getmtime(latest_file))
        diff = (datetime.today() - log_file_dt).total_seconds()

        if diff <= 16 * 60:
            logging.info(f'{camera_capture.APP_NAME} was running {timedelta(seconds=diff)} ago')
        else:
            logging.error(f'{camera_capture.APP_NAME} is NOT running since {diff / 60} minutes')
            logging.info('Trying to sync code before rebooting')
            sync_all_files(camera_capture.read_config()['cloud'])

            run_command('sudo reboot', f'Rebooting to force restart of {camera_capture.APP_NAME}', thread=True)
    except:
        logging.error(sys.exc_info()[1], exc_info=sys.exc_info())


logging.info('+' * 80)
logging.info('Job IsAlive scheduled to run every 5 minutes')
schedule.every(5).minutes.do(isalive).run()

if __name__ == "__main__":
    while True:
        try:
            schedule.run_pending()
            sleep(1)
        except:
            logging.error(sys.exc_info()[1], exc_info=sys.exc_info())
