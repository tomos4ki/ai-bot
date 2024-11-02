import logging

import time

# Set up the logging format
logging.basicConfig(format='%(asctime)s %(levelname)s: %(message)s', level=logging.INFO)

# Log a message

def log_message(message, x):#level=logging.INFO):
    level = ''
    if x == 1:
        level = logging.INFO
    elif x == 2:
        level = logging.WARNING
    else:
        level = logging.ERROR
    print("level is ",level)
    return logging.info(message, level)


def infinite_log(message, x):
    while True:
        log_message(message, x)
        time.sleep(2)

def log(message, x):
    if x == 1:
        level = logging.INFO
    elif x == 2:
        level = logging.WARNING
    else:
        level = logging.ERROR
    log_message(message, level)

if __name__ == '__main__':
    infinite_log("test", 2)
else:
    log()