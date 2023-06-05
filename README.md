
## Interactive SMS to OS shell command interface

#### This script provides a simple and robust way to control and interact with an OS shell remotely via SMS commands. It supports executing either customisable predefined commands via SMS keyword shortcuts, or sending shell commands directly. 

#### After sending a shell command via SMS, incoming messages are converted into shell input, executed and the resulting shell output is replayed back to the sender's phone number via SMS. All SMS command outputs above a configurable character limit will be paginated over multiple SMS messages/pages.

#### Built-in keyword commands are included for ping test "P", display of an abbreviated Linux process list "PL", and for killing a Linux process "KILL pid". Six extra blank keyword command templates are included to configure your own shortcuts.
For convenience, all keyword shortcuts are ***case insensitive*** whereas direct sms commands remain ***case sensitive***.

    Script further includes:
     Access control list (allowed phone numbers white list)
     Flexible support for a variety of modems with varied default character sets/languages/text mode parameters
     Flexible management of modem SMS message memory limits
     SMS command logging, log rotation, log size management
     Error handing and logging on all functions for stability 
     An installer bash script for installing the python script as a systemd Linux service

  	Requirements:
	An AT serial or USB modem with a functioning sim/carrier connection 
	A basic understanding of AT modem syntax, bash and python.
  	A recent Debian flavoured Linux OS with python3 and python pip installed 
   	
	
	Setup instructions:
		1. Install dependencies: sudo apt install minicom python3-pip and then sudo pip3 install pyserial
		2. Copy sms-to-shell.py and sms-to-shell-setup.sh to your home directory
		3. Customise the python script's variables for your phone numbers, hardware and use case.
		4. Make the setup script executable: chmod +x sms-to-shell.sh
		5. Run the setup script: sudo ./sms-to-shell.sh to setup the python script as a service (enabled at boot).
		6. Send a test message and check the log file, check phone for expected return output.

	Troubleshooting:
		Tested and working solidly with Waveshare (Simcom) 7600x on Rasberry Pi 4B / Raspian Bullseye 64. 
		Most issues will likely relate to the modem serial interface or SMS character encoding:
			* Check for correct serial or usb device paths being set in the script.
			   Test modem with sudo minicom -D /dev/tty[your device you set in the script] 
			   In minicom type ATE1 and then AT+COPS? If you get no response you have a modem issue
			* Garble or hex in the log, or weird sms return characters means character set issues
			   1. AT+CSCS=? gives the modem's supported character sets. Check this. 
			   2. Search modem docs for "AT+CSMP" to learn modem's default text mode parameters.
			   3. Stop the script and reset the modem to factory defaults (typically "ATZ" and "AT+CRESET")
			   4. Configure the script with the modem settings learned in 1 & 2
			   5. You may need to further research the correct encoding for the required character set
			      i.e. UCS2 needs utf-16 for Asian/Arabic languages, GSM needs utf-8 etc. 

			For more modem troubleshooting see modem-setup.txt & included AT command reference PDF.
	
	Future plans: Add a OTP or 2FA SMS challenge reply before each command to harden against potential phone number spoofing
		      Limit the script only to a white list of available commands
		      Multi-threading to make immediate parsing of cancel/break commands more feasible
