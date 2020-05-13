import logging
import subprocess
import sys
import threading


def run_command(command, message=None, ensure_log_written=False, should_log=True):
    if message is not None:
        logging.info(message)

    if ensure_log_written:
        threading.Thread(target=lambda: do_run_command(command, should_log=lambda x: should_log,
                                                       format_log=lambda x: x, should_reboot=lambda: False)).start()
    else:
        return do_run_command(command, should_log=lambda x: should_log, format_log=lambda x: x, should_reboot=lambda x: False)


def do_run_command(command, should_log, format_log, should_reboot, log_after=False):
    lines = []
    flag_reboot = False

    popen = subprocess.Popen(command, shell=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

    for log, level in clean_logs(popen, should_log, format_log):
        if should_reboot(log):
            flag_reboot = True
        lines.append((level, log))
        if not log_after:
            logging.log(level, log)

    popen.stdout.close()

    if log_after:
        for level, log in lines:
            logging.log(level, log)

    if flag_reboot:
        reboot('Rebooting to take changes to code into account')

    return lines


def sync_all_files(cloud_configs):
    try:
        for cloud_config in cloud_configs:
            src = cloud_config['src']
            destinations = cloud_config['dst']
            for d in (destinations if isinstance(destinations, list) else [destinations]):
                sync_files(src, d, log_after='log' in src)

        sync_app()
    except:
        logging.error(sys.exc_info()[1], exc_info=sys.exc_info())


def reboot(reason):
    run_command('sudo reboot', message=reason, ensure_log_written=True, should_log=False)


def sync_app():
    subprocess.run("git checkout HEAD -- camera_capture.json", shell=True)

    return do_run_command("git -C /home/pi/Documents/EnergySuD/RaspberryPi-Camera-Capture pull origin master",
                          should_log=lambda line: '|' in line,
                          format_log=lambda line: f'Syncing {line.strip()}',
                          should_reboot=lambda x: '.py' in x and 'tests/' not in x,
                          log_after=False)


def sync_files(src, dst, log_after=False):
    return do_run_command(f"rclone sync -v --retries 2 {src} {dst}",
                          should_log=lambda line: any(ext + ':' in line for ext in ['.jpg', '.py', '.json', '.log']),
                          format_log=lambda line: f'Syncing {src}/'
                                                  + ' '.join([sub_line.strip() for sub_line in line.split(':')[-2:]])
                                                  + f' to {dst}',
                          should_reboot=lambda x: False,
                          log_after=log_after)


def clean_logs(popen, should_log, format_log):
    for stdout_line in iter(popen.stdout.readline, ""):
        stdout_line = stdout_line.strip()
        if 'error' in stdout_line.lower():
            yield ''.join(stdout_line[stdout_line.lower().find('error') + len('error'):]).strip(
                ': '), logging.ERROR
        elif should_log(stdout_line):
            yield format_log(stdout_line), logging.INFO
