


#Import packages
import numpy as np 					# for math
import sys
import deepdish as dd				# nice way to save files (similar to pickle)
import matplotlib.pyplot as plt		# for plotting the data
from scipy import signal			#For filtering

#-------------
#	Functions
#-------------

def loadDataDict(file_loc):
	'''
	Load the data dictionary saved as HDF5 in the specified location

	We currently save scan data as a dictionary, with keys that are integers,
		specifying different measurements

	Each value of the dictionary is another dictionary containing all of the
		parameters of the particular measurement, and any data that was recorded
	'''
	data_dict = dd.io.load(file_loc)

	print('Data dictionary has %d measurements' % getNumMeasurements(data_dict))

	try:
		print('The first measurement has %d parameters.' % len(data_dict[data_dict.keys()[0]]))
		print(data_dict[data_dict.keys()[0]].keys())
	except:
		errormsg = 'Error examining the parameters of the first measurement.\nAre the elements of the data dictionary also dictionaries?'
		print(errormsg)
		print "The error:", sys.exc_info()[0]

	return data_dict


def getDataShape(data_dict, nMeas=0):
	'''
	Gets the shape of the 'data' array stored for measurement nMeas (keys of data_dict are integers)

	Returns the tuple (nRows, nColumns)
	'''
	return np.shape(data_dict[nMeas]['data'])

def getNumMeasurements(data_dict):
	''' 
	Returns the number of measurements recorded in the data_dict.
	This is probably just the length of data_dict... but we allow for
	more complicated operations to take place later.
	'''

	if '# measurements' in data_dict.keys():
		nMeasurements = data_dict['# measurements']
	else:
		nMeasurements = len(data_dict)

	return nMeasurements

def getMeasurementList(data_dict):
	'''
	Since not all measurements may be needed for analysis,
		or since we may need to exclude measurements with errors present,
		this function returns a list of the desired keys of the data dictionary
		data_dict that are to be used to access the correct data.	
	'''

	#Check for wavemeter error
	allMeasurements = range(getNumMeasurements(data_dict))
	measList = []
	for meas in allMeasurements:
		if data_dict[meas]['wavemeter error'] != 'ok':
			print('\nExcluding measurement %d due to some wavemeter error.' % meas)
		elif data_dict[meas]['frequency'] < 438000 :
			print('\nExcluding measurement %d because the frequrncy is out of expected scan range' % meas)
		else:
			measList.append(meas)

	return measList

def getSignal(data):
	'''
	For a given numpy array 'data' which has columns [t(s), CH1(V), CH2(V)],
		we want to convert the channel voltages into optical powers,
		and then take the ratio to calculate the OD of the crystal
	'''
	
	#Convert CH1 to Power Difference (uW)
	data[:,1] = data[:,1] * (5.0/0.235)
	#Then convert power difference into absorption (%)
	#	(this assumes the beam has power 56uW at the detector)
	data[:,1] = data[:,1] / 56.0
	#Turn this into absorption
	absorption = data[:,1].max() - data[:,1]
	
	#Smooth the data?
	#data[:,1] = filterSignal(data[:,1])
	
	#Convert CH2 to P_out(uW)
	fluorescence = data[:,2]
	
	#Calculate OD based on absorption
	OD = -np.log10(1.0-absorption)
	
	return OD,absorption,fluorescence

def filterSignal(sigData, filterParam = 0.05):
	'''Apply some sort of filtering to the data to make atomic features stand out '''
	
	#Filter the data
	b, a = signal.butter(3, filterParam)			#Create 3rd order Butterworth filter
	y = signal.filtfilt(b, a, sigData)		#Apply filter
	
	return y

