# Raspberry Pi SMS Remote Control Command Interface

Securely control your Raspberry Pi over SMS without the need for full-time internet access or a cloud subscription. This project supports optional QR code TOTP authentication, shell command whitelisting, and phone number white/blacklist restrictions.

The main script script `sms-to-shell.py` provides a robust framework for controlling and interacting with a Linux shell remotely using SMS commands. It supports executing customisable predefined commands via SMS keyword shortcuts or complete shell commands, even where intermittent wake/sleep cycling is a requirement. For convenience, all keyword shortcuts are **_case insensitive_**, while direct SMS commands remain **_case sensitive_**.

After sending a command via SMS, incoming messages are converted into shell input, executed, and the resulting shell output is replayed back to the sender's phone number via SMS. All SMS command outputs exceeding the SMS message character limit will be paginated over multiple SMS messages/pages.

Achieve zero trust with optional TOTP authentication for every command interaction. For less stringent security use cases, phone number whitelisting and unrestricted shell commands are enabled by default. All SMS interactions are logged.

## Features

The script includes the following features:

- Flexible support for most modems across various character sets, languages, and text mode parameters.
- Management of modem internal message storage and a flexible approach towards message storage limits
- Security logging, log rotation, and log size management.
- Minimisation of unnecessary serial commands for better latency and lower power consumption
- Multiple layers of error handling and logging for increased stability.
- An installer bash script for adding the main Python script as a systemd Linux service to run at boot.

## Requirements

To use this script, you need the following:

- A working mobile SIM card.
- A working modem (you should be able to connect via `minicom -D /dev/[device] -b 115200` and issue +AT commands).
- A basic working knowledge of bash and Python.
- Raspbian or any other recent Debian-flavored Linux OS with the below dependencies installed.

## Setup Instructions

Follow these steps to set up the `sms-to-shell.py` script:

### 1. Install dependencies:
```
sudo apt update && sudo apt install minicom python3-pip 
sudo pip3 install pyserial qrcode pyotp --system
```
Alternatively, for simplified system updates check if the required dependencies are available from your Linux distribution:
```
sudo apt update && sudo apt install minicom python3-serial python3-pyotp python3-qrcode
```

### 2. Copy or clone the following files to your Linux shell home directory:
- sms-to-shell.py
- sms-to-shell-setup.sh
- otp-setup.py

### 3. Configure the main script `sms-to-shell.py`:
- Configure the script according to your modem device. Specifics may vary, so refer to your modem's documentation for instructions.
  - Example: `MODEM = '/dev/ttyS0'`, `MODEM = '/dev/ttyUSB2'`, and `MODEM_BAUD_RATE = '115200'`.
- Update the `CURRENT_DIR = ` to set the current directory context that incoming shell commands will assume.
- Verify that the log file path in `LOG_FILE_PATH = '/var/log/'` exists in your Linux distro.

### 4. Choose the appropriate SMS-to-Shell security level:
- Adjust the `ACL = ` section to include the phone number(s) from which incoming commands will be permitted.
  - *To allow ALL phone numbers, you can convert the ACL into a black list (refer to script comments for instructions).*
- To restrict SMS-to-Shell to a whitelist of pre-set keyword commands, set `RESTRICT_COMMANDS = True`.
- For TOTP (one-time password) support, set `OTP_ENABLED = True`.
  - For TOTP authentication, you must also

    - Run `python3 otp-setup.py` to generate the secret key `otp-key.txt` and the QR code `otp-qrcode.png` files.
    - Copy the secret key saved in `otp-key.text` to `TOTP_SECRET_KEY = 'xxxxxxxxxx'`.
    - Use the QR code image `otp-qrcode.png` to set up your preferred TOTP authenticator app.
  - *Note: Command whitelisting, TOTP, and phone number ACLs can be used together or separately.*

