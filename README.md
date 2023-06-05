<h1 align="center">:iphone: Raspberry Pi SMS Remote Control Command Interface</h1>

<p align="center">
  <strong>DIRECTLY & SECURELY interact with Raspberry Pi via native SMS (no cloud APIs or subscriptions).</strong>
</p>
<p align="center">
  <img src="https://img.shields.io/badge/GitHub-GPL--3.0-informational.svg" alt="License">
</p>
<p align="center">
  <img src="https://github.com/iiiypuk/rpi-icon/blob/master/128.png" alt="Icon" width="100">
</p>

<p align="justify">
This project forms a robust framework for interacting with any Linux shell remotely using only SMS commands. It supports executing customisable predefined commands either via SMS keyword shortcuts, or through long form SMS shell commands. Commands can be processed in real time or will queue wherever intermittent wake/sleep cycling is a requirement. For convenience, all keyword shortcuts are case insensitive, while full SMS commands remain case sensitive.

After sending a command via SMS, incoming messages are converted into shell input, executed, and the resulting shell output is replayed back to the sender's phone number via SMS. All SMS command outputs exceeding the SMS message character limit will be paginated over multiple SMS messages/pages.

Zero trust is achievable with TOTP authentication optionally added to every command interaction. For less stringent security use cases, phone number whitelisting and unrestricted shell commands are enabled by default. All SMS interactions are logged.
</p> 

## :rocket: Features

- Flexible support for most modems across various character sets, languages, and text mode parameters.
- Management of modem storage limits & SMS message memory locations.
- Security logging, log rotation, and log size management.
- Efficient minimization of repetitive serial command inputs for better latency and lower power consumption.
- Multiple layers of error handling and logging for increased stability.
- An installer bash script for configuring the main SMS-to-Shell Python script as a Linux systemd service to start at boot.

## :white_check_mark: Requirements

To use this script, you need the following:

- A working mobile SIM card.
- A working modem (e.g. you are able to connect to it via `sudo minicom -D /dev/tty[your modem device]` and issue +AT commands).
- Raspbian or any other recent Debian-flavored Linux OS with the below dependencies installed.

## :wrench: Setup Instructions

Follow these steps to set up the `sms-to-shell.py` script:

### 1. Install dependencies:
```shell
sudo apt update && sudo apt-get install minicom python3-pip 
sudo pip3 install pyserial qrcode pyotp --system
```

Alternatively, the dependencies may be natively available from your Linux distro. If so this simplifies future updates:
```shell
sudo apt update && sudo apt-get install minicom python3-serial python3-pyotp python3-qrcode
```

### 2. Copy or clone the following files to your Linux shell home directory:
- `sms-to-shell.py`
- `sms-to-shell-setup.sh`
- `otp-setup.py`

### 3. Minimum `sms-to-shell.py` script re-configurations before first run:
While there are many user definable parameters labeled at the top of the main script, the included default settings are a stable and nonrestrictive starting point. By default, unrestricted commands can be passed to the shell, and only phone number whitelisting is enabled. For use cases where higher security is desired, see steps 4 & 7. Below are the **minimum** items you will need to customize to get up and running:

- Configure the script according to your modem device. Refer to your modem's documentation to find your modem's specific device path:
   - Serial modem e.g: `MODEM = '/dev/ttyS0'` or USB modem e.g: `MODEM = '/dev/ttyUSB2'`
   - Baud rate e.g: `MODEM_BAUD_RATE = '115200'`.
- Next, update the `CURRENT_DIR = ` to set the current directory context that incoming shell commands will assume.
- Verify that the log file path in `LOG_FILE_PATH = '/var/log/'` exists in your Linux distro or adjust as required.
- Lastly, add at least one trusted mobile phone number to the `ACL = ` section that you will be sending test SMS commands from.

### 4. Choose the appropriate SMS-to-Shell security level (Optional):
- You may further expand the `ACL = ` section to include several mobile phone numbers from which incoming commands will be permitted, with each phone number being separated by a comma. To allow ANY phone number to send commands, remove all trusted phone numbers from `ACL =` and instead convert this ACL to a blacklist (refer to script comments for specific instructions on how to make this simple change).
- To restrict SMS-to-Shell to only the keyword command whitelist, set `RESTRICT_COMMANDS = True`.
- For TOTP one-time password support, set `OTP_ENABLED = True`.
  - If TOTP is to be enabled you must also:

    - Run `python3 otp-setup.py` to generate secret key `otp-key.txt` and QR code `otp-qrcode.png` files.
    - Copy the secret key saved in `otp-key.text` to `TOTP_SECRET_KEY = 'xxxxxxxxxxxxxxxxxxxx'`.
    - Use the QR code image `otp-qrcode.png` to set up your preferred TOTP authenticator app.
  - *Note: Command whitelisting, TOTP, and phone number ACLs can be used together.*

### 5. Manually test the script:
```shell
sudo python3 sms-to-shell.py
```

