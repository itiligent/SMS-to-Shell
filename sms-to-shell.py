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

# USER DEFINED SECURITY SETTINGS
OTP_ENABLED = False  # Enable OTP security globally here
TOTP_SECRET_KEY = 'run otp-setup.py and add secret key value from otp-key.txt here'
RESTRICT_COMMANDS = False  # Limit the script to only allow a whitelist of keyword commands
ACL = '+611234567890,+19876543210'  # Phone number white list. (See comments in ACL section to convert to a black list)

# USER DEFINED SCRIPT PARAMETERS
MODEM = '/dev/ttyS0'  # Modem hardware device
MODEM_BAUD_RATE = 115200  # Modem port speed
MODEM_CHAR_ENCODING = 'iso-8859-1' # Character encoding scheme
MODEM_CHAR_SET = 'AT+CSCS="IRA"'  # Typically your modem manufacturer's default character set
MODEM_TXT_MODE_PARAM = 'AT+CSMP=17,167,0,0'  # Typically your modem manufacturer's default text mode parameters
MODEM_MSG_FORMAT = 'AT+CMGF=1' # Set the modem SMS mode to text or PDU format, typically this is =1 for text
MAX_SMS_LENGTH = 150  # Max characters in a single SMS. (Reduce if pages are skipped, GSM default is 160 minus pagination overhead)
MODEM_DELAY = 15 # Give modem time to initialise after reboot so modem config commands are not given too early and fail.
PURGE_ALL_ON_START = False # False = process commands in memory or arrived while device was offline/not ready. True = Clean out all (read or unread) commands on startup
PURGE_ALL_SMS = 'AT+CMGD=1,4'  # Command to purge all SMS in modem storage (won't delete /bounced/not yet arrived )
PURGE_PROC_SMS= 'AT+CMGD=1,2'  # Command to purge "received read" or "stored sent" messages from modem storage.
DEL_SMS_BATCH = 10  # Threshold of stored read messages to trigger a batch delete. Check modem message storage capacity with AT+CPMS?
LOG_ROTATE_COUNT = 2 # How many security logs to keep in rotation before overwrite
CURRENT_DIR = '/root' # Default current directory path for the SMS interactive user
LOG_FILE_NAME = 'sms-to-shell.log'  # Log file name
LOG_FILE_PATH = '/var/log/'  # Log file location. Consider the account name the script runs under to ensure write access
MAX_LOG_FILE_SIZE = 64 * 1024  # Maximum log file size in bytes (E.g. 64k = 64 * 1024) Keep it small for micro devices.
CMD_PASS_MSG = 'OK'  # Feedback to append to successful commands
CMD_FAIL_MSG = 'Command failed' # Feedback to append to failed commands

# Static script parameters, don't change unless you know what you're doing
totp = pyotp.TOTP(TOTP_SECRET_KEY)
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

# USER DEFINED KEYWORD SHORTCUTS. USE ALL UPPERCASE FOR KEYWORD_# SHORTCUT VALUES! 
# Shortcuts are case insensitive for the SMS sender only!
# To add more keywords, extend both the global variables directly below and the keyword structure in the 'process_sms' section
KEYWORD_PROCESS_LIST = 'PL'  # Built-in command to send a running process list formatted for SMS
KEYWORD_PING = 'PING'  # Built-in command to test the network on check ping responses via sms'

KEYWORD_0 = 'F0'
KEYWORD_0_CMD = 'echo "Hello World!"'

KEYWORD_1 = 'F1'
KEYWORD_1_CMD = 'ls -l'

KEYWORD_2 = 'F2'
KEYWORD_2_CMD = 'touch filename.txt'

KEYWORD_3 = 'F3'
KEYWORD_3_CMD = 'cat ~/.ssh/authorized_keys'

KEYWORD_4 = 'F4'
KEYWORD_4_CMD = 'uname -r'

KEYWORD_5 = 'F5'
KEYWORD_5_CMD = 'uname -o'

KEYWORD_6 = 'F6'
KEYWORD_6_CMD = 'uname -a'

KEYWORD_7 = 'F7'
KEYWORD_7_CMD = 'uname -m'

KEYWORD_8 = 'F8'
KEYWORD_8_CMD = 'uname -v'

KEYWORD_9 = 'F9'
KEYWORD_9_CMD = 'uname -o'


############ START OF SCRIPT ACTIONS ############

# Check if OTP authentication is enabled
def is_otp_enabled():
    return OTP_ENABLED


