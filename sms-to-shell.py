#!/usr/bin/python
######################################################################################################################
# SMS command interface for OS shells
# David Harrop
# May 2023
#######################################################################################################################

import serial
import time
import subprocess
import re
import logging
import os
import logging.handlers

MODEM = '/dev/ttyS0'  # Modem hardware device
MODEM_BAUD_RATE = 115200  # Modem port speed
MODEM_CHAR_ENCODING = 'iso-8859-1' # Character encoding scheme
MODEM_CHAR_SET = 'AT+CSCS="IRA"'  # Use your modem manufacturer's default character set
MODEM_TXT_MODE_PARAM = 'AT+CSMP=17,167,0,0'  # Use your modem manufacturer's default text mode parameters
MODEM_MSG_FORMAT = 'AT+CMGF=1' # Set the modem SMS mode to text or PDU format
MAX_SMS_LENGTH = 150  # Max characters in a single SMS. (Reduce if pages are skipped, GSM default is 160 minus pagination overhead)
MODEM_DELAY = 30 # Allow modem to initialise after reboot so critical one-time modem config commands are not missed.
DEL_SMS_BATCH = 10  # Batch delete read messages to reduce serial latency/loads/power use. Check modem docs for max storage figure.
PURGE_SMS = 'AT+CMGD=1,4'  # Purge all SMS in modem storage
ACL = '+611234567890,+19876543210'  # Phone number access control list
LOG_ROTATE_COUNT = 2 # How many full logs to keep in rotation before overwrite
CURRENT_DIR = '/root' # Default current directory path for SMS user

LOG_FILE_NAME = 'sms-to-shell.log'  # Log file name
LOG_FILE_PATH = '/var/log/'  # Log file location
MAX_LOG_FILE_SIZE = 64 * 1024  # Maximum log file size in bytes (E.g. 64k = 64 * 1024) Keep it small for micro devices.

# USE ALL UPPERCASE FOR KEYWORD SHORTCUT VALUES! (Shortcuts are only case insensitive for the sms sender! )
KEYWORD_PROCESS_LIST = 'PL'  # Send the cut down running process list
KEYWORD_PING = 'PING'  # Ping keyword shortcut'
KEYWORD_1 = 'K1' # User defined keyword shortcut
KEYWORD_1_CMD = 'echo "Hello World!"'
KEYWORD_2 = 'K2' # User defined keyword shortcut
KEYWORD_2_CMD = 'ps -aux'
KEYWORD_3 = 'K3' # User defined keyword shortcut
KEYWORD_3_CMD = 'uname -a'
KEYWORD_4 = 'K4' # User defined keyword shortcut
KEYWORD_4_CMD = 'uname -s'
KEYWORD_5 = 'K5' # User defined keyword shortcut
KEYWORD_5_CMD = 'uname -i'
KEYWORD_6 = 'K6' # User defined keyword shortcut
KEYWORD_6_CMD = 'uname -o'

# Define the logger object
logger = logging.getLogger()
logger.setLevel(logging.INFO)
# Configure log file handler for rotation
log_file = os.path.join(LOG_FILE_PATH, LOG_FILE_NAME)
file_handler = logging.handlers.RotatingFileHandler(log_file, maxBytes=MAX_LOG_FILE_SIZE, backupCount=LOG_ROTATE_COUNT)
# Create format for log messages
formatter = logging.Formatter('%(message)s')
# Apply format to log file handler
file_handler.setFormatter(formatter)
# Add log file handler to logger
logger.addHandler(file_handler)

def switch_to_directory():
    # Change to the home directory
    os.chdir(CURRENT_DIR)


