"""
Logs the error signal of the home built temperature controller.

Includes all important operations as function defs so that they can be imported by other functions
"""

import time
import random
import zmq
import datetime
import sys
from labjack import ljm
import numpy as np
from scipy.interpolate  import interp1d
import os

import argparse

def labjackInitialize():
	'''
	All the code to initialize the connection to the labjack.

	Searches for the first Labjack that is connected, initializes the connection,
		and returns a handle for communication
	'''

	# Open first found LabJack
	# Eventually we will have multiple labjacks open, so fix this
	handle = ljm.open(ljm.constants.dtANY, ljm.constants.ctANY, "ANY")

	info = ljm.getHandleInfo(handle)
	print("\nOpened a LabJack with Device type: %i, Connection type: %i,\n" \
		"Serial number: %i, IP address: %s, Port: %i,\nMax bytes per MB: %i" % \
		(info[0], info[1], info[2], ljm.numberToIP(info[3]), info[4], info[5]))

	return handle

def getVoltageConversion():
	'''
	Create a conversion function for the silicon thermometer in the cryostat

	Returns a function VtoT that takes voltages (V) as input and returns temperature (K)
	'''
	#interpolation for Voltage-Temperature conversion
	Temp, Voltage, Sens = np.loadtxt('/home/labuser/Desktop/Experiment Control/DT-600 Standard Curve Interpolation Table.txt', skiprows = 3, unpack = True)

	VtoT = interp1d(Voltage, Temp)

	return VtoT


def get_voltage(handle, channel="AIN0", navg=100):
	'''
	Uses the labjack connection, averages over several readings, and returns the measured voltage
	inputs:	'handle' 	- the handle for the labjack connection 
			'channel' 	- the channel to read
			'navg'		- the number of consecutive readings to average over
	'''
	return np.mean(np.array([ljm.eReadName(handle, channel) for i in range(navg)]))


counter = 0
if __name__ == '__main__':

	handle = labjackInitialize()
	VtoT = getVoltageConversion()

	done = False
	while not done:
		try:
			# average 10 times
   			voltage_mean1 = get_voltage(handle, "AIN0", 100)
			voltage_mean2 = get_voltage(handle, "AIN1", 100)
			#temp_mean = VtoT(voltage_mean)
			counter += 1
			if counter%5 == 0:
 				print(voltage_mean2 - voltage_mean1)
		except KeyboardInterrupt:
			ljm.close(handle)
			done = True


