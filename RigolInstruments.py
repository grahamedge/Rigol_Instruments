"""RigolIntruments.py
~~~~~~~~~~~~~~

A collection of classes to perform simple interfaces with oscilloscopes,
function generators, and other instruments purchased from Rigol

Communication is performed with the use of the pyVISA package, which itself
requires either:
 - National Instruments VISA drivers
	(https://pyvisa.readthedocs.io/en/stable/getting_nivisa.html#getting-nivisa)
 - pyVISA-py, with PySerial and PyUSB
 	(https://pyvisa-py.readthedocs.io/en/latest/)


Graham Edge
March 27, 2017
"""

#Internal packages
import time
import os
import random

#External packages
import visa
import serial
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

#To Do
# - sort out arbitrary waveforms for the DG1032
# - sort out arbitrary waveforms for the DG4162
# - add more functions:
#		- send software trigger
#		- channel 1 = channel 2
#		- AM, FM, PM, Sweep Modulation
#		- set trigger parameters (rising/falling, INT/EXT/MAN)

#----------------------------------------------------------------------------------
# Some backend USBTMC classes
#----------------------------------------------------------------------------------
class usbtmc:
    """Simple implementation of a USBTMC device driver, in the style of visa.h"""
 
    def __init__(self, device):
        self.device = device
        self.FILE = os.open(device, os.O_RDWR)
 
        # TODO: Test that the file opened
 
    def write(self, command):
        os.write(self.FILE, command);
 
    def read(self, length = 4000):
        return os.read(self.FILE, length)

    def query(self, command, length = 4000):
    	self.write(command)
    	return self.read(length)
 
    def getName(self):
        self.write("*IDN?")
        return self.read(300)
 
    def sendReset(self):
        self.write("*RST")

    # def close(self):
    # 	#Do nothing    

#----------------------------------------------------------------------------------
# Classes for various Rigol Instruments
#----------------------------------------------------------------------------------        

