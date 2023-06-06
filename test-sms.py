#!/usr/bin/python

# This is mostly a copy of a rather clunky test script found in the labyrinth of Waveshare websites
# Set it to your phone number and run. GSM is likely used here this is the 
# most universal (but character limited) encoding scheme.
# It gives a small error at the end I've not bothered to debug but its good 
# just for ensuring that your modem is able to receive and send SMS.

import serial
import time

ser = serial.Serial("/dev/ttyS0", 115200)
ser.flushInput()

phone_number = '+611234567865'  # Updated phone number
text_message = 'test message from python!'
rec_buff = ''

def send_at(command, back, timeout):
    rec_buff = ''
    ser.write((command+'\r\n').encode())
    time.sleep(timeout)
    if ser.inWaiting():
        time.sleep(0.01)
        rec_buff = ser.read(ser.inWaiting())
    if back not in rec_buff.decode():
        print(command + ' ERROR')
        print(command + ' back:\t' + rec_buff.decode())
        return 0
    else:
        print(rec_buff.decode())
        return 1

def SendShortMessage(phone_number, text_message):
    print("Setting SMS mode...")
    send_at("AT+CMGF=1", "OK", 1)
    send_at("AT+CSMP=17,167,2,0", "OK", 1)  # Set coding for each message
    send_at("AT+CSCS=\"GSM\"", "OK", 1)  # Set character set for each message
    print("Sending Short Message")
    answer = send_at("AT+CMGS=\"" + phone_number + "\"", ">", 2)
    if 1 == answer:
        ser.write(text_message.encode())
        ser.write(b'\x1A')
        answer = send_at('', 'OK', 20)
        if 1 == answer:
            print('send successfully')
        else:
            print('error')
    else:
        print('error%d' % answer)

def ReceiveShortMessage():
    rec_buff = ''
    print('Setting SMS mode...')
    send_at('AT+CMGF=1', 'OK', 1)
    send_at('AT+CPMS=\"SM\",\"SM\",\"SM\"', 'OK', 1)
    answer = send_at('AT+CMGR=1', '+CMGR:', 2)
    if 1 == answer:
        answer = 0
        if 'OK' in rec_buff:
            answer = 1
            print(rec_buff)
    else:
        print('error%d' % answer)
        return False
    return True

try:
    print('Sending Short Message Test:')
    SendShortMessage(phone_number, text_message)
    print('Receive Short Message Test:\n')
    print('Please send a message to phone ' + phone_number)
    ReceiveShortMessage()
except:
    if ser != None:
        ser.close()