def switch_to_directory():
    # Change to the designated current directory
    os.chdir(CURRENT_DIR)


def send_sms_response(modem, phone_number, command):
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

        # Add a small delay between SMS messages
        time.sleep(0.5)

        return sent_successfully
    except Exception as e:
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
        logger.error('An error occurred while executing the shell command: %s', str(e))
        return str(e)


def parse_sms(sms):
    try:
        lines = sms.splitlines()
        phone_number = lines[0].split(',')[2].strip('"')
        content = lines[1]
        return phone_number, content

    except IndexError as e:
        logger.error('An error occurred while parsing the SMS: %s', str(e))
        return None, None

    except ValueError as ve:
        logger.error('ValueError occurred while parsing the SMS: %s', str(ve))
        return None, None

    except Exception as e:
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
            send_sms_response(modem, phone_number, message)

    except Exception as e:
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
            send_sms_response(modem, phone_number, message)

    except Exception as e:
        error_message = f"Failed to send ping response: {str(e)}"
        logger.error(error_message)  # Log the error message


def kill_process(modem, phone_number, pid):
    try:
        # Execute the kill command with signal -9 and echo the exit status
        command = f'kill -9 {pid} ; echo "exit status =" $?'
        output = execute_shell_command(command)

        # Send the kill command output as SMS
        message = f"Kill output:\n{output}"
        send_sms_response(modem, phone_number, message)

    except Exception as e:
        error_message = f"Failed to kill process {process_id}: {str(e)}"
        logger.error(error_message)  # Log the error message