class RigolDS1102(object):
	'''
	A class for computer control of the Rigol DS1102 dual channel oscilloscope

	Since there is a known issue with USB connectios on this instrument, it seems
		difficult to connect to the scope using the pyvisa-py backend

	Instead, pyvisa working with the National Instruments VISA backend seems to be OK

	On 64bit Linux where NI drivers are unavailable, connections can be made using
		USBTMC protocol directly rather than going through the VISA interface
	'''

	def __init__(self, resourceManager = [], address = '', useUSBTMC = False, path = '/dev/usbtmc0'):
		'''
		Establish communication with the instrument

		If using the resource manager, the address is a bytestream as returned by 
			pyvisa's list_resources() command

		If using USBTMC, then address is ignored and connection is made with 'path,
			the location of the usbtmc file as a string (e.g. '/dev/usbtmc0')	
		'''

		if useUSBTMC:
			#Using the USBTMC protocol for connection
			self.resource = usbtmc(path)
			try:
				self.name = self.resource.getName()
	 			print('\nSuccessfully connected via USBTMC to Rigol Scope:\n' + self.name)
	 		except:
	 			print('Unable to connect to Oscilloscope via USBTMC!')

	 		self.USBTMC = True	

		else:
			#Connect through the pyvisa resource manager
			self.resource = resourceManager.open_resource(address)
			try:
				self.idn = self.resource.query('*IDN?')
				print('\nSuccessfully connected to instrument:\n' + self.idn)
			except:
				print('Unable to connect to instrument!')

			#Define functions for reading and writing using PyVISA
			def write(self, command):
				self.resource.write(command)	
			def query(self, command):
				self.resource.query(command)

			self.USBTMC = False			#Should use this to redefine the read/write/query functions

		#Initialize other flags for the class
		self.verbose = False

	#Define commends for reading and writing over USBTMC
	def write(self, command):
		"""
		Send an arbitrary command directly to the scope
		"""
		self.resource.write(command)

	def read(self, nRead):
		"""Read an arbitrary amount of data directly from the scope"""
		return self.resource.read(nRead)

	def query(self, command, nRead = 100):
		'''A query command to write, and subsequently read specified number of bits'''    
		self.write(command)
		return self.read(int(nRead))

	def reset(self):
		"""Reset the instrument"""
		self.resource.sendReset	


	def close(self):
		'''
		Close the VISA session
		'''
		self.resource.close()


	#Reading scope settings
	#-------------------------------
	def getVScale(self, channel):
		'''Get the voltagescale of the selected channel, returned in Volts'''
		command = ":CHAN" + str(channel) + ":SCAL?"
		scale = float(self.query(command))
		time.sleep(0.1)
		return scale
		
	def getVOffset(self, channel):
		'''Get the offset voltage of the given channel'''
		command = ":CHAN" + str(channel) + ":OFFS?"
		offset = float(self.query(command))
		time.sleep(0.1)
		return offset

	def getTScale(self):
		'''
		Updates the time/div scale of the oscilloscope
		in the parameter self.tScale
		'''
		command = ":TIM:SCAL?"
		self.tScale = float(self.query(command))
		time.sleep(0.1)

	def getTOffset(self):
		'''Get the offset time of the scope'''
		command = ":TIM:OFFS?"
		self.tOffs = float(self.query(command))
		time.sleep(0.1)
		return self.tOffs

	def getMemDepth(self):
		'''
		Determine the memory depth of the oscilloscope
			Will return a string matching either NORMAL or LONG

		LONG memory depth is only relevant if acquisition mode is RAW	
		'''
		command = ":ACQ:MEMDEPTH?"
		self.memDepth = self.query(command)
		time.sleep(0.1)
		return self.memDepth

	def getAcqMode(self):
		'''
		Determine the acquisition mode of the oscilloscope
			Will return a string matching either NORM or RAW

		In NORM acquisition mode, the memory depth setting is ignored and
			600 data points are returned
		In RAW acquisition mode, the number of points returned depends on the
			Memory Depth setting, as well as the number of active channels.
			More data can be acquired if only one channel is active.
		'''
		command = ":WAV:POINTS:MODE?"
		self.acqMode = self.query(command)
		time.sleep(0.1)
		return self.acqMode	
		
	def getNPoints(self):
		'''Determine the number of datapoints that will be read by the scope'''

		dataPointSwitch = [self.getAcqMode(), self.getMemDepth(), self.nChannels]
		time.sleep(0.1)

		if dataPointSwitch[0] == 'NORMAL':
			#600 points, plus 10 for the header
			nPoints = 600 + 10
		elif dataPointSwitch[1:3] == ['NORMAL', 2]:
			nPoints = 8192+10
		elif dataPointSwitch[1:3] == ['NORMAL', 1]:
			nPoints = 16384 + 10
		elif dataPointSwitch[1:3] == ['LONG', 2]:
			nPoints = 524288 + 10
		elif dataPointSwitch[1:3] == ['LONG', 1]:
			nPoints = 1048576 + 10	

		self.nPoints = nPoints
		
	def getNumChannels(self, nChannels):
		'''Choose a number of active channels (1 or 2) to use on the scope'''
		command = ":CHAN1:DISP?"
		ch1 = self.query(command)
		command = ":CHAN1:DISP?"
		ch2 = self.query(command)

		if ch1 == 'ON' and ch2 == 'ON':
			self.nChannels = 2
		elif ch1 == 'OFF' and ch2 == 'OFF':
			self.nChannels = 0
		else:
			self.nChannels = 1

		return self.nChannels

	#Helpful printed output
	#-------------------------------
	def setVerbose(self):
		'''Enable lots of printouts'''
		self.verbose = True

	def printReadoutInfo(self):
		'''
		By checking the memory depth and the acquisition mode, this prints to
		the screen a message to inform the user of the number of points to expect
		as well a warning about long readout times.
		'''
		self.acqMode = self.getAcqMode()
		self.memDepth = self.getMemDepth()

		if self.acqMode == 'RAW':
			if self.memDepth == 'NORMAL':
				print('Using normal memory depth')
			elif self.memDepth == 'LONG':
				print("Using long memory depth (will take several seconds for readout).")
		else:
			print('Acquisition mode is normal, 600 points will be collected')



	#Configuring the scope
	#-------------------------------
	def setNumChannels(self, nChannels):
		'''Choose a number of active channels (1 or 2) to use on the scope'''
		self.nChannels = int(nChannels)
		if int(nChannels) == 2:
			self.write(':CHAN1:DISP ON')
			self.write(':CHAN2:DISP ON')
		else:
			self.write(":CHAN1:DISP ON")
			self.write(":CHAN2:DISP OFF")

	def setAcqMode(self, acqMode):
		'''Set the acquisition mode, to either acqMode = NORMAL or RAW'''
		command = ':WAV:POIN:MODE ' + acqMode
		self.write(command)
		time.sleep(0.1)

	def setMemDepth(self, memDepth):
		'''Set the memory depth, to either memDepth = NORMAL or LONG'''
		command = ':ACQ:MEMD ' + memDepth
		self.write(command)
		time.sleep(0.1)

	def setVScale(self, channel, scale):
		'''Set the voltage scale of a selected channel, in Volts'''
		command = ':CHAN' + str(channel) + ':SCALE ' + str(scale)
		self.write(command)
		time.sleep(0.1)
		
	def setProbe(self, channel, probe):
		'''Set the channel probe scale (X), to 1, 10, or 100'''
		command = ':CHAN' + str(channel) + ':PROB ' + probe
		self.write(command)
		time.sleep(0.1)

	def setTimeScale(self, scale):
		'''Set the time/dev in seconds'''
		command = ':TIMEBASE:SCALE ' + scale
		self.write(command)
		time.sleep(0.1)


	def setTimeOffs(self, offs):
		'''Set the time offset for the trigger'''
		command = ':TIMEBASE:OFFS ' + offs
		self.write(command)

	def setTrig(self, trigSource, sweepMode):
		'''
		Configure the scope to edge trigger mode
		by setting the source with trigSourcr = MAN, EXT, or INT
		and the number of sweeps with sweepMode = AUTO, NORM, SING

		Arguments passed as strings, case is irrelevant
		'''
		command = 'TRIG:MODE: EDGE' # set edge trigger mode
		self.write(command)
		time.sleep(0.1)
		command = ':TRIG:EDGE:SOUR ' + trigSource
		self.write(command)
		time.sleep(0.1)
		command = ':TRIG:EDGE:SWEEP ' + sweepMode
		self.write(command)
		time.sleep(0.1)


	#Reading data from the scope
	#-------------------------------
	def triggerScope(self):
		'''Send a software trigger to the scope'''
		self.write(':FORCETRIG')

	def readTrace(self, channel):
		'''Read the data from the specified channel'''
		command = ':WAV:DATA? CHAN' + str(channel)
		self.write(command)		#read waveform data
		time.sleep(0.2)
		rawdata = self.resource.read(self.nPoints)
		data = np.frombuffer(rawdata, 'B')[10:]				#disregard first 10 bits

		if self.verbose:
			print('Read ' + str(len(data)) + ' data points from Channel ' + str(channel) + '.\n')

		return data	

	def rescaleToVolts(self, data, channel):
		'''Rescale the waveform data read from the scope into units of Volts'''
		Voffs = self.getVOffset(channel)
		Vscale = self.getVScale(channel)
		Vdata = ( (np.asarray(data) * -1 + 255) - 130.0 - Voffs/Vscale*25) / 25 * Vscale
		return Vdata

	def readWaveform(self, channel, stopping = True):
		'''
		Read in the appropriate number of points from the specified channel
		which can be 1, 2, or 'BOTH 

		Returns waveData, a numpy array with columns of:
			-  [t(s), selectedChannel(V)]  for channel = 1, 2
			-  [t(s), CH1(V), CH2(V)]  	   for channel = 'BOTH'
		'''

		#Read in the time data
		tData = self.getTimeVec()

		channel = str(channel)

		if channel.upper() == 'BOTH':
			#Acquire from both channels, starting with channel 1
			channel = 1
			bothChannels = True
		else:
			bothChannels = False
			channel = int(channel)

		if self.nPoints > 610:
			#For RAW data acquisition, scope must be stopped
			if stopping:
				self.write(":STOP")
				time.sleep(0.2)

		if self.verbose:
			print('\nAttempting to read ' + str(self.nPoints) + ' bytes from CH1...\n')
		data = self.readTrace(channel)		

		if bothChannels: data2 = self.readTrace(2)

		if self.nPoints > 610:
			#Need to restart the scope
			self.write(":RUN")	

		#Scale the data to units of Volts, and package with time in a column numpy array
		Vdata = self.rescaleToVolts(data, channel)

		if bothChannels: 
			Vdata2 = self.rescaleToVolts(data2, 2)
			waveData = np.column_stack((tData, Vdata, Vdata2))
		else:
			waveData = np.column_stack((tData, Vdata))

		return waveData

	def getNDevs(self):
		'''
		Based on the acquisition mode and the time/dev, get the right number 
			of devs represented in the acquired data
		'''

		#Number of devs represented in waveform depends on the time/dev setting, 
		# 	acquisition mode, memory depth, and number of channels!
		self.getTScale()	#update the time/dev
		tDev = self.tScale
		mode = self.getAcqMode()
		depth = self.getMemDepth()
		nChan = self.nChannels

		useDict = True
		#These if statments should be replaced with a dict of dicts, initialized once
		if mode == 'NORMAL':
			nDev = 12
			useDict = False
		elif depth == 'NORMAL':
			#RAW Aqcuisition, Normal Memory Depth
			if nChan == 1:
				#1 Channel, Largest waveforms
				devDict = {50e-3:12, 20e-3:82, 10e-3: 66, 5e-3: 66, 
				2e-3:82, 1e-3:66, 500e-6:66, 200e-6:82, 100e-6:66,
				50e-6:66, 20e-6:82, 10e-6:66, 5e-6: 66, 2e-6:82}

			elif nChan == 2:
				#2 Channels
				devDict = {50e-3:12, 20e-3:41, 10e-3: 33, 5e-3: 33, 
				2e-3:41, 1e-3:33, 500e-6:33, 200e-6:41, 100e-6:33,
				50e-6:33, 20e-6:41, 10e-6:33, 5e-6: 33, 2e-6:41}	

		else:
			#RAW Acquisition, Long Memory Depth
			# due to the number of samples recorded, and the finite sampling rate of the scope,
			#	all time/dev of 100us and lower are giving essentially the same data out...
			#	it is only the scope screen display that is really changing

			if nChan == 1:
				#1 Channel, Largest waveforms
				devDict = {500e-3:12, 200e-3:12, 100e-3:12, 50e-3:12,20e-3:26, 
					10e-3: 26, 5e-3: 21, 2e-3:26, 1e-3:26, 
					500e-6:21, 200e-6:26, 100e-6:52.5, 50e-6:105, 
					20e-6:262, 10e-6:524, 5e-6: 1048}
					#NOT CALIBRATED YET!!! Probably a factor of 2 off of the 2channel dict below

			elif nChan == 2:
				#2 Channels
				devDict = {500e-3:12, 200e-3:12, 100e-3:12, 50e-3:12,20e-3:26, 
					10e-3: 26, 5e-3: 21, 2e-3:26, 1e-3:26, 
					500e-6:21, 200e-6:26, 100e-6:52.5, 50e-6:105, 
					20e-6:262, 10e-6:524, 5e-6: 1048}

		if useDict:
			try: nDev = devDict[tDev]
			except KeyError: 
				print("ERROR: The current time/dev setting of the scope was not coded into the 'getNDevs' function!\n")

		return nDev


	def getTimeVec(self):
		'''Get a numpy array of all time points to correspond to the acquired voltage readings'''

		#Update tScale and nPoints
		self.getNPoints()
		self.getTScale()
		self.getTOffset()

		#NEED TO FIX THE TIMESCALE FOR LONG ACQUISITION WITh SHORT TIME/DEV

		nDataPoints = self.nPoints-10	#strip 10 bytes of header from the read data
		nDevs = self.getNDevs()

		print(nDevs)

		dt = float(self.tScale * nDevs) / nDataPoints 	#there are 12 divs across the screen
		timeVec = np.arange(-self.tScale*nDevs/2, self.tScale*nDevs/2, dt) + self.tOffs

		return timeVec

	def saveScopeData(self, waveData, file):
		'''
		Save the specified waveform data (a column numpy array with columns
			time, Channel1, Channel2 (optional)
			into a .csv file at the location 'filename' (including full path)   
		'''
		nCols = waveData.shape[1]

		df = pd.DataFrame(waveData)
		
		if nCols == 3:
			head = ["Time (s)", "CH1", "CH2"]
		else:
			head = ["Time (s)", "CH1"]
		df.to_csv(file, header=head)	

	def getTUnits(self, waveData):
		''' Check the time column of the waveData numpy array to
				sort out appropriate units for plotting 

			Returns a tuple containing:
				- tUnit, a string to label the units in a plot axis
				- plotTScale, a number to multiplicatively rescale the plot data	
		'''
		if (waveData[-1:0] < 1e-6):
			plotTScale =  1e9
			tUnit = "ns"
		elif (waveData[-1:0] < 1e-3):
			plotTScale = 1e6
			tUnit = r"$\mu$s"
		elif (waveData[-1:0] < 1):
			plotTScale = 1e3
			tUnit = "ms"
		else:
			plotTScale = 1
			tUnit = "s"

		return (tUnit, plotTScale)

	def getVUnits(self, waveData, channel):
		'''Check the selected voltage channel of the numpy array waveData
				to sort out appropriate units for plotting

			Returns a tuple containing:
				- vUnit, a string to label the units in a plot axis
				- plotVScale, a number to multiplicatively rescale the plot data
		'''	
		if (waveData[:,int(channel)].max() < 0.2):
			plotVScale = 1e3
			vUnit = 'mV'
		else:
			plotVScale = 1
			vUnit = 'V'

		return (vUnit, plotVScale)

	def randomSample(self, data, nDownsample):
		'''
		Takes a numpy array of (time, Voltage) data points in column format
			and randomly selects a subset of the data according to the downsampling
			rate nDownsample

		Returns the randomly selected data subset dataSample
		'''

		nPoints = len(data[:,0])
		nSamples = nPoints/nDownsample
		indices = np.arange(0,nPoints)
		sampledIndices = random.sample(indices, nSamples)
		sampledIndices.sort()		#Sort the selected indices in ascending order
		dataSample = data[sampledIndices,:]
		return dataSample

	def plotScopeData(self, waveData):
		'''
		Takes some waveform data with columns [t(s), CH1(V), CH2(V) (optional) ]
			in the form of a numpy array, and generates a plot with matplotlib
		'''	

		#Select a sample to plot, if there are many data points
		if self.nPoints > 16394:
			#Using long, raw acquisition: downsample the data for smaller memory use
			if self.nPoints > 524300:
				nDownsample = 20 #~1M samples, use large downsampling
			else:
				nDownsample = 10 ##500k samples, use smaller downsampling

			waveData = self.randomSample(waveData, nDownsample)

		#Get the plotting units and rescale the data
		tUnit, tPlotScale = self.getTUnits(waveData)
		CH1Unit, CH1Scale = self.getVUnits(waveData,1)
		if len(waveData[0,:]) > 2: 
			CH2Unit, CH2Scale = self.getVUnits(waveData, 2)
			waveData = waveData * np.asarray([tPlotScale, CH1Scale, CH2Scale])
			dataMin = waveData[:,1:2].min()
			dataMax = waveData[:,1:2].max()
			dataRange = dataMax-dataMin
		else:
			waveData = waveData * np.asarray([tPlotScale, CH1Scale])
			dataMin = waveData[:,1].min()
			dataMax = waveData[:,1].max()
			dataRange = dataMax - dataMin

		plt.figure(figsize=(20,10), dpi=80, facecolor='w', edgecolor='b')
		plt.plot(waveData[:,0], waveData[:,1], 'y')
		if len(waveData[0,:])>2: 	
			plt.plot(waveData[:,0], waveData[:,2], 'b')
			plt.ylabel('Channel Voltage: CH1 (' + CH1Unit + '), CH2 (' + CH2Unit + ')', fontsize=16)
		else:
			plt.ylabel('Channel Voltage (' + CH1Unit + ')',fontsize=18)
		plt.title('Oscillosope Waveform', fontsize=20)
		plt.xlabel('Time (' + tUnit + ')', fontsize=18)
		plt.xlim(waveData[0,0], waveData[-1,0])
		plt.ylim(dataMin - dataRange/3, dataMax + dataRange/3)

		plt.show()

