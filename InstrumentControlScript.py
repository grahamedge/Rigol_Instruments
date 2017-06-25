

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
savefolder = '~/Python/Physics2/Data/05April2017/'
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



#Connect to USBTMC instruments
#-------------------------------
# scope = RigolDS1102(useUSBTMC = True)
# scope.verbose = True
# saving = True

# scope.setNumChannels(1)

# scope.setAcqMode('NORMAL')
# scope.setMemDepth('NORMAL')

# Connect to the DG4162 Function Generator
# addr = getDG4162USBAddress(usb)
# funcgen1 = RigolDG4162(rm, addr)


# time.sleep(0.5)


#Simple Read and Plot
#---------------------
# funcgen1.sendTrigger(1)
# time.sleep(0.5)

# waveData = scope.readWaveform(1)
# print('Scope timebase is {0:.5f}s/div'.format(scope.tScale))
# print('Scope offset is {0:.8f}s'.format(scope.tOffs))
# scope.plotScopeData(waveData)



# #Acquire Data in a Loop
# #----------------------
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

# 	waveData = scope.readWaveform(1)
# 	if saving:
# 		name = filename + '.csv'
# 		file = savefolder + name
# 		scope.saveScopeData(waveData, file)



# #Connect to the DS1102 scope
# addr = '/dev/usbtmc0'
# scope = RigolDS1102()


#----------------------
#Hiro's PumpProbe Cycle
#----------------------

#Connect to the DG1032 Function Generator
addr = getDG1032USBAddress(usb)
funcgen1 = RigolDG1032(rm, addr)

print('Unlocking...')
funcgen1.unlock() #Unlock the front panel

funcgen1.turnOff(1)
funcgen1.turnOff(2)

funcgen1.reset()

time.sleep(0.5)

#-----------------------------------------------
#Point-by-Point Generation of Arbitrary Waveform
#-----------------------------------------------
kHz = 1e3
ms = 1e-3

t = np.arange(0*ms,8*ms,0.02*ms)
V = 1.0*np.sin(2*np.pi*1*kHz*t)*np.exp(-t/(3*ms))

funcgen1.loadVolatile(t,V, channel = 1)

t = np.arange(-15*ms,0*ms,0.01*ms)
V = 1.0*np.sin(2*np.pi*3*kHz*t)*np.exp(t/(2*ms))

funcgen1.loadVolatile(t,V, channel = 2)


funcgen1.unlock()

funcgen1.turnOn(1)
funcgen1.turnOn(2)

funcgen1.close()