def process_sms(modem, sms):
    try:
        phone_number, content = parse_sms(sms)

        # Check if phone_number and content are not None
        if phone_number is None or content is None:
            raise ValueError("Failed to parse SMS")

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
            send_sms_response(modem, phone_number, rejection_message)
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
                send_sms_response(modem, phone_number, rejection_message)
                logger.warning("Invalid format - Phone Number: %s - Command: %s", phone_number, content)
                return

            if not totp.verify(otp):
                # Invalid 2FA code, send rejection message
                rejection_message = "Invalid authentication code"
                send_sms_response(modem, phone_number, rejection_message)
                logger.warning("Invalid 2FA code - Phone Number: %s - Command: %s", phone_number, content)
                return

            # Separate the OTP from the message content
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
        elif content.strip().upper() == KEYWORD_0:
            # Execute the KEYWORD_0 command
            command = KEYWORD_0_CMD + ' ; command_status=$? ; if [ $command_status -eq 0 ]; then echo "' + CMD_PASS_MSG + '"; else echo "' + CMD_FAIL_MSG + '"; fi'
            output = execute_shell_command(command)
            build_sms_response(modem, phone_number, output)
            return
        elif content.strip().upper() == KEYWORD_1:
            # Execute the KEYWORD_1 command
            command = KEYWORD_1_CMD + ' ; command_status=$? ; if [ $command_status -eq 0 ]; then echo "' + CMD_PASS_MSG + '"; else echo "' + CMD_FAIL_MSG + '"; fi'
            output = execute_shell_command(command)
            build_sms_response(modem, phone_number, output)
            return
        elif content.strip().upper() == KEYWORD_2:
            # Execute the KEYWORD_2 command
            command = KEYWORD_2_CMD + ' ; command_status=$? ; if [ $command_status -eq 0 ]; then echo "' + CMD_PASS_MSG + '"; else echo "' + CMD_FAIL_MSG + '"; fi'
            output = execute_shell_command(command)
            build_sms_response(modem, phone_number, output)
            return
        elif content.strip().upper() == KEYWORD_3:
            # Execute the KEYWORD_3 command
            command = KEYWORD_3_CMD + ' ; command_status=$? ; if [ $command_status -eq 0 ]; then echo "' + CMD_PASS_MSG + '"; else echo "' + CMD_FAIL_MSG + '"; fi'
            output = execute_shell_command(command)
            build_sms_response(modem, phone_number, output)
            return
        elif content.strip().upper() == KEYWORD_4:
            # Execute the KEYWORD_4 command
            command = KEYWORD_4_CMD + ' ; command_status=$? ; if [ $command_status -eq 0 ]; then echo "' + CMD_PASS_MSG + '"; else echo "' + CMD_FAIL_MSG + '"; fi'
            output = execute_shell_command(command)
            build_sms_response(modem, phone_number, output)
            return
        elif content.strip().upper() == KEYWORD_5:
            # Execute the KEYWORD_5 command
            command = KEYWORD_5_CMD + ' ; command_status=$? ; if [ $command_status -eq 0 ]; then echo "' + CMD_PASS_MSG + '"; else echo "' + CMD_FAIL_MSG + '"; fi'
            output = execute_shell_command(command)
            build_sms_response(modem, phone_number, output)
            return
        elif content.strip().upper() == KEYWORD_6:
            # Execute the KEYWORD_6 command
            command = KEYWORD_6_CMD + ' ; command_status=$? ; if [ $command_status -eq 0 ]; then echo "' + CMD_PASS_MSG + '"; else echo "' + CMD_FAIL_MSG + '"; fi'
            output = execute_shell_command(command)
            build_sms_response(modem, phone_number, output)
            return
        elif content.strip().upper() == KEYWORD_7:
            # Execute the KEYWORD_7 command
            command = KEYWORD_7_CMD + ' ; command_status=$? ; if [ $command_status -eq 0 ]; then echo "' + CMD_PASS_MSG + '"; else echo "' + CMD_FAIL_MSG + '"; fi'
            output = execute_shell_command(command)
            build_sms_response(modem, phone_number, output)
            return
        elif content.strip().upper() == KEYWORD_8:
            # Execute the KEYWORD_8 command
            command = KEYWORD_8_CMD + ' ; command_status=$? ; if [ $command_status -eq 0 ]; then echo "' + CMD_PASS_MSG + '"; else echo "' + CMD_FAIL_MSG + '"; fi'
            output = execute_shell_command(command)
            build_sms_response(modem, phone_number, output)
            return
        elif content.strip().upper() == KEYWORD_9:
            # Execute the KEYWORD_9 command
            command = KEYWORD_9_CMD + ' ; command_status=$? ; if [ $command_status -eq 0 ]; then echo "' + CMD_PASS_MSG + '"; else echo "' + CMD_FAIL_MSG + '"; fi'
            output = execute_shell_command(command)
            build_sms_response(modem, phone_number, output)
            return

        # Check if the command is a kill command
        kill_pattern = r'^KILL\s+(\d+)$'
        match = re.match(kill_pattern, content.strip().upper())
        if match:
            pid = match.group(1)
            kill_process(modem, phone_number, pid)
            return

        # Execution of any sms command is allowed if RESTRICT_COMMANDS is set to False
        if not RESTRICT_COMMANDS:
            command = content + ' ; command_status=$? ; if [ $command_status -eq 0 ]; then echo "' + CMD_PASS_MSG + '"; else echo "' + CMD_FAIL_MSG + '"; fi'
            output = execute_shell_command(command)
            build_sms_response(modem, phone_number, output)
            return

        # If any command is not allowed, send an warning message
        error_message = "Unauthorised command"
        send_sms_response(modem, phone_number, error_message)
        logger.warning("Unauthorised command - Phone Number: %s - Command: %s", phone_number, content)

    except ValueError as e:
        error_message = "An value error occurred while parsing the SMS."
        send_sms_response(modem, phone_number, error_message)
        logger.exception("ValueError while parsing the SMS- Phone Number: %s - Command: %s", phone_number, content)
        logger.error("Failed to parse SMS: %s", str(e))

    except Exception as e:
        error_message = "An exception occurred while processing the SMS."
        send_sms_response(modem, phone_number, error_message)
        logger.exception("Exception while processing SMS - Phone Number: %s - Command: %s", phone_number, content)
        logger.error("Exception occurred: %s", str(e))


def build_sms_response(modem, phone_number, output):
    try:
        # Paginate the SMS response
        pages = paginate_output(modem, output)
        num_pages = len(pages)

        # Provide more descriptive feedback for a keyword where it executed successfully but returned no output
        if num_pages == 0:
            confirmation_message = f"{CMD_PASS_MSG}, no output"
            send_sms_response(modem, phone_number, confirmation_message)
            return

        # Provide more descriptive feedback for an unrestricted command that executed successfully but returned no output (other than "OK")
        confirmation_message = pages[0]
        if confirmation_message.strip() == CMD_PASS_MSG and num_pages == 1:
            confirmation_message = f"{CMD_PASS_MSG}, no output"
            send_sms_response(modem, phone_number, confirmation_message)
            return

        # Calculate the total length of all pages
        total_length = sum(len(page) for page in pages)

        # Check if the paginated output can fit into one page, if so send directly without page numbering
        if total_length <= MAX_SMS_LENGTH:
            message = '\n'.join(pages)  # Combine all pages into one message
            send_sms_response(modem, phone_number, message)
            return

        # Send paginated response
        for i, page in enumerate(pages):
            page_number = f"{i+1}/{num_pages}"
            message = page_number + ' ' + page
            send_sms_response(modem, phone_number, message)

    except Exception as e:
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
        logger.error('Failed to check read status of SMS message: %s', str(e))