#----------------------------------------------------------------------------------

class RigolDG4162(object):
	'''
	A class for computer control of the Rigol DG4162 Dual Output Function Generator
	
	Author: Graham Edge
	Date: March 24, 2017

	Requires the following packages:
		pyvisa 			(for VISA communication)
		pyvisa-py 		(backend drivers for VISA communication, not needed if NI drivers are installed)
		pyusb			(usb support for pyvisa-py, also not needed if NI drivers are installed)

	An example call to this class would look like:
	
		x = RigolDG4162(ResourceManager, Address)


	where 'rm' is a resource manager class created by pyvisa, and 'address' is a 
	bytestream giving the USB address of the connected generator, as would be generated 
	by pyvisa code of the following form:
	
		rm = visa.ResourceManager('@py') 	#I use '@py' here to connect with the pyvisa-py backend, rather than the NI backend
		ilist = rm.list_resources()


	If the RG4162 is the only instrument connected to the computer, then its address would be:
	
		address = ilist[0]


	and so the device could be connected using:
	
		x = RigolDG4162(rm, ilist[0])
	'''

	def __init__(self, resourceManager, address):
		'''
		Establish communication with the instrument
		'''

		self.resource = resourceManager.open_resource(address)
		try:
			self.idn = self.resource.query('*IDN?')
			print('\nSuccessfully connected to instrument:\n' + self.idn)
		except:
			print('Unable to connect to instrument!')

	def close(self):
		'''
		Close the VISA session
		'''
		self.resource.close()

	def toggleFrontPanel(self):
		'''
		Lock/unlock the front panel buttons
		
		Note: The front panel buttons always become locked out when connected via USB.
				The KLOCK function either allows or disallows the user from breaking
				local control by pushing the BURST button

				When this option is toggled on, there will be no way to access the front panel
				without closing the USB connection
		'''
		self.resource.write(':SYST:KLOCK: OFF')

	def setFrequency(self, channel, freq, ampl = 1.4, offset = 0, phase = 0):
		'''
		Set the output 'channel' to a sine wave with the given frequency, 
		amplitude, phase, and offset
		'''

		command_string = ':SOURCE'+str(channel)+':APPL:SIN '+str(freq)+','+str(ampl)+','+str(offset)+','+str(phase)
		self.resource.write(command_string)


	def sendTrigger(self, channel):
		'''Send a software trigger to the specified channel, for burst mode'''
		command = ':SOURCE' + str(channel) + ':BURST:TRIGGER:IMM'
		self.resource.write(command)


