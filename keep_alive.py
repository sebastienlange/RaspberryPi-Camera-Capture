import camera_capture
import schedule
import sys
import os
import pathlib
import logging

from utils import run_command, sync_dropbox

from time import sleep
from datetime import datetime, timedelta


LOG_FILE = f'/var/log/EnergySuD/{pathlib.Path(__file__).stem}.log'

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
        log_file_dt = datetime.fromtimestamp(os.path.getmtime(camera_capture.LOG_FILE))
        diff = (datetime.today() - log_file_dt).total_seconds()
        
        if diff <= 16*60:
            logging.info(f'{camera_capture.APP_NAME} was running {timedelta(seconds=diff)} ago')
            temp = run_command('/opt/vc/bin/vcgencmd measure_temp', should_log=False)
            temp = temp.stdout.split('=')[1].strip()
            logging.info(f'Raspberry Pi core temperature is {temp}')
        else:
            logging.error(f'{camera_capture.APP_NAME} is NOT running since {diff/60} minutes')
            logging.info('Trying to sync code before rebooting')
            sync_dropbox(camera_capture.APP_NAME)
            
            run_command('sudo reboot', f'Rebooting to force restart of {camera_capture.APP_NAME}', thread=True)
    except:
        logging.error(sys.exc_info()[1], exc_info=sys.exc_info())

logging.info('+' * 80)
logging.info('Job IsAlive scheduled to run every 5 minutes')
schedule.every(5).minutes.do(isalive)

while True:
    try:
        schedule.run_pending()
        sleep(1)
    except:
        logging.error(sys.exc_info()[1], exc_info=sys.exc_info())