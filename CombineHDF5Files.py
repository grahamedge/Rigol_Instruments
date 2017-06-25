'''
This script can be used to combine the data_dict files from different measurements
	into one large dictionary, for easier plotting and manipulation.

author: Graham Edge
'''



#Load packages
#--------------

#Standard
import time   						#for read/write delays
import cPickle as pickle			#to save data

#Other packages
import numpy as np 					#for math
import visa							#communications
import os 							#for some path handling (file save locations etc...)
import sys							#currently using sys.exit to abort when an error occurs
import deepdish as dd				#nice way to save files (similar to pickle)
# import random
import matplotlib.pyplot as plt 	#for graphics
# import pandas as pd 				#for data handling

#Home-written stuff
from RigolInstruments import RigolDG4162, RigolDG1032, RigolDG1032TMC, RigolDS1102, RigolDS1054
from Wavemeter import WA1500
from cryostat_templog import *
from plotHDF5data import getNumMeasurements
from ScopeLogging import addMeasurement

#A folder with files in it
folder = '/home/labuser/Desktop/Experiment Control/Data/2017/05_May_2017/May_18/'
#A list of files in that folder
file_list = ['4Kdata.h5', '4Kdata_part2.h5', '4Kdata_part3.h5']

#Create a file name for the new data_dict
newFile = 'CombinedDict'


#Combine into a list of absolute paths to files (useful in case we want 
#	to grab files from multiple different folders... could just append to this list)
file_path_list = [folder + filename for filename in file_list]

#Check that all files are correctly specified
for n, fileLoc in enumerate(file_path_list):
	if not os.path.exists(fileLoc):
		print('File not found at location %s, so it will be ignored!' % fileLoc)
		print('Check the folder and file names!')

	else:
		#Open the data_dict
		data_dict = dd.io.load(fileLoc)
		print('Data dictionary %d has %d measurements' % (n, getNumMeasurements(data_dict)) )

		#Loop over the keys (individual measurements)
		for k in data_dict.keys():
			#Access each corresponding measurement
			measurement = data_dict[k]
			# ... and then add it to the new dictionary
			addMeasurement(measurement,newFile, folder)

new_dict_loc = folder + newFile + '.h5'
final_dict = dd.io.load(new_dict_loc)
print('Final data dict has %d measurements' % (getNumMeasurements(final_dict)) )