- Allow ample time for modem initialization and script startup. (The default `MODEM_DELAY = 15` is necessary to allow the modem time to initialise and be ready to receive commands from the script. You may tune this for faster startup with your specific HW/SW recipe).
- **To send SMS commands, use the following syntax:**
  - **If OTP is disabled: `keyword shortcut or full shell command`**
  - **If OTP is enabled: `totp_passcode <space> keyword shortcut or full shell command`**
- Try the included test shortcuts `f1, f2, f3` etc. and follow the log with `tail -f /var/log/sms-to-shell.log`.
  - Debug information will be displayed in the terminal as SMS commands are received and processed.
  - If you have a serial modem that also supports USB (like some Pi hats), separately connect to the modem with Minicom over USB (e.g., /dev/ttyUSB2) while the script connects to the serial modem interface (e.g., /dev/ttyS0) or vice versa. This will allow you to use Minicom to view and follow modem activity and manually query the modem with +AT commands all whilst testing the running script with real SMS commands.
- Create and test your own keyword shortcuts, for example: `KEYWORD_1_CMD = 'your command or script to run'`.
  - IMPORTANT: Corresponding shortcut values must be set in UPPERCASE, e.g., `KEYWORD_1 = 'F1'` NOT `KEYWORD_1 = 'f1'`.

### 6. Install SMS-to-Shell as a systemd service that starts at boot:
- Make sure to stop any running instances of the test script.
- From your Linux home directory, run:
```shell
chmod +x sms-to-shell-setup.sh && sudo ./sms-to-shell-setup.sh
```
  - The above installer script will copy all your changes to `/opt/sms-to-shell/sms-to-shell.py` and create a new (enabled at boot) service unit file in `/lib/systemd/system/sms-to-shell.service`. Check the new service is running with `service sms-to-shell status`

### 7. Advanced security:

  - Security is about managing risk vs maintaining usability. The security levels attainable by this script are intended provide flexibiltiy for home automation though to industrial control use cases. Always be aware that any device that straddles a public network and a LAN presents a potential means of compromise or bypass of existing security policy and  countermeasures.
  -  If issuing of specific SMS commands is the only requirement, consider blocking the modem and LAN interfaces from all internet access.
  -  Another possibility is to run the SMS-to-Shell service as low privileged user (change `SHELL_USER="root"` in `sms-to-shell-setup.sh`).
  -  Other standard mitigations such as VLAN network isolation, a reduced Linux software footprint, automatic updates & monitoring should all be considered.

## Troubleshooting

This Python script has been tested and is very stable with the Waveshare (Simcom) 7600x on Raspberry Pi 4B running Raspbian Bullseye 64 Lite using en_AU.UTF-8 and en_US.UTF-8 system locales.

Here are some troubleshooting tips for common issues:

- Check the log for any error messages. Most issues will likely relate to the modem serial/USB interface or SMS character encoding.
  - Verify that the correct serial or USB device paths are set in the script.
    - `sudo systemctl disable sms-to-shell.service && sudo systemctl stop sms-to-shell.service`  (The service is configured to restart itself if only manually stopped).
    - Now test connect to the modem with `sudo minicom -D /dev/tty[the device set in the script]`
      - In Minicom, type `ATE1` and then `AT+COPS?`. If you get no response or Minicom freezes, there is a modem connectivity or device path issue.
  - Garbled or hex characters visible in the log, SMS reply output, or in Minicom indicate character set mismatch issues.
    - A. Use `AT+CSCS=?` to check the modem's supported character sets.
    - B. Search your modem's documentation for the string `AT+CSMP` to learn about the modem's default text mode parameters.
    - C. Confirm the correct character set used by your country and carrier. Because the character and text mode parameters required by your modem for your specific language may not be the same as the modem's hardware defaults, the script sets all these on startup. The script's character encoding default is set to `iso-8859-1` as this is the standard used by HTML and should be well-supported in most English speaking countries. Other languages or regions will likely require different values that your modem's documentation should cover.
    - D. Next start fresh and reset the modem to factory defaults (typically `ATZ` and `AT+CRESET`).
    - E. Configure the script with the modem settings confirmed in steps a, b, and c. These settings are configured in `MODEM_CHAR_SET =`, `MODEM_TXT_MODE_PARAM =`, and `MODEM_CHAR_ENCODING =` and then `sudo systemctl enable sms-to-shell.service && sudo systemctl start sms-to-shell.service`
    - F. If you're still experiencing issues, run `AT+CSCS?` , `AT+CSMP?` & `AT+CPMS?` to check the modem's current values after the SMS-to-Shell service has started.
      - If any above values do not match the values set in the script, try increasing `MODEM_DELAY =` to give the modem more time to be ready to accept config commands. Also check there are no zombie Python processes still running with a previous version of your script configuration.

For more modem troubleshooting ideas, refer to `modem-setup.txt` and the included AT command reference PDF document.
