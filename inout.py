# -*- coding: cp1251 -*-
"""
Класс реализующий функции записи и чтения в/из форматы/ов altCli
	*.acr - altCli results
	*.acd - altCli data
А так же реализующи представление объектов altCli в виде ЧП текста
"""
import os.path

def resToListOfStr(fnctname, fres):
	"""
	Функция преобразует выходной результат ф-ии расчёта какого-то параметра по станции
	 в человекоПонятную таблицу
	принимает:
		fn - str, имя функции результат которой надо представить в виде строки
		fres - dict, словарь результатов расчтёа
	возвращает:
		head - список заголовков для представления результатов
		res - список результатов в виде строк
		один элемент списка- один столбец
	"""
	if fnctname in ['norm', 'ampl']:
		head = [fnctname + '-%02i' % i for i in range(1, 13)]
		res = [str(round(fres[i], 2)) for i in range(0, 12)]
	elif fnctname in ['trend']:
		head = [fnctname]
		res = [str(round(fres[0], 3))]
	elif 's_' in fnctname:
		if len(fres) == 1:
			k, v = [[k, v] for k, v in fres.items()][0]
			head, res = resToListOfStr(k + fnctname[1:], v)
		else:
			raise ValueError
	else:
		head = [fnctname]
		if type(fres) == list or type(fres) == tuple:
			res = [str(fres[0])]
		elif type(fres) == dict:
			raise ValueError
		else:
			res = [str(fres)]
	return head, res


def saveDat(obj, fn, replace=False):
	"""
	Записывает объет cliDat в файл, без результатов расчётов
	"""
	if fn[-4:] != '.acd': fn += '.acd'
	if os.path.exists(fn):
		if replace == False:
			raise IOError, 'File %s already exist. Change file name or use replace=True argument' % fn
	r = str(obj.meta) + '\n'
	for y in obj:
		r += str(y)
	f = open(fn, 'w')
	f.write(r)
	f.close()


def loadDat(fn):
	"""
	Загружает объект cliDat из файла
	"""
	from clidata import cliData
	if fn[-4:] != '.acd': fn += '.acd'
	f = open(fn, 'r')
	txt = f.read()
	stxt = txt.split('}')       # отделяем метаинформацию от данных
	# убирём строчки с коментариями из метоинформации
	metatxt = '\n'.join([line for line in stxt[0].split('\n') if line.strip()[0] != '#']) + '}'
	meta = eval(metatxt)
	dat = []
	for line in stxt[1].split('\n'):
		if line == '': continue
		if line.strip()[0] == '#': continue
		ln = line.strip()
		arr = [(float(v) if v != 'None' else None) for v in ln.split('\t')]
		dat.append([int(arr[0]), arr[1:]])
	aco = cliData(meta, gdat=dat)
	return aco


def saveRes(obj, fn, replace=False):
	"""
	Сохраняет результаты расчёта в файл
	принимает объект cliDat и имя файла
	сохраняет в файл с расширением .acr
	"""
	if fn[-4:] != '.acr': fn += '.acr'
	if os.path.exists(fn):
		if replace == False:
			raise IOError, 'File %s already exist. Change file name or use replace=True argument' % fn
	f = open(fn, 'w')
	f.write(str(obj.res))
	f.close()


def loadRes(fn):
	"""
	Загружает результаты расчёта из файла
	"""
	if fn[-4:] != '.acr': fn += '.acr'
	f = open(fn, 'r')
	r = eval(f.read())
	f.close()
	return r


def save(obj, fn, replace=False):
	"""
	Сохраняет объект cliDat вместе с результатами расчётов если они есть
	"""
	if obj.__name__ == 'cliData':
		saveDat(obj, fn, replace)
		if obj.res != {}:
			saveRes(obj, fn, replace)
	elif obj.__name__ == 'metaData':
		saveStList(obj, fn, replace)


def load(fn):
	"""
	Загружает объект cliDat вместе с результатами расчётов
	"""

	if fn[-4:] != '.acl':
		aco = loadDat(fn)
		try:
			aco.res = loadRes(fn)
		except IOError:
			pass
	else:
		aco = loadStList(fn)
	return aco


def saveStList(obj, fn, replace=False, ignoreExisting=False):
	"""
	сохраняет набор данных.
	Покаждому объекту acd + acr (данные + метаинформация + результаты расчётов)
	"""
	import os.path
	assert obj.__name__ == 'metaData', 'wrong object type'
	if fn[-4:] != '.acl': fn += '.acl'
	if os.path.exists(fn):
		if replace == False:
			raise IOError, 'File %s already exist. Change file name or use replace=True argument' % fn
	abspath = os.path.abspath(fn)
	pth, filename = os.path.split(abspath)
	f = open(abspath, 'w')
	stl = ','.join([str(st.meta['ind']) for st in obj])
	txt = "# %s \n%s \n%s \n" % ("набор данных без описания", str(obj.meta), stl)
	f.write(txt)
	f.close()
	for st in obj:
		try:
			scrfn = pth + '\\' + str(st.meta['ind'])
			save(st, scrfn, replace)
		except IOError:
			if ignoreExisting == True:
				continue
			else:
				raise IOError, 'File %s already exist. Use ignoreExisting=True argument' % scrfn


def loadStList(fn):
	from altCliCore import config, metaData
	import os.path
	if fn[-4:] != '.acl': fn += '.acl'
	abspath = os.path.abspath(fn)
	pth, filename = os.path.split(abspath)
	f = open(fn, 'r')
	objlist = []
	for line in f.readlines():
		if line[0] == '#': continue
		if line[0] == '{':
			meta = eval(line)
			continue
		for dfn in line.split(','):
			try:
				src = pth + '\\' + dfn.strip()
				objlist.append(load(src))
			except IOError:
				print 'fail to load %s'%src
	cfg = config()
	cfg.get = None # Зануляем ф-ю загрузки новых данных
	cfg.getMeta = None # И ф-ю загрузки методанных
	acl = metaData(meta)
	acl.stList = objlist
	acl.maxInd = len(acl.stList)
	return acl



#===============================================================================
# def saveConfig():
#    pass
# 
# def loadConfig():
#    pass
#===============================================================================