def combineScans(data_dict):
	'''
	For a dictionary data_dict (which contains inside it 
	other dictionaries which each correspond to a measurement)
	this function combines all measured data into one large numpy
	array according to the measured optical frequency

	Assumes that each measurement dictionary has keys:
	- 'frequency' the frequency in GHz
	- 'data' a numpy array with columns [t(s), CH1(V), CH2(V)]

	Also assumes that data_dictionary has parameters:
	- 'scan range' the range in GHz covered by each measurement
	- 'scan time' the time (in s) taken to complete each frequency scan (half of ramp period for a triangle wave)
	'''

	#Determine the shape of each downloaded trace
	lengthData, nColumns = getDataShape(data_dict)
	
	nChannels = nColumns -1
	print('\n%d channels of data recorded.' % nChannels)

	#Check number of measurements
	nMeasurements = getNumMeasurements(data_dict)

	#Determine the points in each trace that represent the ramp
	T_scan = float(data_dict['scan time'])
	tVec = data_dict[0]['data'][:,0]
	scanVec = tVec[ (tVec >= (-T_scan/2)) & (tVec <= (T_scan/2))]
	nPoints = len(scanVec)	
	print('Each scan has %d interesting points.'%nPoints)
	#Determine the index in each trace where the ramp begins and ends	
	print('Total length of each trace is %d ' % lengthData)
	print('Will crop out the %d points corresponding to a single scan' % nPoints)
	rampStart 	= lengthData/2 - int(round(nPoints/2))
	rampEnd		= lengthData/2 + int(round(nPoints/2))

	#Determine the frequency offset vector for each data trace
	fRange = float(data_dict['scan range'])
	df =  fRange / nPoints
	fVec = np.arange(-fRange/2+df/2, fRange/2+df/2, df)		
			#the extra df/2 factor is supposed to account for python zero-indexing... not important when nPoints>>1

	#Get the subset of measurements to be plotted (excluding wavemeter errors etc...)
	measurementList = getMeasurementList(data_dict)

	#Initialize the array to hold all the data
	frequencyData = np.zeros((len(measurementList)*nPoints, nColumns))

	#Iterate over each measurement in data_dict
	for nMeas, nameMeas in enumerate(measurementList):
		nStart 	= (nMeas)*nPoints
		nEnd	= (nMeas+1)*nPoints		

		params = data_dict[nameMeas]
		data = params['data']
		f0 = params['frequency']
		errorMsg = params['wavemeter error']
		f = fVec + f0

		frequencyData[nStart:nEnd, 0] = f
		frequencyData[nStart:nEnd, 1] = data[rampStart:rampEnd+1, 1]
		frequencyData[nStart:nEnd, 2] = data[rampStart:rampEnd+1, 2]

	#Sort the measurements in order of ascending frequency
	frequencyData = frequencyData[frequencyData[:,0].argsort()]

	return frequencyData

#----------------------------
#	Loading and Plotting Data
#----------------------------


if __name__ == '__main__':


	savefolder 	= 	'/home/labuser/Desktop/Experiment Control/Data/2017/05_May_2017/May_18/'
	datafile 	= 	'4Kdata.h5'
	datafile2   =   '4Kdata_part2.h5'
	datafile3   =   '4Kdata_part3.h5'
	file_loc = savefolder + datafile
	file_loc2 = savefolder + datafile2
	file_loc3 = savefolder + datafile3

	data_dict = loadDataDict(file_loc) 
	#data_dict.update(loadDataDict(file_loc2))
	data_dict.update(loadDataDict(file_loc3))

	#Fill in the missing parameters

	for i in data_dict.keys():
		print data_dict[i]['frequency'],data_dict[i]['wavemeter error']

	data_dict['# measurements'] = len(data_dict.keys())
	data_dict['scan time'] = 0.1
	data_dict['scan range'] = 0.6

	runData = combineScans(data_dict)

	#Can print out some of the data for inspection
	printOut=False
	if printOut:
		for i in range(0,len(runData), 100):
			print(runData[i,:])

	#Determine the centre frequency, so that it can be used in the plot axis
	centreFreq = round((runData[:,0].max() + runData[:,0].min())/2)
	print('\nCentre frequency is %d GHz' % centreFreq)


	#Calculate the fraction of power transmitted
	OD,absorption,fluorescence = getSignal(runData)



	#Apply filtering to the signal
	#sigData = filterSignal(sigData)


	plotting = True
	if plotting:
		fig = plt.figure(figsize=(10,6), dpi=80)
		plotA = fig.add_subplot(111)
	
		plotA.plot(runData[:,0]-centreFreq, absorption,'.y')
		#plotA.set_xlim(1.,50000.)
		plotA.tick_params(axis='both', which='major', labelsize=14)
		plotA.set_xlabel('Frequency (GHz) - %d' % centreFreq, fontsize=20)
		plotA.set_ylabel('absorption', fontsize=20)
		plt.title('Crystal Absorption Scan at 4K', fontsize = 20)

		plt.show()

