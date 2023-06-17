# Raspberry Pi SMS remote control command interface 
### Securely control Raspi over SMS without full time internet access or cloud subscription. (Supports optional QRcode TOTP authentication, command whitelist & phone number white/black list restrictions)

This script provides a robust framework to control and interact with an OS shell remotely via SMS commands using only low power or intermittent networking. It supports executing either customisable predefined commands via SMS keyword shortcuts or sending shell commands directly. For convenience, all keyword shortcuts are **_case insensitive_**, whereas direct SMS commands remain **_case sensitive_**.

After sending a shell command via SMS, incoming messages are converted into shell input, executed, and the resulting shell output is replayed back to the sender's phone number via SMS. All SMS command outputs above a configurable character limit will be paginated over multiple SMS messages/pages.

Zero trust is achievable via optional TOTP authentication for every command interaction. For lower security use cases, phone number whitelisting and unrestricted shell commands are enabled by default. All SMS interactions are logged.

## Features

The script includes the following features:

- Flexible support most modems and carriers across various default character sets/languages/text mode parameters etc.
- Flexible management of modem SMS message storage limits
- Security logging, log rotation, and log size management
- Error handling and logging on all functions for stability
- An installer bash script for installing the Python script as a systemd Linux service

## Requirements

To use this script, you need the following:

- An working mobile SIM card 
- A WORKING modem (e.g. you can already connect with `minicom -D /dev/[device] -b 115200` and issue AT commands)
- A basic understanding of AT modem syntax, bash, and Python
- A recent Debian-flavored Linux OS with the above dependencies installed (A Windows adaption for running Powershell commands would need only minor changes )

## Setup Instructions

Follow these steps to set up the `sms-to-shell.py` script:

1. Install dependencies:
   ```
   sudo apt update && sudo apt install minicom python3-pip 
   sudo pip3 install pyserial qrcode pyotp
   ```
   Or for easier updating, dependencies from your Linux distro may be available:
   ```
   sudo apt update && sudo apt install minicom python3-serial python3-pyotp python3-qrcode
   ```

2. Copy the following files to your home directory:
   - sms-to-shell.py
   - sms-to-shell-setup.sh
   - otp-setup.py

3. `sms-to-shell.py` requires some configuration before running:
   - Set the modem device and baud rate
   - Adjust the ACL to your trusted phone numbers
   - Update the `CURRENT_DIR = ` to the preferred current directory path to base the script's operation.

4. Decide the appropriate SMS-to-Shell security level:
  - To restrict SMS-to-Shell to whitelisted keyword commands only, set `RESTRICT_COMMANDS = True`
  - For TOTP one time password support, set `OTP_ENABLED = True`
     - For TOTP authentication, you must also run `otp-setup.py` to generate the secret key `otp-key.txt` and qrcode `otp-qrcode.png` files.
     - Copy the secret key generated on screnn and saved to `otp-key.text` to `TOTP_SECRET_KEY = "xxxxxxxxxx"`
     - Use `otp-qrcode.png` or the secret key to set up your preferred authenticator app.

6. Manually test the script: `python3 sms-to-shell.py` 
   - Give it ample time to initialise - be patient. 
   - Debug info will show on screen as SMS commands are received
   - Watch the log with `tail -f /log/path/sms-to-shell.log`
   - Make your own keyword shortcuts
     - IMPORTANT: shortcut values must be set as UPPERCASE Eg. `KEYWORD_1 = 'AAA'`
   - To send commands, SMS shell command syntax is:
     - OTP enabled: `otp_password [space] command or keyword shortcut`
     - OTP disabled: `command or keyword shortcut`

7. Install SMS-to-Shell as a systemd service
   - Make `sms-to-shell-setup.sh` executable and run it: `chmod +x sms-to-shell.sh` and `sudo ./sms-to-shell.sh`
     - Script is installed to /opt/sms-to-shell/sms-to-shell.py and the service unit configuration file to /lib/systemd/system/sms-to-shell.service
     - Advanced users may want to run the script as a specific user. If so, adjust `sms-to-shell-setup.sh` to the desired value for `SHELL_USER='???'`. 
     - Using `SHELL_USER = 'root'` should work universally and changing this requires understanding the various implications:
       - A lower privileged user may require additional `sudo` command input overhead/back and forth.
       - A lower privileged user typically can't write to `/var/log/` therefore a log path such as `/home/user` will be needed.


## Troubleshooting

Script was tested and works solidly with Waveshare (Simcom) 7600x on Raspberry Pi 4B / Raspian Bullseye 64.

Here are some troubleshooting tips for common issues:

- Check logs for any error messages. Most issues will likely relate to the modem serial interface or SMS character encoding
   - Check for correct serial or USB device paths being set in the script
     - Test the modem with `sudo minicom -D /dev/tty[your device you set in the script]`
     - In minicom, type `ATE1` and then `AT+COPS?`. If you get no response, you have a modem connectivity or setup issue.
   - Garbled or hex characters visible in the log or in minicom indicates character set mismatch issues.
      - a. Use `AT+CSCS=?` to check the modem's supported character sets.
      - b. Search the modem documentation for "AT+CSMP" to learn about the modem's default text mode parameters.
      - c. Stop the script and reset the modem to factory defaults (typically "ATZ" and "AT+CRESET").
      - d. Configure the script with the modem settings learned in steps a and b.
      - e. You may need to further research the correct encoding for the required character set, e.g., UCS2 needs UTF-16 for Asian/Arabic languages, GSM needs UTF-8, etc.

For more modem troubleshooting, refer to `modem-setup.txt` and the included AT command reference PDF.