#----------------------------------------------------------------------------------
class RigolDG1032TMC(object):


	def __init__(self, resourceManager = [], address = '', useUSBTMC = True, path = '/dev/usbtmc0'):
		'''
		Establish communication with the instrument

		If using the resource manager, the address is a bytestream as returned by 
			pyvisa's list_resources() command

		If using USBTMC, then address is ignored and connection is made with 'path,
			the location of the usbtmc file as a string (e.g. '/dev/usbtmc0')	
		'''

		if useUSBTMC:
			#Using the USBTMC protocol for connection
			self.resource = usbtmc(path)
			try:
				self.name = self.resource.getName()
	 			print('\nSuccessfully connected via USBTMC to DG1032:\n' + self.name)
	 		except:
	 			print('Unable to connect to Function Generator via USBTMC!')

	 		self.USBTMC = True	

		else:
			#Connect through the pyvisa resource manager
			self.resource = resourceManager.open_resource(address)
			try:
				self.idn = self.resource.query('*IDN?')
				print('\nSuccessfully connected to instrument:\n' + self.idn)
			except:
				print('Unable to connect to instrument!')

			#Define functions for reading and writing using PyVISA
			def write(self, command):
				self.resource.write(command)	
			def query(self, command):
				self.resource.query(command)

			self.USBTMC = False			#Should use this to redefine the read/write/query functions

		#Initialize other flags for the class
		self.verbose = False


	#Define commends for reading and writing over USBTMC
	def write(self, command):
		"""
		Send an arbitrary command directly to the scope
		"""
		self.resource.write(command)

	def read(self, nRead):
		"""Read an arbitrary amount of data directly from the scope"""
		return self.resource.read(nRead)

	def query(self, command, nRead = 100):
		'''A query command to write, and subsequently read specified number of bits'''    
		self.write(command)
		return self.read(int(nRead))

	def reset(self):
		"""Reset the instrument"""
		self.resource.sendReset	


	def close(self):
		'''
		Close the VISA session
		'''
		self.resource.close()		

	def turnOff(self, channel):
		'''Disable the channel output'''
		command = 'OUTP'+str(channel)+' OFF'
		self.write(command)
		time.sleep(0.1)

	def turnOn(self, channel):
		'''Enable the channel output'''
		command = ':OUTP'+str(channel)+' ON'
		self.write(command) 
		time.sleep(0.05)

	def reset(self):
		'''Reset the generator to defaults'''
		self.write(":SYST:PRESET DEFAULT")	

	def unlock(self):
		'''
		Unlock the font panel keys
		(this only -allows- the user to unlock the keys by pressing "Help" on the front panel)
		'''
		time.sleep(0.5)
		self.resource.write(':SYST:KLOC:STATE OFF')
		time.sleep(0.1)	


	def getWaveformDetails(self, channel = 1):
		'''
		Query the details of the current waveform
		'''	
		command = ':SOUR'+str(channel)+':APPL?'
		details = self.query(command)
		if not details:
			#No details returned... give some helpful output
			details = '"No details returned!\n(maybe set to ARB or there was a recent reboot)"'
		return details


	def setArbitrary(self, channel, samplerate = 20e6, ampl = 1, offs = 0):
		''' 
		Turn on the arbitrary waveform output of the selected channel, with
		20MSa/s sampling rate (the default), a peak to peak amplitude of 'ampl',
		and an offset of 'offs'

		Does not actually define the arbitrary waveform
		'''
		#Turn on arbitrary output
		command = ':SOURCE'+str(channel)+':APPL:ARB '+str(samplerate)+','+str(ampl)+','+str(offs)
		self.write(command)
		time.sleep(0.5)	

	def getVolatilePoints(self,channel = 1):
		'''Check the number of points in volatile memory'''

		return(self.query(':SOUR'+str(channel)+':DATA:POINTS? VOLATILE'))

	def setVolatilePoints(self,n, channel = 1):
		
		self.write(':SOUR'+str(channel)+':TRACE:DATA:POIN VOLATILE,'+str(n))
		time.sleep(0.1)

	def setVolatileVal(self,n,val, channel = 1):
		'''
		Adds the value 'val' to position n in the volatile memory

		Can be used iteratively to build an arbitrary waveform point by point
		
		It is best to wait ~15ms between sending points to avoid communication errors,
			making this process very slow for large waveforms
		'''
		self.write(':SOUR'+str(channel)+':DATA:VAL VOLATILE,'+str(n)+','+str(val))
		time.sleep(0.015)	#wait times less than 10ms can lead to dropped values	

	def loadVolatile(self,t,V, channel = 1, pointRange = 16383):
		'''
		Load an arbitrary waveform defined by the time vector t
			and the voltage vector V into the volatile memory

		Elements of t are timepoints in seconds
		
		Elements of V are voltages in Volts
		'''

		if len(t) != len(V):
			print('Voltage and Time vectors for arbitrary waveform do not match!\n')

		#Determine the appropriate volt scale and offset for the channel
		VMax, VMin = ( V.max(), V.min() )
		VAmpl = (VMax - VMin)
		VOffs = (VMax + VMin)/2.0
		V = 1.0*(V-VMin)/VAmpl			#Voltages rescaled to [0,1]
		
		VAmpl = np.round(VAmpl,3)
		VOffs = np.round(VOffs,3)

		#Rescale voltages into the range [0,16383] and store as a list
		val_list = 	list(np.round(V*pointRange).astype(int))
		
		#Determine the appropriate sampling rate for the channel
		nPoints = len(t)
		dt = t[1]-t[0]
		sRate = int(round(1/dt))
		print('Channel ' + str(channel) + ' Arb Settings:\n' \
			'Sampling Rate \t' + str(sRate) + 'Sa/s\n' \
			'Voltage Scale \t' + str(VAmpl) + 'V\n' \
			'Voltage Offset \t' + str(VOffs) + 'V\n')

		# Configure the arbitrary waveform settings
		self.setArbitrary(channel, samplerate = sRate, ampl = VAmpl, offs = VOffs)
		time.sleep(1)

		# Set the number of points for the channel
		self.setVolatilePoints(nPoints, channel)
		time.sleep(1)

		#Write the points to the channel one by one
		for num, val in enumerate(val_list, start=1):
			if num%50 == 0:
				print('Loading point {0!s} with value {1!s}'.format(num,val))
			self.setVolatileVal(num,val, channel)	


