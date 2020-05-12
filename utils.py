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


def sync_dropbox(app_name_to_watch_for_reboot):
    threading.Thread(target=lambda: do_sync_dropbox(app_name_to_watch_for_reboot)).start()


def do_sync_dropbox(app_name_to_watch_for_reboot):
    try:

        should_reboot = False

        for (src, dest) in [
            # ('dropbox:EnergySuD/RaspberryPi/Python', '/home/pi/Documents/EnergySuD'),
            ('/home/pi/Pictures/EnergySuD', 'dropbox:EnergySuD/RaspberryPi/Pictures'),
            ('/var/log/EnergySuD', 'dropbox:EnergySuD/RaspberryPi/logs'), ]:

            result = subprocess.run(f"rclone sync -v {src} {dest}".split(' '), text=True, capture_output=True)
            for std in [result.stdout, result.stderr]:
                for log, level in clean_dropbox_log(std):
                    log = f'Syncing {src}/{log} to {dest}'
                    logging.log(level, log)

        result = subprocess.run(f"git -C /home/pi/Documents/EnergySuD/RaspberryPi-Camera-Capture pull origin master",
                                shell=True, text=True, capture_output=True)
        for std in [result.stdout, result.stderr]:
            for log, level in clean_logs(std):
                if level != logging.INFO or all(
                        msg not in log for msg in ['Déjà à jour', 'Depuis https://github.com', '* branch']):
                    app_changed = app_name_to_watch_for_reboot in log
                    log = f'{log}' + (
                        ' => WILL REBOOT AFTER DROPBOX SYNC...' if app_changed else '')
                    logging.log(level, log)
                    if app_changed:
                        should_reboot = True

        if should_reboot:
            run_command('sudo reboot', f'Rebooting to take changes to code into account', thread=True)

    except:
        logging.error(sys.exc_info()[1], exc_info=sys.exc_info())


def clean_dropbox_log(logs):
    logs = logs.strip()
    for log in logs.splitlines():
        if 'ERROR' in log:
            yield ''.join(log[log.find('ERROR') + len('ERROR'):]).strip(': '), logging.ERROR
        elif any(ext + ':' in log for ext in ['.jpg', '.py', '.json', '.log']):
            log = ' '.join([l.strip() for l in log.split(':')[-2:]])
            yield log, logging.INFO