def delete_message(modem, message):
    try:
    # Delete messages individually outside of the purge function.
        message_index = message.split(',')[0]  # Extract the message index
        delete_command = f'AT+CMGD={message_index}\r\n'
        modem.write(delete_command.encode(MODEM_CHAR_ENCODING))

        modem.read_until(b'OK\r\n')
    except Exception as e:
        logger.error('An error occurred while deleting the message: %s', str(e))


def purge_proc_sms(modem):
    try:
        # Remove messages that are already read or processed and sent 
        modem.write((PURGE_PROC_SMS + '\r\n').encode(MODEM_CHAR_ENCODING))
        modem.read_until(b'OK\r\n')

    except Exception as e:
        # Log the error message
        logger.error('Failed to purge processed SMS messages: %s', str(e))
        return 'An error occurred while purging processed SMS messages.'


def purge_all_sms(modem):
    try:
        # A more efficient function to purge all SMS messages from modem memory rather than delete on every run.
        # Incoming messages that bounced due to storage being full wont be deleted and likely (eventually) arrive. 
        modem.write((PURGE_ALL_SMS + '\r\n').encode(MODEM_CHAR_ENCODING))
        modem.read_until(b'OK\r\n')

    except Exception as e:
        logger.error('Failed to purge all SMS messages: %s', str(e))
        return 'An error occurred while purging all SMS messages.'


def process_offline_messages(modem):
    try:
        # Check for unread messages in memory or sent while offline/arriving before modem is fully online
        modem.write(b'AT+CMGL="REC UNREAD"\r\n')
        response = modem.read_until(b'OK\r\n')
        time.sleep(0.1)

        # Parse and process each waiting message
        messages = response.decode(MODEM_CHAR_ENCODING).split('+CMGL: ')[1:]
        for message in messages:
            try:
                phone_number, content = parse_sms(message)
                process_sms(modem, message)
                time.sleep(0.5)
                # In case too many messages are sent while offline and modem memory fills and causes messages to bounce, messages processed at startup are immediately deleted. This is because the main loop that handles batched message purging will not run until the waiting message backlog is first cleared.
                delete_message(modem, message)
                time.sleep(1)

            except Exception as e:
                logger.error('An error occurred while parsing offline SMS message: %s', str(e))

    except Exception as e:
        logger.error('An error occurred while processing offline messages: %s', str(e))


def main():
    try:
        # Script modem startup & setup commands:

        # Switch to the desired current directory context
        switch_to_directory()

        # Add a delay before initialising the modem in case of reboot
        time.sleep(MODEM_DELAY)

        # Initialise the modem connection
        with serial.Serial(MODEM, MODEM_BAUD_RATE, timeout=1) as modem:
            time.sleep(0.1)
            modem.write(b'AT\r\n')
            modem.read_until(b'OK\r\n')
            time.sleep(0.1)

            # Set character set
            modem.write((MODEM_CHAR_SET + '\r\n').encode(MODEM_CHAR_ENCODING))
            modem.read_until(b'OK\r\n')
            time.sleep(0.1)

            # Set text mode parameters
            modem.write((MODEM_TXT_MODE_PARAM + '\r\n').encode(MODEM_CHAR_ENCODING))
            modem.read_until(b'OK\r\n')
            time.sleep(0.1)

            if PURGE_ALL_ON_START:
                # We may not want to have messages queue up while offline. Clean the slate on startup
                purge_all_sms(modem)
                time.sleep(0.5)
            else:
                # Housekeeping with modem memory to remove read and sent messages on startup
                purge_proc_sms(modem)
                time.sleep(0.5)

            # Process waiting messages
            process_offline_messages(modem)

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
                    time.sleep(0.5)

                # Check for read SMS messages to delete
                check_read_sms(modem)

                # Wait for a little before checking again
                time.sleep(1)

    except Exception as e:
        logger.error('An error occurred in the main function: %s', str(e))

if __name__ == '__main__':
    main()