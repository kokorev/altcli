# coding=utf-8
__author__ = 'vkokorev'
import math

def rh2ah(f, T):
	"""
	@param f: relative humidity, %
	@param t: temperature, deg. C
	@return: a - absolute humidity, g/m^3
	"""
	a=(6.112 * math.e**( (17.67*T)/(T+243.5) ) * f * 2.1674)/(273.15+T)
	return a

def rh2vpd(f,T):
	"""

	@param f: relative humidity, %
	@param T: temperature, deg. C
	@return: VPD - Vapour Pressure Deficit, mbar
	"""
	if f>1:f=f/100.
	if T<100: T=T+273.15
	VPsat=math.e**(-0.000188/T + -13.1 + -0.015*T + 8*10**-7*T**2 + -1.69*10**-11*T**3 + 6.456*math.log(T))
	VPair=VPsat*f
	VPD=VPsat - VPair # Vapour Pressure Deficit, kPa
	return VPD*10 # mbar