### 5. Manually test the script:
```
sudo python3 sms-to-shell.py
```
- Allow ample time for initialization.
- To send SMS commands, use the following syntax:
  - If OTP is enabled: `totp_passcode [space] keyword shortcut or shell command`.
  - If OTP is disabled: `keyword shortcut or shell command`.
- Send some preset test shortcuts such as the script presets `f0, f1, f2`, etc., and monitor the log with `tail -f /var/log/sms-to-shell.log`.
- Debug information will be displayed in the terminal as SMS commands are received.
- Now you are free to create your own keyword shortcuts, for example: `KEYWORD_1_CMD = 'your command to run'`.
  - IMPORTANT: Corresponding shortcut values must be set in UPPERCASE, e.g., `KEYWORD_1 = 'AAA'`.

### 6. Install SMS-to-Shell as a systemd service that starts at boot:
- From your Linux home directory, run:
```
chmod +x sms-to-shell-setup.sh && sudo ./sms-to-shell-setup.sh
```
  - This installer script will copy the script to `/opt/sms-to-shell/sms-to-shell.py` and create a new (enabled at boot) service unit file in `/lib/systemd/system/sms-to-shell.service`.
  - Advanced users may want to run the script as a specific user or account. If desired, inside `sms-to-shell-setup.sh`, change `SHELL_USER =` to the desired account name.
  - By keeping `SHELL_USER = 'root'`, the script should work universally. Changing this requires an understanding of the implications:
    - A lower privileged user may require additional `sudo` command inputs or other workarounds for other authentication prompts.
    - A lower privileged user typically can't write directly to `/var/log/`, so a different log path such as `/home/user` will be needed.

## Troubleshooting

This Python script has been tested and works reliably with the Waveshare (Simcom) 7600x on Raspberry Pi 4B with Raspbian Bullseye 64.

Here are some troubleshooting tips for common issues:

- Check the logs for any error messages. Most issues will likely relate to the modem serial/USB interface or SMS character encoding.
  - Verify that the correct serial or USB device paths are set in the script.
    - Test the modem with `sudo minicom -D /dev/tty[your device you set in the script]`.
    - In minicom, type `ATE1` and then `AT+COPS?`. If you get no response, there might be a modem connectivity or setup issue.
  - Garbled or hex characters visible in the log, SMS reply output, or in minicom indicate character set mismatch issues.
    - a. Use `AT+CSCS=?` to check the modem's supported character sets.
    - b. Search to your modem's documentation for `AT+CSMP` to learn about the modem's default text mode parameters.
    - c. Confirm the correct character set used by your country and carrier. Because these may not be the same as the modem defaults, the script takes care of this by setting the values needed on startup.


    - The character encoding is set to the current default of `iso-8859-1` because this is the standard character set of HTML and should be well-supported in most English speaking countries. It works perfectly in AU so probably will be fine in CA, NZ, UK, USA and many others. Other languages or regions may require a different value.
    - d. Reset the modem to factory defaults (typically `ATZ` and `AT+CRESET`).
    - e. Configure the script with the modem settings confirmed in steps a, b, and c. These settings are configured in `MODEM_CHAR_SET =`, `MODEM_TXT_MODE_PARAM =`, and `MODEM_CHAR_ENCODING =`.
    - f. If you're still experiencing issues, run `AT+CSCS?` and `AT+CSMP?` to check the modem's currently configured character set and text mode parameters. If these values do not match the settings you added/confirmed in the script in step c, try increasing `MODEM_DELAY =` to allow the modem more time to initialise at startup so it is ready to accept the script's modem setup commands when they are sent.

For more modem troubleshooting ideas, refer to `modem-setup.txt` and the included AT command reference PDF document.

## Compatibility with Other Distros and Platforms

While there may be several more efficient or advanced ways to approach parts of this project, the functional dependencies have been kept as Python-native as possible to ensure compatibility with other embedded distros and platforms such as OpenWRT, where non-native Python libraries may be too large to run or not readily available as packages.
A Windows version of this project that runs PowerShell commands over SMS would likely require only minor changes. If anyone wants to branch or fork, feel free to do so!