def send_sms_command(modem, phone_number, message):
    try:
        # Set sms text send mode
        modem.write(b'MODEM_MSG_FORMAT\r\n')
        modem.read_until(b'OK\r\n')

        # Send SMS command
        modem.write('AT+CMGS="{}"\r\n'.format(phone_number).encode(MODEM_CHAR_ENCODING))
        modem.read_until(b'> ')
        modem.write(message.encode(MODEM_CHAR_ENCODING))
        modem.write(bytes([26]))  # Ctrl+Z
        modem.read_until(b'+CMGS: ')
        response = modem.read_until(b'OK\r\n')

        # Check if the command was sent successfully
        sent_successfully = '+CMGS: ' in response.decode(MODEM_CHAR_ENCODING)

        time.sleep(0.5)  # Add a small delay between sending SMS messages

        return sent_successfully
    except Exception as e:
        # Log the error message
        logger.error('An error occurred while sending an SMS command: %s', str(e))
        return False


def execute_shell_command(command):
    try:
        output = subprocess.check_output(command, shell=True, stderr=subprocess.STDOUT)
        return output.decode(MODEM_CHAR_ENCODING)
    except subprocess.CalledProcessError as e:
        # Log the error message
        logger.error('Command execution failed with error: %s', e.output.decode(MODEM_CHAR_ENCODING))
        return str(e.output.decode(MODEM_CHAR_ENCODING))
    except Exception as e:
        # Log the error message
        logger.error('An error occurred while executing the shell command: %s', str(e))
        return str(e)


def parse_sms(sms):
    try:
        lines = sms.splitlines()
        phone_number = lines[0].split(',')[2].strip('"')
        content = lines[1]
        return phone_number, content
    except Exception as e:
        # Log the error message
        logger.error('An error occurred while parsing the SMS: %s', str(e))
        return None, None


def send_process_list(modem, phone_number):
    try:
        command = 'ps -d -o pid,cmd --no-headers | awk \'!/^\[.*\]/{gsub(/[^a-zA-Z0-9_./-]/, "", $2); gsub(/\\x27/, "\\\\x27", $2); print $1, $2}\''
        output = execute_shell_command(command)

        # Check if the output is empty
        if not output:
            raise ValueError("Empty process list")

        # Paginate and send the process list as SMS
        pages = paginate_output(modem, output)
        num_pages = len(pages)

        for i, page in enumerate(pages):
            page_number = f"{i+1}/{num_pages}"
            message = page_number + ' ' + page
            send_sms_command(modem, phone_number, message)

    except Exception as e:
        # Log the error message
        logger.error('An error occurred in send_process_list function: %s', str(e))


def ping_host(target):
    try:
        # Execute the ping command with a limited number of pings
        command = f'ping -c 5 {target}'
        output = execute_shell_command(command)

        return output

    except subprocess.CalledProcessError as e:
        # Handle the specific error for ping command
        error_message = f"Ping command failed with return code {e.returncode}: {e.output.decode(MODEM_CHAR_ENCODING)}"
        logger.error(error_message)  # Log the error message
        return error_message

    except Exception as e:
        # Log the error message
        error_message = f"An error occurred while executing ping command: {str(e)}"
        logger.error(error_message)  # Log the error message
        return error_message


def send_ping_response(modem, phone_number, response, error_message=None):
    try:
        if error_message:
            logger.error(error_message)  # Log the error message

        # Paginate and send the ping response as SMS
        pages = paginate_output(modem, response)
        num_pages = len(pages)

        for i, page in enumerate(pages):
            page_number = f"{i+1}/{num_pages}"
            message = page_number + ' ' + page
            send_sms_command(modem, phone_number, message)

    except Exception as e:
        # Log the error message
        error_message = f"Failed to send ping response: {str(e)}"
        logger.error(error_message)  # Log the error message


def kill_process(modem, phone_number, pid):
    try:
        # Execute the kill command with signal -9 and echo the exit status
        command = f'kill -9 {pid} ; echo "command exit status =" $?'
        output = execute_shell_command(command)

        # Send the kill command output as SMS
        message = f"Kill output:\n{output}"
        send_sms_command(modem, phone_number, message)

    except Exception as e:
        # Log the error message
        error_message = f"Failed to kill process {process_id}: {str(e)}"
        logger.error(error_message)  # Log the error message