class RigolDG1032(object):
	'''
	A class for computer control of the Rigol DG1032 Dual Output Function Generator

	Author: Graham Edge
	Date: March 24, 2017
	'''

	# import random
	 
	# import instrument 					#custom class for Rigol DS1102E scope

	def __init__(self, resourceManager, address):
		'''
		Establish communication with the instrument
		'''

		self.resource = resourceManager.open_resource(address)
		try:
			#For some reason the DG1032 does not support identity queries in the form *IDN?
			# instead we try to query the system for its USB information
			self.idn = self.resource.query(':SYST:COMM:USB:INF?')	#for some reason this has a trailing zero
			print('\nSuccessfully connected to instrument:\n' + self.idn[0:-2])
		except:
			print('Unable to connect to instrument!')


		#Initialize flags
		self.ArbLimitsSet = False	

	def close(self):
		'''
		Close the VISA session
		'''
		self.resource.close()

	def unlock(self):
		'''
		Unlock the font panel keys
		(this only -allows- the user to unlock the keys by pressing "Help" on the front panel)
		'''
		time.sleep(0.5)
		self.resource.write(':SYST:KLOC:STATE OFF')
		time.sleep(0.1)

	def turnOff(self, channel):
		'''Disable the channel output'''
		command = 'OUTP'+str(channel)+' OFF'
		self.resource.write(command)
		time.sleep(0.1)

	def turnOn(self, channel):
		'''Enable the channel output'''
		command = ':OUTP'+str(channel)+' ON'
		self.resource.write(command) 
		time.sleep(0.05)

	def reset(self):
		'''Reset the generator to defaults'''
		self.resource.write(":SYST:PRESET DEFAULT")		

	def setSineWave(self, channel, freq, ampl = 1, offset = 0, phase = 0):

		command = ':SOURCE'+str(channel)+':APPL:SIN '+str(freq)+','+str(ampl)+','+str(offset)+','+str(phase)
		self.resource.write(command)
		time.sleep(0.05)

	def getWaveformDetails(self, channel = 1):
		'''
		Query the details of the current waveform
		'''	
		command = ':SOUR'+str(channel)+':APPL?'
		return self.resource.query(command)

	def setArbitrary(self, channel, samplerate = 20e6, ampl = 1, offs = 0):
		''' 
		Turn on the arbitrary waveform output of the selected channel, with
		20MSa/s sampling rate (the default), a peak to peak amplitude of 'ampl',
		and an offset of 'offs'

		Does not actually define the arbitrary waveform
		'''
		#Turn on arbitrary output
		command = ':SOURCE'+str(channel)+':APPL:ARB '+str(samplerate)+','+str(ampl)+','+str(offs)
		self.resource.write(command)
		time.sleep(0.5)

	def setSquareWave(self, channel, highV = 1, lowV = -1, period = 1e-3, delay = 0):
		'''
		Set a square wave with arbitrary high, low values
		'''
		freq = 1.0/period
		ampl = (highV - lowV)/1.0
		offset = (highV + lowV)/2.0
		phase = (delay/period)*360.0

		command = ':SOURCE'+str(channel)+':APPL:SQU '+str(freq)+','+str(ampl)+','+str(offset)+','+str(phase)
		self.resource.write(command)
		time.sleep(0.05)

	def setPulse(self, channel, highV = 1, lowV = -1, period = 1e-3, duty = 50, delay = 0):
		'''
		Set a square wave with arbitrary high, low values
		'''
		freq = 1.0/period
		ampl = (highV - lowV)/1.0
		offset = (highV + lowV)/2.0
		phase = (delay/period)*360.0

		command = ':SOURCE'+str(channel)+':APPL:PULSE '+str(freq)+','+str(ampl)+','+str(offset)+','+str(phase)
		self.resource.write(command)
		time.sleep(0.05)

		command = ':SOURCE'+str(channel)+':FUNCTION:PULSE:DCYCLE '+str(duty)
		self.resource.write(command)
		time.sleep(0.05)

	def setRamp(self, channel, period = 10e-3, ampl = 1.25, offset = 0, phase = 0, symm = 50):
		'''
		Set a ramp with delay before starting, period, and dV
		'''
		freq = 1.0/period

		command = ':SOURCE'+str(channel)+':APPL:RAMP '+str(freq)+','+str(ampl)+','+str(offset)+','+str(phase)
		self.resource.write(command)
		time.sleep(0.05)

		command = ':SOURCE'+str(channel)+':FUNCTION:RAMP:SYMM '+str(symm)
		self.resource.write(command)
		time.sleep(0.05)	

	def getVolatilePoints(self,channel = 1):
		'''Check the number of points in volatile memory'''

		return(self.resource.query(':SOUR'+str(channel)+':DATA:POINTS? VOLATILE'))

	def setVolatilePoints(self,n, channel = 1):
		
		self.resource.write(':SOUR'+str(channel)+':TRACE:DATA:POIN VOLATILE,'+str(n))
		time.sleep(0.1)

	def setVolatileVal(self,n,val, channel = 1):
		'''
		Adds the value 'val' to position n in the volatile memory

		Can be used iteratively to build an arbitrary waveform point by point
		(but this is incredibly tedious!)
		'''
		self.resource.write(':SOUR'+str(channel)+':DATA:VAL VOLATILE,'+str(n)+','+str(val))
		time.sleep(0.015)	#wait times less than 10ms can lead to dropped values

	def loadStoredVolatile(self, channel = 1):

		command = ':DATA:COPY VOL.RAF,VOLATILE'
		print(command)
		self.resource.write(command)


	def loadVolatile(self,t,V, channel = 1, pointRange = 16383):
		'''
		Load an arbitrary waveform defined by the time vector t
			and the voltage vector V into the volatile memory

		Elements of t are timepoints in seconds
		
		Elements of V are voltages in Volts
		'''

		if len(t) != len(V):
			print('Voltage and Time vectors for arbitrary waveform do not match!\n')

		#Determine the appropriate volt scale and offset for the channel
		VMax, VMin = ( V.max(), V.min() )
		VAmpl = (VMax - VMin)
		VOffs = (VMax + VMin)/2.0
		V = 1.0*(V-VMin)/VAmpl			#Voltages rescaled to [0,1]
		
		VAmpl = np.round(VAmpl,3)
		VOffs = np.round(VOffs,3)

		#Rescale voltages into the range [0,16383] and store as a list
		val_list = 	list(np.round(V*pointRange).astype(int))
		
		#Determine the appropriate sampling rate for the channel
		nPoints = len(t)
		dt = t[1]-t[0]
		sRate = int(round(1/dt))
		print('Channel ' + str(channel) + ' Arb Settings:\n' \
			'Sampling Rate \t' + str(sRate) + 'Sa/s\n' \
			'Voltage Scale \t' + str(VAmpl) + 'V\n' \
			'Voltage Offset \t' + str(VOffs) + 'V\n')

		#Limits not set yet, configure them
		self.setArbitrary(channel, samplerate = sRate, ampl = VAmpl, offs = VOffs)
		time.sleep(0.1)

		# Set the number of points for the channel
		self.setVolatilePoints(nPoints, channel)
		time.sleep(0.1)

		#Write the points to the channel one by one
		for num, val in enumerate(val_list, start=1):
			if num%50 == 0:
				print('Loading point {0!s} with value {1!s}'.format(num,val))
			self.setVolatileVal(num,val, channel)

	def checkVolatile(self):
		
		command = 'SOURCE1:DATA:CAT?'
		print(self.resource.query(command))
		time.sleep(0.1)	

	def setNCycBurst(self, channel, nCycl = 1, trigSource = 'INT', burstPeriod = 0.1, tDelay = 0, idleLevel = 0):
		''' 
		Turn on the burst mode
		
		Idle level is a number between 0 and 16383 (14 bits, which sets the idle level of the signal between
		bursts to either the min (if idle=0) of the waveform, the max (if idle=16384) , or 
		somewhere in between
		'''

		command = ':SOURCE'+str(channel)+':BURST:MODE TRIG'			#Set the burst to occur on trigger
		self.resource.write(command)
		time.sleep(0.05)

		command = ':SOURCE'+str(channel)+':BURST:NCYCL ' + str(nCycl)	#Set the number of cycles
		self.resource.write(command)
		time.sleep(0.05)

		command = ':SOURCE'+str(channel)+':BURST:TRIG:SOURCE '+trigSource	#External triggering
		self.resource.write(command)
		time.sleep(0.05)

		if trigSource == 'INT':
			#Set the period of the internal trigger
			command = ':SOURCE'+str(channel)+':BURST:INT:PER '+str(burstPeriod)	#Set burst period
			self.resource.write(command)
			time.sleep(0.05)

		command = ':SOURCE'+str(channel)+':BURST:TDEL ' + str(tDelay)	#Set the delay
		self.resource.write(command)
		time.sleep(0.05)

		command = ':SOURCE'+str(channel)+':BURST:IDEL ' + str(idleLevel)	#Set the leve between bursts
		self.resource.write(command)
		time.sleep(0.05)

		command = ':SOURCE'+str(channel)+':BURST:STATE ON'		#Enable the burst mode
		self.resource.write(command)
		time.sleep(0.05)


