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


def sync_all_files():
    try:
        for (src, dst) in [
            ('/home/pi/Pictures/EnergySuD', 'dropbox:EnergySuD/RaspberryPi/Pictures'),
            ('/home/pi/Pictures/EnergySuD', 'dox:EcoCityTools/Photos_compteur/Jean-Marie'),
            ('/var/log/EnergySuD', 'dropbox:EnergySuD/RaspberryPi/logs')
        ]:
            sync_files(src, dst)

        sync_app()
    except:
        logging.error(sys.exc_info()[1], exc_info=sys.exc_info())


def reboot(reason):
    run_command('sudo reboot', reason, thread=True)


def sync_app():
    should_reboot = False

    subprocess.run("git checkout HEAD -- camera_capture.json", shell=True)

    popen = subprocess.Popen(f"git -C /home/pi/Documents/EnergySuD/RaspberryPi-Camera-Capture pull origin master",
                             shell=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    for log, level in clean_logs(popen, lambda line: '|' in line, lambda line: line.strip()):
        app_changed = level == logging.INFO and '.py' in log and 'tests/' not in log
        if level == logging.INFO:
            log = f'Syncing {log}' + (
                ' => WILL REBOOT AFTER SYNC FILES...' if app_changed else '')
        logging.log(level, log)
        if app_changed:
            should_reboot = True

    if should_reboot:
        reboot('Rebooting to take changes to code into account')


def sync_files(src, dest, log_after=False):
    lines = []
    popen = subprocess.Popen(f"rclone sync -v --retries 2 {src} {dest}", shell=True, text=True,
                             stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    for log, level in clean_logs(popen, lambda line: any(ext + ':' in line for ext in ['.jpg', '.py', '.json', '.log']),
                                 lambda line: ' '.join([sub_line.strip() for sub_line in line.split(':')[-2:]])):
        log = f'Syncing {src}/{log} to {dest}' if level == logging.INFO else log
        if log_after:
            lines.append((level, log))
        else:
            logging.log(level, f'Syncing {src}/{log} to {dest}' if level == logging.INFO else log)

    popen.stdout.close()

    for level, log in lines:
        logging.log(level, log)


def clean_logs(popen, should_log, format_log):
    for stdout_line in iter(popen.stdout.readline, ""):
        stdout_line = stdout_line.strip()
        if 'error' in stdout_line.lower():
            yield ''.join(stdout_line[stdout_line.lower().find('error') + len('error'):]).strip(
                ': '), logging.ERROR
        elif should_log(stdout_line):
            yield format_log(stdout_line), logging.INFO
