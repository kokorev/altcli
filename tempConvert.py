# coding=utf-8
"""
Модуль конвертирующий значения температуры между системами измерений
"""
def kelvin2celsius(val):
	k=273.15
	return val-k

def celsus2kelvin(val):
	k=273.15
	return val+k

def celsius2fahrenheit(val):
	celsius = (val - 32) / (9.0/5.0)
	return celsius

def fahrenheit2celsius(val):
	fahrenheit = (val * (9.0/5.0)) + 32
	return fahrenheit

def fahrenheit2kelvin(val):
	celsius=fahrenheit2celsius(val)
	kelvin=celsus2kelvin(celsius)
	return kelvin

def kelvin2fahrenheit(val):
	celsius=kelvin2celsius(val)
	fahrenheit=celsius2fahrenheit(celsius)
	return fahrenheit