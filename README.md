# Raspberry Pi SMS Remote Control Command Interface

Securely control your Raspberry Pi over SMS without the need for full-time internet access or a cloud API/subscription. This project supports optional QR coded TOTP authentication, shell command whitelisting, and phone number white/blacklist restrictions.

The main script script `sms-to-shell.py` provides a robust framework for interacting with a Linux shell remotely using SMS commands. It supports executing customisable predefined commands via SMS keyword shortcuts or complete shell commands in real time or where intermittent wake/sleep cycling is a requirement. For convenience, all keyword shortcuts are **_case insensitive_**, while direct SMS commands remain **_case sensitive_**.

After sending a command via SMS, incoming messages are converted into shell input, executed, and the resulting shell output is replayed back to the sender's phone number via SMS. All SMS command outputs exceeding the SMS message character limit will be paginated over multiple SMS messages/pages.

Achieve zero trust with optional TOTP authentication for every command interaction. For less stringent security use cases, phone number whitelisting and unrestricted shell commands are enabled by default. All SMS interactions are logged.

## Features

The script includes the following features:

- Flexible support for most modems across various character sets, languages, and text mode parameters.
- Management of modem storage limits & SMS message memory locations.
- Security logging, log rotation, and log size management.
- Efficient minimisation of repetitive serial command inputs for better latency and lower power consumption.
- Multiple layers of error handling and logging for increased stability.
- An installer bash script for configuring the main Python script as a systemd Linux service that runs at boot.

## Requirements

To use this script, you need the following:

- A very basic working knowledge of Bash and Python.
- A working mobile SIM card.
- A working modem (you are able to connect via `minicom -D /dev/tty[your modem device] -b 115200` and issue +AT commands).
- Raspbian or any other recent Debian-flavored Linux OS with the below dependencies installed.

## Setup Instructions

Follow these steps to set up the `sms-to-shell.py` script:

### 1. Install dependencies:
```
sudo apt update && sudo apt-get install minicom python3-pip 
sudo pip3 install pyserial qrcode pyotp --system
```
Alternatively, for simplified system updates the required dependencies may be packages available from your Linux distribution:
```
sudo apt update && sudo apt-get install minicom python3-serial python3-pyotp python3-qrcode
```

### 2. Copy or clone the following files to your Linux shell home directory:
- sms-to-shell.py
- sms-to-shell-setup.sh
- otp-setup.py

### 3. Minimum `sms-to-shell.py` re-configuration before first run:
While there are many user definable parameters labelled at the top of the main script, the included default settings are a stable and nonrestrictive starting point. By default unrestricted commands can be passed to the shell and only phone number whitelisting is enabled. For use cases where higher security or privacy is desired, see steps 4  & 7. Below are the **minimum** items you will need to customise to get up and running:

- Configure the script according to your modem device. Refer to your modem's documentation for discovering your modem's specific device path:
   - Serial modem e.g: `MODEM = '/dev/ttyS0'` or USB modem e.g: `MODEM = '/dev/ttyUSB2'`
   - Baud rate e.g: `MODEM_BAUD_RATE = '115200'`.
- Next, update the `CURRENT_DIR = ` to set the current directory context that incoming shell commands will assume.
- Verify that the log file path in `LOG_FILE_PATH = '/var/log/'` exists in your Linux distro, or adjust are required.
- Lastly add at least one trusted mobile phone number to the `ACL = ` section that you will be sending test SMS commands from.

### 4. Choose the appropriate SMS-to-Shell security level (Optional):
- You may further expand the `ACL = ` section to include several mobile phone numbers from which incoming commands will be permitted, with each phone number being separated by a comma. To allow ANY phone number to send commands, remove all trusted phone numbers from the ACL before converting it to a black list (refer to script comments for further instructions).
- To restrict SMS-to-Shell to only the keyword command whitelist, set `RESTRICT_COMMANDS = True`.
- For TOTP one-time password support, set `OTP_ENABLED = True`.
  - For TOTP authentication, you must also:

    - Run `python3 otp-setup.py` to generate secret key `otp-key.txt` and QR code `otp-qrcode.png` files.
    - Copy the secret key saved in `otp-key.text` to `TOTP_SECRET_KEY = 'xxxxxxxxxxxxxxxxxxxx'`.
    - Use the QR code image `otp-qrcode.png` to set up your preferred TOTP authenticator app.
  - *Note: Command whitelisting, TOTP, and phone number ACLs can be used together or separately.*

### 5. Manually test the script:
```
sudo python3 sms-to-shell.py
```
- Allow ample time for modem initialisation and script startup. (The default `MODEM_DELAY = 15` is necessary to allow the modem time to be up and ready to receive commands from the script. You may tune this for faster startup with your specific HW/SW recipe).
- To send SMS commands, use the following syntax:
  - If OTP is disabled: `keyword shortcut or full shell command`.
  - If OTP is enabled: `totp_passcode [space] keyword shortcut or full shell command`.
