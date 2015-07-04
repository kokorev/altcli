# coding=utf-8
"""
Общие функции и классы, имеющие чисто техническое значение
Основа - класс config определяющий глобальные настройки
"""
__author__ = 'Vasily Kokorev'
__email__ = 'vasilykokorev@gmail.com'
import os
import dummy

elSynonyms = {
	'temp' : ['temperature','temp','T','tas','dta','temperature_anomaly','2 metre temperature','air_temperature','tmp'],
	'prec' : ['P','precipitation','prec','pr'],
	'hsnow' : ['hsnow'],
	'ctl' : ['ctl'],
	'rhs' : ['rhs'],
	'wind' : ['wind','sfcWind'],
	'runoff' : ['runoff'],
	'ch4' : ['ch4'],
}

elSynom=dict()

for k, ln in elSynonyms.items():
	elSynom.update({v:k for v in ln})

def makePythonRusFriendly(font='GARA'):
	""" делает настройки для поддержки русских шрифтов """
	import matplotlib.pyplot as plt, matplotlib.font_manager as fm
	global fp1
	plt.rcParams["text.usetex"] = False
	fp1 = fm.FontProperties(fname=os.path.split(dummy.__file__)[0] + '//resources//' + font + ".ttf")
	return fp1

def getSaveResId(method, *args, **kwargs):
	"""
	функция принимает метод и его аргументы, а возвращает индификатор под которым
	результаты расчёта этого метода с этими параметрами были записаны в словарь
	Ключ слваря составляетьс по форме "имя функции--список значений аргументов через запятую"
	"""
	dId = method.__name__ + '--'
	for s in args: dId += str(s) + ','
	for s in kwargs: dId += str(s) + ','
	return dId[0:-1]

def timeit(method):
	""" Печатает время выполнения функции """
	def timed(*args, **kw):
		import time
		ts = time.clock()
		result = method(*args, **kw)
		te = time.clock()
		print '%r (%r, %r) %2.2f sec' %(method.__name__, args, kw, te-ts)
		print '%r %3.3f sec' %(method.__name__, te-ts)
		return result
	return timed