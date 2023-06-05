#!/usr/bin/python
######################################################################################################################
# Create 2FA Secret Key for Authentication App Setup
# David Harrop
# May 2023
#######################################################################################################################
# sudo apt-get install qrencode
import pyotp
import subprocess

# Generate a new secret key
secret_key = pyotp.random_base32()

# Create a TOTP object with the secret key
totp = pyotp.TOTP(secret_key)

# Generate the OTP (One-Time Password)
otp = totp.now()

# Display the OTP and secret key
print("OTP:", otp)
print("Secret Key:", secret_key)

# Generate the otpauth URI
otp_uri = totp.provisioning_uri(name='SMS-to-Shell', issuer_name='Itiligent')

# Generate the QR code using qrencode command-line tool
qr_code = subprocess.run(
    ['qrencode', '-t', 'UTF8', otp_uri],
    capture_output=True,
    text=True
)

# Display the QR code
print(qr_code.stdout)

# Save the key and OTP to a file
with open('secret-2fa-key.txt', 'w') as file:
    file.write(f"OTP: {otp}\n")
    file.write(f"Secret Key: {secret_key}\n")


#!/usr/bin/python
######################################################################################################################
# SMS command interface for OS shells with 2FA authentication
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
import pyotp  # Import pyotp library for TOTP authentication

# Add your 2FA secret key here
TOTP_SECRET_KEY = 'YOUR_SECRET_KEY'

# Rest of your script code...

# Define the logger object and other constants

# ...

# Create a TOTP object with the secret key
totp = pyotp.TOTP(TOTP_SECRET_KEY)

# ...

def process_sms(modem, sms):
    try:
        phone_number, content = parse_sms(sms)

        # Verify the 2FA authentication code
        if not totp.verify(content):
            # Invalid 2FA code, send rejection message
            rejection_message = "Invalid authentication code"
            send_sms_command(modem, phone_number, rejection_message)
            logger.warning("Invalid 2FA code - Phone Number: %s - Command: %s", phone_number, content)
            return

        # Rest of your existing code for processing SMS commands...
        
        # ...
        
    except Exception as e:
        # Log the error message
        logger.error('An error occurred in process_sms function: %s', str(e))

# ...