- Try the included test shortcuts `f1, f2, f3` etc. and follow the log with `tail -f /var/log/sms-to-shell.log`.
  - Debug information will be displayed in the terminal as SMS commands are received and processed.
  - If you have a serial modem that also supports USB (like some Pi hats), connect to the modem with mincom over USB while the script calls the serial modem interface (or vice versa). This will allow you to follow along with modem activity and manually query the modem with +AT commands as you test.
- Create and test your own keyword shortcuts, for example: `KEYWORD_1_CMD = 'your command or script to run'`.
  - IMPORTANT: Corresponding shortcut values must be set in UPPERCASE, e.g., `KEYWORD_1 = 'F1'` NOT `KEYWORD_1 = 'f1'`.

### 6. Install SMS-to-Shell as a systemd service that starts at boot:
- Make sure to stop any running instances of the test script.
- From your Linux home directory, run:
```
chmod +x sms-to-shell-setup.sh && sudo ./sms-to-shell-setup.sh
```
  - This installer script will copy the local test script with all your changes to `/opt/sms-to-shell/sms-to-shell.py` and create a new (enabled at boot) service unit file in `/lib/systemd/system/sms-to-shell.service`. The SMS-to-Shell service should now be up and running. 
  - Check service is running with `service sms-to-shell status`
  - Your installation is now complete!


### 7. Advanced security:

  - Security is about managing risk vs maintaining usability. The security levels attainable by this script are intend provide a balance that should suit most home automation or many standalone industrial use cases. For Enterprise or more sensitive/high impact deployments, any device that straddles WAN and LAN networks presents a means of bypassing existing security policy and countermeasures (via internal or external actors). There is also at least some potential for zero day or unpatched vulnerabilities within modem firmware that a very motivated attacker could theoretically target. In these situations, further risk mitigation steps to prevent lateral movement such as VLAN network isolation, running the SMS-to-Shell service script as a lower privileged user (change `SHELL_USER="root"` in `sms-to-shell-setup.sh`) , reduced Linux software footprint, automatic updates, firewalling & monitoring etc. should all be considered.


## Troubleshooting

This Python script has been tested and is very stable with the Waveshare (Simcom) 7600x on Raspberry Pi 4B running Raspbian Bullseye 64 Lite using en_AU.UTF-8 and en_US.UTF-8 system locales.

Here are some troubleshooting tips for common issues:

- Check the log for any error messages. Most issues will likely relate to the modem serial/USB interface or SMS character encoding.
  - Verify that the correct serial or USB device paths are set in the script.
    - `sudo systemctl disable sms-to-shell.service`, `sudo systemctl stop sms-to-shell.service` to test connect to the modem with `sudo minicom -D /dev/tty[the device set in the script]` (The service is resiliently configured to restart itself if just manually stopped)
      - In minicom, type `ATE1` and then `AT+COPS?`. If you get no response or minicom freezes, there is a modem connectivity or device path issue.
  - Garbled or hex characters visible in the log, SMS reply output, or in minicom indicate character set mismatch issues.
    - A. Use `AT+CSCS=?` to check the modem's supported character sets.
    - B. Search to your modem's documentation for the string `AT+CSMP` to learn about the modem's default text mode parameters.
    - C. Confirm the correct character set used by your country and carrier. Because the character and text mode parameters required by your modem for your specific language may not be the same as the modem's hardware defaults, the script sets all these on startup. The script's character encoding default is set to `iso-8859-1` as this is the standard used by HTML and should be well-supported in most English speaking countries. It works perfectly in AU so probably will be fine in CA, NZ, UK, USA and many others. Other languages or regions will likely require different values that your modem's documentation should cover.
    - D. Next start fresh and reset the modem to factory defaults (typically `ATZ` and `AT+CRESET`).
    - E. Configure the script with the modem settings confirmed in steps a, b, and c. These settings are configured in `MODEM_CHAR_SET =`, `MODEM_TXT_MODE_PARAM =`, and `MODEM_CHAR_ENCODING =` and then `sudo systemctl enable sms-to-shell.service`, `sudo systemctl start sms-to-shell.service`
    - F. If you're still experiencing issues, run `AT+CSCS?` , `AT+CSMP?` & `AT+CPMS?` to check the modem's current values after the SMS-to-Shell service has started.
      - If any above values do not match the values set in the script, try increasing `MODEM_DELAY =` to give the modem more time to be ready to accept config commands. Also check there are no zombie Python processes still running with a previous version of your script configuration.

For more modem troubleshooting ideas, refer to `modem-setup.txt` and the included AT command reference PDF document.

## Compatibility with other distros and hardware platforms

While there may be several more advanced ways to approach parts of this project, the functional dependencies have been kept as Python-native as possible to ensure compatibility with embedded platforms such as OpenWRT where non-native Python libraries may be too large to run or not readily available as packages. Also, testing has showed that various low cost IOT modems do not exhibit great stability with message queuing and multi threading applied (another reason to K.I.S.S.) Additionally, no Raspberry Pi specific modules are called within the script so it can remain portable across many Linux flavours on different x86/Arm hardware. A Windows version of this project that runs PowerShell commands over SMS would likely require only minor changes too. If anyone wants to branch or fork, feel free to do so!