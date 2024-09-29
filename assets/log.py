import logging

import time

# Set up the logging format
logging.basicConfig(format='%(asctime)s %(levelname)s: %(message)s', level=logging.INFO)

# Log a message


def log_message(message="hi", level = 1):#level=logging.INFO):
    logging.info(level, message)


def infinite_log():
    while True:
        log_message()
        time.sleep(0.05)

def log(message, x):
    if x == 1:
        level = logging.INFO
    elif x == 2:
        level = logging.WARNING
    else:
        level = logging.ERROR
    log_message(message, level)

if __name__ == '__main__':
    infinite_log()
else:
    log()