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
	@return: VPD - Vapour Pressure Deficit, гПа
	"""
	if f>1:f=f/100.
	VPsat=6.11*10**(7.5*T/(273.15+T))
	VPair=VPsat*f
	VPD=VPsat - VPair # Vapour Pressure Deficit, гПа
	return VPD
