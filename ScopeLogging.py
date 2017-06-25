

#Load virtual environment 
#	(my packages are loaded in virtualenv, but I call python with sudo 
#	 in order to have full access to the USB device, this allows a sudo call to use the venv)
activate_this = '/home/graham/Envs/Physics2/bin/activate_this.py'
execfile(activate_this, dict(__file__=activate_this))


#Load packages
import time   						#for read/write delays
import numpy as np 					#for math
# import matplotlib.pyplot as plt 	#for graphics
import visa							#communications
# import pandas as pd 				#for data handling
import os 							#for some path handling
import sys
# import random
from RigolInstruments import RigolDG4162, RigolDG1032, RigolDG1032TMC, RigolDS1102

#Flags
verbose = True


def resourceManagerInit(useNIDrivers = True):
	'''
	Initializes and returns a pyvisa resource manager to connect to devices over USB, serial, and GPIB

	The default behaviour for pyvisa is to use NI VISA drivers, but these are not available on 64bit Linux
	
	Calling this function with useNIDrivers = False will attempt to use the pyvisa-py backend instead
	 of the NI drivers. This requires the packages 'pyvisa-py' and 'pyusb' to be installed
	'''

	# Find all available instruments'
	if useNIDrivers:
		rm = visa.ResourceManager()
	else:
		rm = visa.ResourceManager('@py')
	return rm

def getDG4162USBAddress(usb):
	'''
	From the list of USB devices 'usb' this function finds any that appear to be
	DG4162 generators, and returns the address
	'''

	# #Rigol DG4xxx Function Generators should have 'DG4' appear in their description, so search for this
	usb_as_strings = [str(s) for s in usb]
	dg4_loc = [n for n,s in enumerate(usb_as_strings) if 'DG4' in s]

	#Check if multiple matching instruments were found
	if len(dg4_loc) == 0:
		print("Trying to connect to a DG4162 function generator, but no function generator found in list of USB devices!")
	elif len(dg4_loc) > 1:
		print("\nMore than one 'DG4' device was found, the first one will be used!")

	dg4_address = usb[dg4_loc[0]]
	if verbose:
		print('\n \nUsing this DG4162 function generator:\n')
		print(dg4_address)
	return dg4_address

def getDG1032USBAddress(usb):
	'''
	From the list of USB devices 'usb' this function finds any that appear to be
	DG1032 generators, and returns the address
	'''
	# #Rigol DG1xxx Function Generators should have 'DG1' appear in their description, so search for this
	usb_as_strings = [str(s) for s in usb]
	dg1_loc = [n for n,s in enumerate(usb_as_strings) if 'DG1' in s]

	#Check if multiple matching instruments were found
	if len(dg1_loc) == 0:
		print("Trying to connect to a DG1032 function generator, but no function generator found in list of USB devices!")
	elif len(dg1_loc) > 1:
		print("\nMore than one 'DG1' device was found, the first one will be used!")

	dg1_address = usb[dg1_loc[0]]
	if verbose:
		print('\n \nUsing this DG1032 function generator:\n' + str(dg1_address))
	return dg1_address	


#-------------------------
#Connect to Instruments
#-------------------------


#Open folder for saving data
savefolder = '~/Python/Physics2/Data/11April2017/'
savefolder = os.path.expanduser(savefolder)
if not os.path.exists(savefolder):
	os.makedirs(savefolder)

# Basic script for connection and interface using the above functions

rm = resourceManagerInit(useNIDrivers = False)	#Initialize resource manager using pyvisa-py backend
try:
	ilist = rm.list_resources()					#Get a list of connected resources
except ValueError:
	print('\nTrouble reading the list of devices, maybe try rebooting the Rigol instruments.\n')
	sys.exit(-1)
usb = filter(lambda x: 'USB' in x, ilist)	#Filter out USB devices
if len(usb) == 0:
    print 'No USB devices found!', ilist
    sys.exit(-1)
else:
	if verbose:								#Print out the USB devices that were found
		print('\nFound the following USB Devices:\n')
		print(usb)

# Connect to USBTMC instruments
scope = RigolDS1102(useUSBTMC = True)
scope.verbose = True
saving = True

scope.setNumChannels(2)

scope.setAcqMode('RAW')
scope.setMemDepth('LONG')

# Connect to the DG4162 Function Generator
# addr = getDG4162USBAddress(usb)
# funcgen1 = RigolDG4162(rm, addr)


time.sleep(0.5)


#Simple Read and Plot
# ---------------------
# funcgen1.sendTrigger(1)
time.sleep(0.5)


waveData = scope.readWaveform(2)
print('Scope timebase is {0:.5f}s/div'.format(scope.tScale))
print('Scope offset is {0:.8f}s'.format(scope.tOffs))

scope.saveScopeData(waveData, 'RbDataSingleChannel.csv')
scope.plotScopeData(waveData)



# #Acquire Data in a Loop
# # #----------------------
# n_save = 100

