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
import pyotp

OTP_ENABLED = False  # Enable OTP security globally here
TOTP_SECRET_KEY = 'run otp-setup.py and add secret key value from otp-key.txt here'
totp = pyotp.TOTP(TOTP_SECRET_KEY)

RESTRICT_COMMANDS = False  # Limit the script to only allow a whitelist of keyword commands

MODEM = '/dev/ttyS0'  # Modem hardware device
MODEM_BAUD_RATE = 115200  # Modem port speed
MODEM_CHAR_ENCODING = 'iso-8859-1' # Character encoding scheme
MODEM_CHAR_SET = 'AT+CSCS="IRA"'  # Typically your modem manufacturer's default character set
MODEM_TXT_MODE_PARAM = 'AT+CSMP=17,167,0,0'  # Typically your modem manufacturer's default text mode parameters
MODEM_MSG_FORMAT = 'AT+CMGF=1' # Set the modem SMS mode to text or PDU format, typically =1 for text
MAX_SMS_LENGTH = 150  # Max characters in a single SMS. (Reduce if pages are skipped, GSM default is 160 minus pagination overhead)
MODEM_DELAY = 15 # Allow modem to initialise after reboot so one-time modem config commands are not given too early and fail.
PURGE_ON_START = False # False = process waiting commands sent while device was down/not ready. True = Don't run any waiting commands at script start
DEL_SMS_BATCH = 10  # Threshold of stored read messages to trigger batch delete. Check modem specs: Waveshare storage limit = 20
PURGE_SMS = 'AT+CMGD=1,4'  # Purge all SMS in modem storage
ACL = '+611234567890,+19876543210'  # Phone number white list. (See comments in ACL section to convert to a black list)
LOG_ROTATE_COUNT = 2 # How many security logs to keep in rotation before overwrite
CURRENT_DIR = '/root' # Default current shell directory path for the SMS user

LOG_FILE_NAME = 'sms-to-shell.log'  # Log file name
LOG_FILE_PATH = '/var/log/'  # Log file location. Consider the security context the script runs in to ensure write access
MAX_LOG_FILE_SIZE = 64 * 1024  # Maximum log file size in bytes (E.g. 64k = 64 * 1024) Keep it small for micro devices.

# USE ALL UPPERCASE FOR KEYWORD SHORTCUT VALUES! (Shortcuts are only case insensitive for the SMS sender!)
KEYWORD_PROCESS_LIST = 'PL'  # Send the cut down running process list
KEYWORD_PING = 'PING'  # Ping keyword shortcut'

KEYWORD_1 = 'K1'
KEYWORD_1_CMD = 'echo "Hello World!"'

KEYWORD_2 = 'K2'
KEYWORD_2_CMD = 'ps -aux' # careful as this returns a 100+ pages and may cost $$

KEYWORD_3 = 'K3'
KEYWORD_3_CMD = 'uname -a'

KEYWORD_4 = 'K4'
KEYWORD_4_CMD = 'uname -s'

KEYWORD_5 = 'K5'
KEYWORD_5_CMD = 'uname -m'

KEYWORD_6 = 'K6'
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


# Check if OTP authentication is enabled
def is_otp_enabled():
    return OTP_ENABLED


def switch_to_directory():
    # Change to the designated current directory
    os.chdir(CURRENT_DIR)


def send_sms_command(modem, phone_number, command):
    try:
        # Set sms text send mode
        modem.write(b'MODEM_MSG_FORMAT\r\n')
        modem.read_until(b'OK\r\n')

        # Send an SMS
        modem.write('AT+CMGS="{}"\r\n'.format(phone_number).encode(MODEM_CHAR_ENCODING))
        modem.read_until(b'> ')
        modem.write(command.encode(MODEM_CHAR_ENCODING))
        modem.write(bytes([26]))  # Ctrl+Z
        modem.read_until(b'+CMGS: ')
        response = modem.read_until(b'OK\r\n')

        # Check if the command was sent successfully
        sent_successfully = '+CMGS: ' in response.decode(MODEM_CHAR_ENCODING)

        time.sleep(0.5)  # Add a small delay between SMS messages

        return sent_successfully
    except Exception as e:
        # Log the error message
        logger.error('An error occurred while sending an SMS command: %s', str(e))
        return False