#--------------------------------
# Other devices in the lab
#--------------------------------

class Lakeshore331(object):

	def __init__(self, path = '/dev/ttyUSB0', baudrate=9600, timeout=2):
		'''
		Make a connection to the Lakeshore Cryogenic Temperature controller
		over RS232, or maybe a USB-RS232 adapter

		If a USB-Serial adapter is used to connect to the RS232 port of the LakeShore controller,
			follow the steps at (https://blog.mypapit.net/2008/05/how-to-use-usb-serial-port-converter-in-ubuntu.html)
			to set up the USB-RS232 link in Ubuntu
			The result should be a USB address like '/dev/ttyUSB0'

		'''

		self.timeout = timeout

		#Use the USBTMC protocol for connection
		self.resource = serial.Serial(path, baudrate=baudrate, timeout = self.timeout)
		print(self.resource.name)
		self.resource.flush()
		self.resource.write('*IDN?')
		self.resource.flushInput()
		print(self.resource.isOpen())
		try:
			s = self.resource.readline()
			print('Received: %s' % s)
			self.resource.flushOutput()
 			print('\nSuccessfully connected via USBTMC to LakeShore instrument:\n')
 		except:
 			print('Unable to connect to LakeShore controller via serial!')


 	#Define commends for reading and writing over USBTMC
	def write(self, command):
		"""
        Send an arbitrary command directly to the scope
        """
		print(command)
		self.resource.write(command)
 
	def read(self, nRead):
		"""Read an arbitrary amount of data directly from the scope"""
		return self.resource.read(nRead)

	def query(self, command, nRead = 100):
		'''A query command to write, and subsequently read specified number of bits'''    
 		print(command)
 		self.write(command)
 		return self.read(int(nRead))

	def reset(self):
		"""Reset the instrument"""
		self.resource.sendReset	

	def getTemp(self):
		'''Read the thermocouple junction temperature in K'''

		command = "TEMP?"

		return self.query(command)

