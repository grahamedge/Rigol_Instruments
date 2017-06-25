'''
Generate a waveform to load into a Rigol arbitrary waveform generator

Important features of an arbitrary waveform file:
- must use 4096 time steps
- the value at each step is between 0 and 16383 (14 bit depth)
- the values should be stored in a binary file as an 
	unsigned 16-bit binary word in little-endian format
- the overall period and amplitude of the wave will be set by the settings
	of the specific channel on the generator
'''

import numpy as np
import matplotlib.pyplot as plt

nSteps = 4096
bitrange = 16383

#create time vector
T = np.arange(nSteps)
wave = np.zeros(nSteps)


#Basic commands
#--------------

def V2b(V):
	'''
	Convert a voltage in the range [0,1] into a 14 bit number
	'''
	return np.round(bitrange*V)

def b2V(b):
	'''
	Convert a 14 bit number back into the range [0,1]
	'''	
	return b/bitrange

def t2step(t):
	'''
	From a time in the range [0,1], return the corresponding timestep

	Can accept a tuple of times and output a tuple of steps
	'''	
	return int(nSteps*t)

def step2t(step):
	'''
	For a given timestep, return the corresponding time in the range [0,1]
	'''	
	return step/nSteps

def getV(t):
	'''
	Finds the current value of the wave at the given fractional time
	'''
	return b2V(wave[t2step(t)])

def fillV(stepf, Vf):
	'''
	Fill the rest of the wave from time tf to the end with the voltage level Vf
	'''
	wave[stepf:-1] = V2b(Vf)


#Function sections
#-----------------

def addRampSegment(ti, Vi, tf, Vf):
	'''
	Create a linear ramp starting at ti and ending at (tf-1)

	All times and voltages are input in the range [0,1]
	'''
	i, f = (t2step(ti), t2step(tf))

	wave[i:f] = V2b(  Vi + (Vf-Vi)*( T[i:f] - i )/(f-i)  ) 	#Fill in the ramp
	fillV(f, Vf)	#Hold the ramp final value

def addStep(ti, Vi, Vf):
	'''
	Like a ramp that takes one timestep
	'''	
	i = t2step(ti)
	wave[i] = V2b(Vi)
	wave[i+1] = V2b(Vf)
	fillV(i+1, Vf)			#Hold the final value of the step

def addGaussian(ti, to, A, sigma, avoidDiscontinuity = False):
	'''
	Create a Gaussian pulse centred at to, with amplitude A and standard deviation sigma

	Since the Gaussian function is defined for all t, the arguement ti 
		specifies the time to begin sampling the Gaussian function

	The avoidDiscontinuity arguement should be used carefully. It does make the 
		output function look nicer by removing the small steps when turning on and off
		but it changes the max height of the Gaussian from what would be expected
		based on the input amplitude. It is probably better to sample the Gaussian over
		a larger range by using (ti-to) >> sigma
	'''	
	tf = to+(to-ti)							#Time to stop sampling the Gaussian
	i, centre, f = ( t2step(ti), t2step(to), t2step(tf) )	#Convert to timesteps
	s = float(t2step(sigma))	#Convert sigma to timestep units

	if avoidDiscontinuity:
		#shift the Gaussian down to match smoothly with the voltage at ti
		#	this preserves the time constant of the pulse
		#	but changes the expected peak height
		offsetV = getV(ti) - A*np.exp(-(T[i] - centre)**2 / (2*s**2))
	else:
		offsetV = getV(ti)	#Gaussian is defined relative to the initial voltage at ti

	wave[i:f] = V2b( offsetV + (A*np.exp(-(T[i:f] - centre)**2 / (2*s**2))) )


#Interactivity and Debugging
#---------------------------

def plotWave():
	'''
	Plot the wave for visualization
	'''
	plt.plot(T, b2V(wave), 'k')
	plt.xlabel('Time Step')
	plt.ylabel(r'$V / V_{max}$')
	plt.title('Arbitrary Waveform')
	plt.ylim((-0.02,1.02))

	plt.show()


#----------
#Examples
#----------	

#Example 1 - A series of piecewise linear ramps and steps
#---
#Make a simple wave and plot it
# addRampSegment(0.25, getV(0.25), 0.5, 1)

# addStep(0.55, getV(0.55), 0)

# addRampSegment(0.75,getV(0.75),0.85, 0.5)

# addRampSegment(0.9, getV(0.9), 0.95, 0)

#---


#Example 2 - A train of Gaussian pulses
#---
pulsesep = 0.2
pulsetimes = np.arange(0.1, 1, pulsesep)

for time in pulsetimes:
	addGaussian(time-pulsesep/3, time, 0.5, 0.01, avoidDiscontinuity=False)
#_--


plotWave()