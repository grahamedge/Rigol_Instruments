'''
Wavemeter.py 

Condensed version of Shreyas' Wavemeter logger, to be opened as a class

Useful only for local reading of the wavelength, in order to tag data files,
 does not distribute frequency on the network for logging

Edited by: 	Graham Edge
Date:		May 5 2017
'''

import time
import serial
import random
import zmq
import datetime
import sys
 

wavemeterAddress = '/dev/ttyUSB0'
 
class WA1500:

    def __init__(self, address, baudrate=1200, timeout=2):

        self.timeout = timeout
        self.device = serial.Serial(address, baudrate=baudrate,
                                    timeout=self.timeout)
        self.device.flush()

    def read_frequency(self):
        self.device.write("@Q\r\n")
        self.device.flushInput()
        err_msg = 'ok'
        try:
            s = self.device.readline()
            print('Wavemeter Reading: %s' % s)
            self.device.flushOutput()
            if 'LO SIG' in s:
                err_msg = 'low signal'
                print(err_msg)
                frequency = -1.0
            elif 'HI SIG' in s:
                err_msg = 'high signal'
                print(err_msg)
                frequency = -1.0
            elif '~' in s:
                err_msg = 'possibly multimode'
                print(err_msg)
                frequency = float(s.split(',')[0][1:])
            else:
                frequency = float(s.split(',')[0])
        except KeyboardInterrupt:
            raise
        except:
            # write better error handling here
            frequency = -1.0
            err_msg = 'unknown error'
        return frequency, err_msg

    def close(self):
        self.device.close()
        if not self.device.isOpen():
            return "WA-1500 link closed"
        else:
            return "WA-1500 close error"

if __name__ == '__main__':

	done = False
	wavemeter_defined = False
	while not done:
		try:

		    wavemeter = WA1500(wavemeterAddress)

		    wavemeter_defined = True
		    while True:
		        freq, err_msg = wavemeter.read_frequency()
		        data_dict = {'freq': freq,
		                     'err_msg': err_msg}
		        time.sleep(0.5)
		except KeyboardInterrupt as e:
		    print "KeyboardInterrupt: exiting"
		    print wavemeter.close()
		    done = True
		except serial.serialutil.SerialException as e:
		    print "SerialException: ", e
		    if wavemeter_defined:
		        wavemeter.close()
		        wavemeter_defined = False
		    data_dict = {'freq': -1.0,
		                 'err_msg': 'SerialException'}
		    time.sleep(1.0)