def execute_shell_command(command):
    # Run the SMS command in the shell
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
    # Split phone numbers from SMS command content
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
        # Send a process list formatted for SMS viewing
        command = 'ps -d -o pid,cmd --no-headers | awk \'!/^\[.*\]/{gsub(/[^a-zA-Z0-9_./-]/, "", $2); gsub(/\\x27/, "\\\\x27", $2); print $1, $2}\''
        output = execute_shell_command(command)

        # Check for empty error in output
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
        # Capture ping command errors up front
        if error_message:
            logger.error(error_message)  # Log the error message

        # Split ping output into multi page SMS reply
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
        command = f'kill -9 {pid} ; echo "exit status =" $?'
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
        logger.info('D: %s T: %s Ph: %s Command: %s',
                    time.strftime('%Y-%m-%d'), time.strftime('%H:%M:%S'), phone_number, content)

        # Check if the phone number is allowed
        if phone_number not in ACL: # make ACL a black list by reversing line to "if phone_number is in ACL:"
            # Phone number not allowed, send rejection message
            rejection_message = "Access denied"
            send_sms_command(modem, phone_number, rejection_message)
            logger.warning("D: %s T: %s UNAUTHORISED ACCESS ATTEMPT Ph: %s Command: %s",
                        time.strftime('%Y-%m-%d'), time.strftime('%H:%M:%S'), phone_number, content)
            return

        # If OTP is enabled, verify one-time password before proceeding
        if is_otp_enabled():
            try:
                # Split the content into OTP and the actual command
                otp, command = content.split(' ', 1)
            except ValueError:
                # Invalid format, send rejection message
                rejection_message = "Invalid format. Please provide OTP and command separated by a space."
                send_sms_command(modem, phone_number, rejection_message)
                logger.warning("Invalid format - Phone Number: %s - Command: %s", phone_number, content)
                return

            if not totp.verify(otp):
                # Invalid 2FA code, send rejection message
                rejection_message = "Invalid authentication code"
                send_sms_command(modem, phone_number, rejection_message)
                logger.warning("Invalid 2FA code - Phone Number: %s - Command: %s", phone_number, content)
                return

            # Remove the OTP from the message content
            content = command

        if content.strip().upper() == KEYWORD_PROCESS_LIST:
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

        # Execute unrestricted sms commands if RESTRICT_COMMANDS is False
        if not RESTRICT_COMMANDS:
            command = content + ' ; echo "exit status =" $?'
            output = execute_shell_command(command)
            build_sms_response(modem, phone_number, output)
            return

        # If the command is not recognised, send an error message
        error_message = "Command not allowed"
        send_sms_command(modem, phone_number, error_message)
        logger.warning("Illegal command - Phone Number: %s - Command: %s", phone_number, content)

    except Exception as e:
        # Handle any exceptions that occur during processing
        error_message = "An error occurred while processing the SMS."
        send_sms_command(modem, phone_number, error_message)
        logger.exception("Exception occurred - Phone Number: %s - Command: %s", phone_number, content)


def build_sms_response(modem, phone_number, command):
    try:
        # Paginate the SMS response
        pages = paginate_output(modem, command)
        num_pages = len(pages)

        for i, page in enumerate(pages):
            page_number = f"{i+1}/{num_pages}"
            message = page_number + ' ' + page
            send_sms_command(modem, phone_number, message)

    except Exception as e:
        # Log the error message
        logger.error('Failed to send SMS response: %s', str(e))



def paginate_output(modem, output):
    # Split longer SMS replies into multiple messages
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
        # Check for read SMS messages in modem memory
        modem.write(b'AT+CMGL="REC READ"\r\n')
        response = modem.read_until(b'OK\r\n')

        # Count the number of read SMS messages in modem memory
        messages = response.decode(MODEM_CHAR_ENCODING).split('+CMGL: ')[1:]
        num_read_sms = len(messages)

        # Delete all messages from modem memory if the batch delete threshold is reached
        if num_read_sms >= DEL_SMS_BATCH:
            purge_all_sms(modem)

    except Exception as e:
        # Log the error message
        logger.error('Failed to check read status of SMS message: %s', str(e))


def purge_all_sms(modem):
    try:
        # Function to purge all SMS messages from modem memory
        modem.write((PURGE_SMS + '\r\n').encode(MODEM_CHAR_ENCODING))
        modem.read_until(b'OK\r\n')
    except Exception as e:
        # Log the error message
        logger.error('Failed to purge all SMS messages: %s', str(e))
        return 'An error occurred while purging all SMS messages.'


def main():
    try:
        # One time commands:

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

            if PURGE_ON_START:
                purge_all_sms(modem)

        # Loop commands:
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