def process_sms(modem, sms):
    try:
        phone_number, content = parse_sms(sms)

        # Print debug information
        print("Received SMS:")
        print("Phone number:", phone_number)
        print("Command:", content)
        # Log the phone number, time, date, and command received
#        logger.info('Phone Number: %s, Time: %s, Date: %s, Command Received: %s',
#                    phone_number, time.strftime('%H:%M:%S'), time.strftime('%Y-%m-%d'), content)
        logger.info('D: %s T: %s Ph: %s Command: %s',
                    time.strftime('%Y-%m-%d'), time.strftime('%H:%M:%S'), phone_number, content)

        # Check if the phone number is allowed
        if phone_number not in ACL:
            # Phone number not allowed, send rejection message
            rejection_message = "Access denied"
            send_sms_command(modem, phone_number, rejection_message)
#            logger.warning("Unauthorised access attempt - Phone Number: %s - Unauthorised Command: %s", phone_number, content)
            logger.warning("D: %s T: %s UNAUTHORISED ACCESS ATTEMPT Ph: %s Command: %s",
                        time.strftime('%Y-%m-%d'), time.strftime('%H:%M:%S'), phone_number, content)
            return

        elif content.strip().upper() == KEYWORD_PROCESS_LIST:
            # Send process list
            send_process_list(modem, phone_number)
            return
        elif content.strip().upper().startswith(KEYWORD_PING):
            # Ping command
            ping_target = content.strip().split(' ')[1]
            ping_response = ping_host(ping_target)
            send_ping_response(modem, phone_number, ping_response)
            return
        elif content.strip().upper() == KEYWORD_1:
            # Execute the KEYWORD_1 command
            output = execute_shell_command(KEYWORD_1_CMD)
            build_sms_response(modem, phone_number, output)
            return
        elif content.strip().upper() == KEYWORD_2:
            # Execute the KEYWORD_2 command
            output = execute_shell_command(KEYWORD_2_CMD)
            build_sms_response(modem, phone_number, output)
            return
        elif content.strip().upper() == KEYWORD_3:
            # Execute the KEYWORD_3 command
            output = execute_shell_command(KEYWORD_3_CMD)
            build_sms_response(modem, phone_number, output)
            return
        elif content.strip().upper() == KEYWORD_4:
            # Execute the KEYWORD_4 command
            output = execute_shell_command(KEYWORD_4_CMD)
            build_sms_response(modem, phone_number, output)
            return
        elif content.strip().upper() == KEYWORD_5:
            # Execute the KEYWORD_5 command
            output = execute_shell_command(KEYWORD_5_CMD)
            build_sms_response(modem, phone_number, output)
            return
        elif content.strip().upper() == KEYWORD_6:
            # Execute the KEYWORD_6 command
            output = execute_shell_command(KEYWORD_6_CMD)
            build_sms_response(modem, phone_number, output)
            return

        # Check if the command is a kill command
        kill_pattern = r'^KILL\s+(\d+)$'
        match = re.match(kill_pattern, content.strip().upper())
        if match:
            pid = match.group(1)
            kill_process(modem, phone_number, pid)
            return

        # Execute the sms command in the shell
        command = content + ' ; echo "exit status =" $?'
        output = execute_shell_command(command)
        print("Command output:")
        print(output)

        # Send the command output as SMS
        build_sms_response(modem, phone_number, output)

        time.sleep(0.5)  # Delay to give the modem time to keep up

    except Exception as e:
        # Log the error message
        logger.error('An error occurred in process_sms function: %s', str(e))


def build_sms_response(modem, phone_number, response):
    try:
        # Paginate the SMS response
        pages = paginate_output(modem, response)  # Pass the 'modem' argument as well
        num_pages = len(pages)

        for i, page in enumerate(pages):
            page_number = f"{i+1}/{num_pages}"
            message = page_number + ' ' + page
            send_sms_command(modem, phone_number, message)

# Uncomment to log the successful SMS response
#        logger.info('SMS response sent to %s', phone_number)
    except Exception as e:
        # Log the error message
        logger.error('Failed to send SMS response: %s', str(e))


