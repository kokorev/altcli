# coding=utf-8
"""
Модуль конвертирующий значения осадков между системами измерений
"""

def si2mmPerMonth(val,year=None,month=None):
	"""
	Конвертирует сумму осадков из системы си - кг/м^2 *c в месячные суммы в миллиметрах
	если заданы год и месяц то используется релаьное количестве дней, если не заданы то 30.5
	"""
	import calendar
	if year is not None and month is not None:
		numD=calendar.monthrange(year, month)[1]
	else:
		numD=30.5
	r=val*86400*numD
	return r

def si2mmPerDay(val,year=None,month=None):
	return val*86400