class WA1500(object):

	def __init__(self):
		'''
		Establish communication using RS232 or a USB-RS232 adapter
		'''	

		self.resource = resourceManager.open_resource(address)
		try:
			self.idn = self.resource.query('*IDN?')	
			print('\nSuccessfully connected to WA1500:\n' + self.idn)
		except:
			print('Unable to connect to WA1500!')	

		#WA1500 boots in Broadcast mode
		self.QueryMode = False		

	def packageCommand(self, hex_command):
		'''
		All commands to the wavemeter are bracketed by start and stop characters
		 - commands begin with '@'
		 - commands end with '\r\n' (carriage return - line feed pair)
		 - between these characters, commands are single Hexadecimal numbers
		'''		
		command = '@' + hex_command + '\r\n'
		return command

	def unpackResponse(self, response):
		'''
		Responses are 23-character, comma-delimited, fixed-field, formatted strings
		 - first character is always a '+' or '~'
		 - terminating character is always a CR (0x0D) carriage return and
		 		LF (0x0A) line feed pair
		 - fields are:
		 	1) first 11 characters: wavelength or status code
		 	2) next 4 characters: display LED status as hexadecimal
		 	3) next 4 characters: system LED status as hexadecimal

		 e.g. '+ 632.9911,2A49,0200\r\n'
		 			- wavelength 632.9911nm
		 			- 2A49 -> averaging off, auto resolution, vacuum wavelength, nm units
		 			- 0200 -> input attenuator in automatic mode
		'''	

	def buildHexDicts(self):
		'''
		Creates dictionaries to keep track of the various hexadecimal commands
			associated with the front panel buttons, LED status
		'''	

		self.buttonCommands = {'save':'0E', 'reset':'0F', 
			'manual deattenuate':'10', 'manual attenuate':'11', 'auto attenuate':'13',
			'humidity':'20', 'pressure':'21', 'temperature':'22',
			'# averaged':'23', 'averaging':'2B',
			'analog res':'24', 'display res':'25', 'setpoint':'26',
			'units':'27', 'display':'28', 'medium':'29', 'resolution':'2A'}

		self.displayLEDMask = {'unitsNM':0x0009, 'unitsCM':0x0012, 'unitsGHZ':0x0024,
			'displayWavelength':0x0040, 'displayDeviation':0x0080,
			'mediumAir':0x0100, 'mediumVacuum':0x0200,
			'resolutionFixed':0x0400, 'resolutionAuto':0x0800,
			'averagingOn':0x1000, 'averagingOff':0x2000}

		self.systemLEDMask = {'displayRes':0x0001, 'setpoint':0x0002,
			'# averaged':0x0004, 'analog res':0x0008,
			'pressure':0x0010, 'temperature':0x0020, 'humidity':0x0040,
			'setup':0x0080, 'remote':0x0100,
			'attenuator auto':0x0200, 'attenuator manual':0x0400}
		
