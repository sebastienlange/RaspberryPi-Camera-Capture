import logging
import subprocess
import sys
import threading


def run_command(command, message=None, thread=False, should_log=True):
    if message:
        logging.info(message)

    if thread:
        threading.Thread(target=lambda: do_run_command(command, should_log)).start()
    else:
        return do_run_command(command, should_log)


def do_run_command(command, should_log=True):
    result = subprocess.run(command, shell=True, text=True, capture_output=True)

    if should_log:
        for logs in [result.stdout, result.stderr]:
            for log, level in clean_logs(logs):
                logging.log(level, log)

    return result


def clean_logs(logs):
    for log in logs.strip().splitlines():
        if 'error' in log.lower():
            yield ''.join(log[log.lower().find('error') + len('error'):]).strip(': '), logging.ERROR
        else:
            yield log.strip(), logging.INFO


def sync_files():
    try:
        sync_logs_and_pictures()
        sync_app()
    except:
        logging.error(sys.exc_info()[1], exc_info=sys.exc_info())


def reboot(reason):
    run_command('sudo reboot', reason, thread=True)


def sync_app():
    should_reboot = False

    subprocess.run("git checkout HEAD -- camera_capture.json", shell=True)
    result = subprocess.run(f"git -C /home/pi/Documents/EnergySuD/RaspberryPi-Camera-Capture pull origin master",
                            shell=True, text=True, capture_output=True)
    for std in [result.stdout, result.stderr]:
        for log, level in clean_logs(std):
            if level != logging.INFO or '|' in log:
                app_changed = level == logging.INFO and '.py' in log
                if level == logging.INFO:
                    log = f'Syncing {log}' + (
                        ' => WILL REBOOT AFTER SYNC FILES...' if app_changed else '')
                logging.log(level, log)
                if app_changed:
                    should_reboot = True

    if should_reboot:
        reboot('Rebooting to take changes to code into account')


def sync_logs_and_pictures():
    for (src, dest) in [
        ('/home/pi/Pictures/EnergySuD', 'dropbox:EnergySuD/RaspberryPi/Pictures'),
        ('/var/log/EnergySuD', 'dropbox:EnergySuD/RaspberryPi/logs')
    ]:

        result = subprocess.run(f"rclone sync -v {src} {dest}".split(' '), text=True, capture_output=True)
        for std in [result.stdout, result.stderr]:
            for log, level in clean_rclone_log(std):
                log = f'Syncing {src}/{log} to {dest}'
                logging.log(level, log)


def clean_rclone_log(logs):
    logs = logs.strip()
    for log in logs.splitlines():
        if 'ERROR' in log:
            yield ''.join(log[log.find('ERROR') + len('ERROR'):]).strip(': '), logging.ERROR
        elif any(ext + ':' in log for ext in ['.jpg', '.py', '.json', '.log']):
            log = ' '.join([l.strip() for l in log.split(':')[-2:]])
            yield log, logging.INFO
