# SMS-to-Shell architecture overview

#### The script and its variables sets up the modem connection using the serial python module to open the serial port to the modem.

#### The *"process_sms"* function 
is the engine room and handles most of the the logic for processing incoming SMS messages, executing commands, and sending appropriate responses based on the content of the messages. It takes two arguments: "modem" and "sms" (the content of the SMS message) and parses the SMS message to extract the phone number and content. It then checks if the phone number is allowed based on the access control list (ACL). If not listed it sends a rejection message and logs the unauthorised access attempt. If the originating phone number is in the ACL it checks the content of the SMS message for predefined keywords or commands. If the SMS content matches one of the predefined KEYWORD_X, it executes the corresponding command and sends the return output as one or multiple SMS messages. If OTP in enabled, this section is responsible for validating OTP. If SMS commands are limited to keywords, this section is also responsible for handing what commands are allowed vs blocked.   

#### The *"execute_shell_command"*
function facilitates the execution of shell commands and captures shell output or error messages for further processing.

#### The *"main" function*
enters an infinite loop to continuously check for incoming SMS messages. It reads the modem responses, checks if there are any unread messages, and processes each as they arrive. This section also sets up the one-time modem parameter settings.

#### The *"parse_sms" function*
extracts information from incoming SMS messages. It creates the parameter "message" to represent the content of SMS messages and returns a dictionary containing all the parsed information.

#### The *"build_sms_response"* 
function merges together the parameters of "modem", "phone_number" and "response" (which is the body of the return message) then sends this to the "send_SMS_command" via the "paginate_output" function for then final outgoing send.

#### The *"paginate_output"* function is responsible for splitting the output of a shell command into multiple pages of text, each fitting within the maximum length of an SMS message. 

#### The *"send_sms_response"* 
handles outgoing messages by instructing the modem to match outgoing SMS messages with their correct sender phone numbers. It then monitors outgoing SMS for successful message send.

#### The *"check_read_SMS"*
function keeps track of the number of read SMS messages in the modem memory and when a predefined count is reached, the purge_SMS function is called. Modems may have storage for < 20 messages so it is vital to manage this.

#### The *"purge_all_sms"* and *"purge_proc_sms"*
clears all or just the read and sent messages from the modem's memory.