def paginate_output(modem, output):
    try:
        pages = []
        current_page = ''

        for line in output.splitlines():
            # Calculate remaining characters in current page
            remaining_chars = MAX_SMS_LENGTH - len(current_page)

            if len(line) <= remaining_chars:
                # Append line to current page
                current_page += line + '\n'
            else:
                # Line does not fit in current page, start new page
                pages.append(current_page.strip())
                current_page = line + '\n'

        if current_page:
            pages.append(current_page.strip())

        return pages

    except Exception as e:
        # Log the error message
        logger.error('Failed to paginate output: %s', str(e))
        return []  # Return an empty list in case of error


def check_read_sms(modem):
    try:
        # Check the number of read SMS messages in modem memory
        modem.write(b'AT+CMGL="REC READ"\r\n')
        response = modem.read_until(b'OK\r\n')

        # Count the number of read SMS messages
        messages = response.decode(MODEM_CHAR_ENCODING).split('+CMGL: ')[1:]
        num_read_sms = len(messages)

        if num_read_sms >= DEL_SMS_BATCH:
            purge_all_sms(modem)

    except Exception as e:
        # Log the error message
        logger.error('Failed to check read status of SMS message: %s', str(e))


# Unused but kept for syntax in some use cases where modem memory may be weird or where things might need to save to the sim card.
# This Function calls the current message ID in real time for deletion.
# SMS are now purged in batches with the catch all purge_all_sms function for greater responsiveness and lower power use.
#def delete_sms(modem, message):
#    try:
#        # Delete the current SMS message from modem memory
#        message_id = message.split(',')[0]
#        modem.write(f'AT+CMGD={message_id}\r\n'.encode(MODEM_CHAR_ENCODING))
#        modem.read_until(b'OK\r\n')
#    except Exception as e:
#        # Handle the exception by printing an error message
#        print(f"Failed to delete SMS: {str(e)}")


def purge_all_sms(modem):
    try:
        # Purge all SMS messages from modem memory
        modem.write((PURGE_SMS + '\r\n').encode(MODEM_CHAR_ENCODING))
        modem.read_until(b'OK\r\n')
    except Exception as e:
        # Log the error message
        logger.error('Failed to purge all SMS messages: %s', str(e))
        return 'An error occurred while purging all SMS messages.'


def main():
    try:

        # Switch to the desired current directory context
        switch_to_directory()

        # Add a delay before initialising the modem in case of reboot
        time.sleep(MODEM_DELAY)

        # Initialise the modem connection
        with serial.Serial(MODEM, MODEM_BAUD_RATE, timeout=1) as modem:
            time.sleep(1)
            modem.write(b'AT\r\n')
            modem.read_until(b'OK\r\n')
            time.sleep(1)

            # Set character set
            modem.write((MODEM_CHAR_SET + '\r\n').encode(MODEM_CHAR_ENCODING))
            modem.read_until(b'OK\r\n')
            time.sleep(1)

            # Set text mode parameters
            modem.write((MODEM_TXT_MODE_PARAM + '\r\n').encode(MODEM_CHAR_ENCODING))
            modem.read_until(b'OK\r\n')
            time.sleep(1)

            # Purge all SMS messages from modem memory on script start
            purge_all_sms(modem)

            # Main loop
            while True:
                # Check for new SMS messages
                modem.write(b'AT+CMGL="REC UNREAD"\r\n')
                response = modem.read_until(b'OK\r\n')
                time.sleep(0.1)

                # Parse and process each SMS message
                messages = response.decode(MODEM_CHAR_ENCODING).split('+CMGL: ')[1:]
                for message in messages:
                    phone_number, content = parse_sms(message)
                    process_sms(modem, message)
                    time.sleep(0.1)

                # Check for read SMS messages to delete
                check_read_sms(modem)

                # Wait for a little before checking again
                time.sleep(1)

    except Exception as e:
        # Log the error message
        logger.error('An error occurred in the main function: %s', str(e))

if __name__ == '__main__':
    main()