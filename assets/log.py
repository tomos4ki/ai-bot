import logging
import time

# Set up the logging format
logging.basicConfig(format='%(asctime)s %(levelname)s: %(message)s', level=logging.INFO)

# Log a message with  the correct level and message type

def log_message(message, message_type):
    return True
#     if message_type == 1:
#         logging.info(f'Bot message : {message}')
#     elif message_type == 2:
#         logging.error(f'Error message : {message}')
#     elif message_type == 3:
#         logging.info(f'notification : {message}')
#     elif message_type == 4:
#         logging.info(f'reply message : {message}')
#     else :
#         logging.warning(f'Unknown message type : {message}')
#     print(logging)
#     return(logging)


# #infinite logging loop for demenstration
# def infinite_log(message, message_type):
#     while True:
#         log_message(message, message_type)
#         time.sleep(0.2)



# if __name__ == '__main__':
#     infinite_log("this is a test messae",3)

#log_message(message, type)