#Some non-button settings
#------------------------

	def setQueryMode(self):
		'''
		Set the wavemeter to Query mode (read wavelength only on command)
			rather than the default Broadcast mode (wavelength is transmitted automatically)
		'''		
		command = '@\x51\r\n'

		#send command

		#update flags
		self.QueryMode = True

#Button type settings
#---------------------

	def pressButton(self, button):
		'''
		Send the software command equivalent to pressing the selected button
			on the front panel of the wavemeter

		Possible buttons are:
			Auto Attenuate, Manual Attenuate, Manual Deattenuate
			Hummidity, Pressure, Temperature
			# Averaged, Averaging
			Units, Display, Medium, Resolution
			Setpoint, Analog Res, Display Res
		'''

		self.write(packageCommand())		


# funcgen.write(":SOURCE1:MOD:TYPE FM")				#Enable FM MOD
# funcgen.write(":SOURCE1:MOD:FM:DEV 5e6")			#Set parameters of FM MOD
# funcgen.write(":SOURCE1:MOD:FM:SOURCE EXT")			#External triggering
# funcgen.write(":SOURCE1:MOD:FM:INT:RAMP")			#Modulate with the ramp waveform
# funcgen.write(":SOURCE1:MOD:FM:INT:FREQ 1e3")		#Set the rate of FM modulation

# funcgen.write(":SOURCE1:MOD:STATE ON")				#Enable the deviation