#!/usr/bin/python
######################################################################################################################
# SMS test modem script
# David Harrop
# June 2023
#######################################################################################################################

import serial
import time

# Modem setup variables
MODEM = '/dev/ttyUSB2'  # Modem hardware device
MODEM_BAUD_RATE = 115200  # Modem port speed
MODEM_CHAR_ENCODING = 'iso-8859-1'  # May or may not be your modem manufacturer's default encoding scheme
MODEM_CHAR_SET = 'AT+CSCS="IRA"'  # May or may not be your modem manufacturer's default character set
MODEM_TXT_MODE_PARAM = 'AT+CSMP=17,167,0,0'  # Typically your modem manufacturer's default text mode parameters
MODEM_MSG_FORMAT = 'AT+CMGF=1'  # Set the modem SMS mode to text or PDU format, typically this is =1 for text

# Function to send AT command to modem and get response
def send_at_command(command):
    modem.write(command.encode(MODEM_CHAR_ENCODING) + b'\r')
    time.sleep(1)
    response = modem.read_all().decode(MODEM_CHAR_ENCODING)
    return response

# Initialise modem connection
modem = serial.Serial(MODEM, MODEM_BAUD_RATE, timeout=1)

# Send modem setup commands
send_at_command(MODEM_CHAR_SET)
send_at_command(MODEM_TXT_MODE_PARAM)
send_at_command(MODEM_MSG_FORMAT)

# Set recipient phone number and message content
recipient_number = '+61234567890'  # Replace with the actual recipient phone number
message_content = 'This is a test sms'

# Send SMS command
sms_command = 'AT+CMGS="{}"'.format(recipient_number)
send_at_command(sms_command)

# Send message content
modem.write(message_content.encode(MODEM_CHAR_ENCODING))
modem.write(bytes([26]))  # ASCII code for Ctrl+Z

# Wait for response
time.sleep(1)
response = modem.read_all().decode(MODEM_CHAR_ENCODING)

# Close modem connection
modem.close()

# Print response
print(response)