# loop_acquisition = False
# if loop_acquisition:
# 	print("Using looped acquisition...\n")
# 	while True:
# 		# filename=raw_input("Type filename for saved data, or end to stop:\n")
# 		# if filename=="end": break
# 		# else:
# 		#Trigger the function generator and read the resulting trace on the scope
# 		# funcgen1.sendTrigger(2)
# 		# time.sleep(1)	#Wait for the experiment to complete and the scope trace to be fully recorded

# 		n_save = n_save + 1

# 		waveData = scope.readWaveform('BOTH')
# 		name = 'StillWarmingUp' + str(n_save) + '.csv'
# 		file = savefolder + name
# 		scope.saveScopeData(waveData, file)

# 		time.sleep(10)

# 			# scope.plotScopeData(waveData)
# else:
# 	print("Acquiring one trace...")
# 	filename = raw_input("Type filename for saved data:\n")
# 	#Trigger the function generator and read the resulting trace on the scope
# 	# funcgen1.sendTrigger(2)
# 	# time.sleep(1)	#Wait for the experiment to complete and the scope trace to be fully recorded

# 	waveData = scope.readWaveform('BOTH', stopping = False)

# 	scope.plotScopeData(waveData)
# 	if saving:
# 		name = filename + '.csv'
# 		file = savefolder + name
# 		scope.saveScopeData(waveData, file)



# Read temperature
#---------

# lakeshore = Lakeshore331()

# print(lakeshore.getTemp())





# #Connect to the DS1102 scope
# addr = '/dev/usbtmc0'
# scope = RigolDS1102()

# #Set frequency
# channel, freq, ampl = (1, 40e6, 0.5)
# funcgen1.setFrequency(channel, freq, ampl, 0.25, 90)  #rename to setSineWave!

# funcgen1.close()

#Connect to the LakeShore Temperure Controller




#----------------------
#Hiro's PumpProbe Cycle
#----------------------

#Connect to the DG1032 Function Generator
# addr = getDG1032USBAddress(usb)
# funcgen1 = RigolDG1032(rm, addr)

# funcgenAddr = '/dev/usbtmc0'
# funcgen1 = RigolDG1032TMC(path = funcgenAddr)

# print('Unlocking...')
# # funcgen1.unlock() #Unlock the front panel

# funcgen1.turnOff(1)
# funcgen1.turnOff(2)

# time.sleep(0.5)

# #Set Channel 1 to a special square wave appropriate for Pump/Probe/Off amplitude control
# #----------------------------------------------------------------------------
# highV = 1.0
# lowV = -0.1			#HighV > 0 and lowV < 0 required, for idle level to be ==0
# tPump = 5e-3
# tProbe = 1e-3
# tOff = 10e-3

# funcgen1.setPulse(1, highV, lowV, tPump+tProbe, tPump/(tPump+tProbe)*100, 0)
# idle = 16383.0*(abs(lowV)/(highV-lowV))	#calculate the idle level for 0V between bursts
# funcgen1.setNCycBurst(1, 1, 'INT', tPump+tProbe+tOff, 0, idle)

# #Set Channel 2 to a special ramp wave appropriate for Pump/Probe Frequency Modulation
# #------------------------------------------------------------------------------------
# dV = 1.25	#dV = 1.25 matches up really well with the FM imput of the DG4162 generator

# funcgen1.setRamp(2, tProbe, 1.25, 0, 0, 0.0)
# funcgen1.setNCycBurst(2, 1, 'EXT', tDelay = tPump, idleLevel = 16384.0/2.0)





# #-----------------------------------------------
# #Point-by-Point Generation of Arbitrary Waveform
# #-----------------------------------------------
# kHz = 1e3
# ms = 1e-3

# # t = np.arange(0,20*ms,1*ms)
# # V = (t/(20*ms))*5

# # funcgen1.setVolatilePoints(100,2)

# # funcgen1.ArbLimitsSet = True

# t = np.arange(0,10*ms,0.1*ms)
# V = -1.0*np.sin(2*np.pi*1*kHz*t)*np.exp(-t/(5*ms))

# data = funcgen1.getWaveformDetails(1)
# print('Query 1: Channel 1 after reboot')
# print(data)
# time.sleep(0.5)

# funcgen1.write(':SOUR1:APPL:DC')
# time.sleep(0.5)

# data = funcgen1.getWaveformDetails(1)
# print('Query 2: Channel 1 after setting CH1 to DC')
# print(data)
# time.sleep(0.5)

# data = funcgen1.getWaveformDetails(2)
# print('Query 3: Channel 2 after setting CH1 to DC')
# print(data)
# time.sleep(0.5)

# funcgen1.setArbitrary(1, samplerate = 10e3, ampl = 1, offs = 0.5)

# data = funcgen1.getWaveformDetails(1)
# print('Query 4: Channel 1 after setting CH1 to ARB')
# print(data)
# time.sleep(0.5)


# funcgen1.loadStoredVolatile(1)

# funcgen1.checkVolatile()

# funcgen1.loadVolatile(t,V, channel = 1)
# funcgen1.setArbitrary(2, samplerate = 10e3, ampl = 1, offs = 0)







# funcgen1.turnOn(1)
# # funcgen1.turnOn(2)

# time.sleep(0.5)

# funcgen1.close()

