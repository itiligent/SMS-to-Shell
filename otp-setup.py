#!/usr/bin/python
######################################################################################################################
# Create a Secret Key for TIME BASED Authenticator App Setup
# David Harrop
# May 2023
#######################################################################################################################

import pyotp
import qrcode
from PIL import Image

# Generate a new secret key
secret_key = pyotp.random_base32(length=32)

# Create a TOTP object with the secret key
totp = pyotp.TOTP(secret_key)

# Generate the OTP (One-Time Password)
otp = totp.now()

# Display the OTP and secret key
#print("OTP:", otp)
print("Secret Key:", secret_key)

# Generate the otpauth URI
otp_uri = totp.provisioning_uri(name='SMS-to-Shell', issuer_name='Itiligent')

# Generate the QR code using a Python library like qrcode
qr_code = qrcode.QRCode()
qr_code.add_data(otp_uri)
qr_code.make()
qr_code_img = qr_code.make_image(fill='black', back_color='white')

# Save the QR code as an image file
qr_code_img.save('otp-qrcode.png')

# Save the key and OTP to a file
with open('otp-key.txt', 'w') as file:
#    file.write(f"OTP: {otp}\n")
    file.write(f"Secret Key: {secret_key}\n")

