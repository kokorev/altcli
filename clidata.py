# coding=utf-8
"""
Модуль работы с базой климатических данных
реализует функции выборки данных из базы по заданным параметрам,
функции расчёта основных климатических характеристик,
функции визуализации результатов
"""
__author__ = 'Vasily Kokorev'
__email__ = 'vasilykokorev@gmail.com'
__version__ = '2.0 beta'

from common import *
import clicomp as cc
import numpy as np

def saveRes(method):
	import functools
	"""
	Декоратор. Сохраняет результат работы функции в словарь self.res
	Ключ слваря составляется по форме "имя функции--список значений аргументов через запятую"
	"""
	@functools.wraps(method)
	def wrapper(self, *args, **kwargs):
		dictId = getSaveResId(method, *args, **kwargs)
		result = method(self, *args, **kwargs)
		if self.__name__ == 'yearData':
			# если функцию вызвал объект yearData не имеющий родителся
			# то сохраняем результат в self.res и на этом заканчиваем
			# если self имеет родителя
			# то сохраняем результат в self.res и в self.parent.res
			# при этом во втором случае ключ словаря имеет приставку 'year-%i-' % self.year
			if self.parent == None:
				self.res.update({dictId:result})
			else:
				self.res.update({dictId:result})
				dictId = 'year-%i-' % self.year + dictId
				self.parent.res.update({dictId:result})
		else:
			self.res.update({dictId:result})
		return result
	return wrapper

def timeit(method):
	def timed(*args, **kw):
		import time
		ts = time.clock()
		result = method(*args, **kw)
		te = time.clock()
		#print '%r (%r, %r) %2.2f sec' %(method.__name__, args, kw, te-ts)
		#print '%r %3.3f sec' %(method.__name__, te-ts)
		return result
	return timed

def getCacheId(method, *args, **kwargs):
	"""
	функция принимает метод и его аргументы, а возвращает индификатор под которым
	результаты расчёта этого метода с этими параметрами были записаны в словарь
	Ключ слваря составляетьс по форме "имя функции--список значений аргументов через запятую"
	"""
	dId = method.__name__ + '--'
	for s in args: dId += str(s) + ','
	for s in kwargs: dId += str(s) + ','
	return dId[0:-1]

def cache(method):
	import functools
	"""
	Декоратор. То же что и saveRes, но кеширующий
	"""
	@functools.wraps(method)
	def wrapper(self, *args, **kwargs):
		dictId = getCacheId(method, *args, **kwargs)
		if dictId in self.res:
			result = self.res[dictId]
		else:
			result = method(self, *args, **kwargs)
			if self.__name__ == 'yearData':
				# если функцию вызвал объект yearData не имеющий родителся
				# то сохраняем результат в self.res и на этом заканчиваем
				# если self имеет родителя
				# то сохраняем результат в self.res и в self.parent.res
				# при этом во втором случае ключ словаря имеет приставку 'year-%i-' % self.year
				if self.parent == None:
					self.res.update({dictId:result})
				else:
					self.res.update({dictId:result})
					dictId = 'year-%i-' % self.year + dictId
					self.parent.res.update({dictId:result})
			else:
				self.res.update({dictId:result})
		return result
	return wrapper


class cliData:
	"""
	Класс реализующий функции загрузки и обработки климатических данных не зависящих от их типа
	"""
	@timeit
	def __init__(self, meta, gdat, cfg=None):
		"""
		Для создания объекта надо передать словарь с метоинформацией meta={'ind':20274, 'dt':'temp', ...}
		и указатель на cfg или массив с данными gdat
		gdat=[[year, [val1, val2, ..., val12]], [...]]
		cfg=config()
		"""
		if cfg == None: cfg = config()
		self.cfg = cfg
		self.__name__ = 'cliData'
		self.res = dict()
		self.setSeasons = self.cfg.setSeasons
		self.yearObjects=dict()
		self.precision=2
		self.seasonsCache=dict()
		# Проверяем есть ли в словаре все необходимые значения
		try:
			a = meta['ind']
		except KeyError:
			print "в meta не указано ind"
			raise KeyError
		try:
			meta['dt'] = cfg.elSynom[meta['dt']]
		except KeyError:
			pass
		# проверяем есть ли в словаре годы начала и конца, если нет устанавливаем
		try:
			a = meta['yMin']
		except KeyError:
			meta['yMin'] = self.cfg.yMin
		try:
			a = meta['yMax']
		except KeyError:
			meta['yMax'] = self.cfg.yMax
		self.meta = meta
		self.filledValue=-999.99
		d=[ln for ln in gdat if ln[1].count(None)<12]
		try:
			self.data=np.ma.masked_values([strdat[1] for strdat in d], None, copy=True)
		except TypeError:
			self.data=np.ma.array([strdat[1] for strdat in d])
		else:
			np.place(self.data, np.ma.getmaskarray(self.data), [self.filledValue])
		self.yList=[strdat[0] for strdat in d]
		if len(self.yList) == 0: raise ValueError, 'Не пропущенные значения отсутствуют'
		self.timeInds={y:i for i,y in enumerate(self.yList)}
		self.yMin, self.yMax = min(self.yList), max(self.yList)
		if meta['yMin'] == -1: meta['yMin'] = self.yMin
		if meta['yMax'] == -1: meta['yMax'] = self.yMax
#		self.minInd = 0
#		self.maxInd = len(self.yList)

	#TODO: add __deepcopy__ function

	@staticmethod
	@timeit
	def load(fn):
		"""
		Загружает объект cliDat из файла
		"""
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

	@timeit
	def __getitem__(self, item):
		"""
		Системная функция отвечающая за обработки оператора []
		возвращает экземпляр yearData
		"""
		if isinstance(item, slice):
			#indices = item.indices(len(self))
			#print item.indices()
			gdat = []
			start = item.start if item.start >= self.yMin else self.yMin
			stop = item.stop if item.stop <= self.yMax else self.yMax
			for year in range(start, stop):
				if self[year] == None:continue
				gdat.append([year, list(self[year].data)])
			return cliData(dict(self.meta), gdat, cfg=self.cfg)
		else:
			if item in self.timeInds:
				if item in self.yearObjects:
					val=self.yearObjects[item]
				else:
					val=yearData(item,self)
					self.yearObjects[item]=val
			else:
				self.cfg.logThis("нет данных для года " + str(item) + " на станции" + str(self.meta['ind']))
				val=yearData(item,self)
				self.yearObjects[item]=val
		return val



	def __iter__(self):
		self.thisInd = self.yMin
		return self


	def next(self):
		if self.thisInd > self.yMax: raise StopIteration
		ret = self[self.thisInd]
		self.thisInd += 1
		return ret


	def __str__(self):
		"""
		Функция конвертации в строку. В заголовке записываються номер и координаты станции, год за который записаны данные
		Далее после разделитьеля идут данные на доной на каждой строке записываеться номер годи а данные за 12 месяцев
		Разделитель - табуляция
		"""
		resStr = "Ind:" + str(self.meta['ind']) + "\r"
		resStr += "lat:" + str(self.meta["lat"]) + "\r"
		resStr += "lon:" + str(self.meta["lon"]) + "\r"
		resStr += "Years:" + str(self.yMin) + "-" + str(self.yMax) + "\r"
		resStr += "===============================================================\r"
		for y in self.data:
			resStr += str(y[1])
		return resStr


	def __len__(self):
		""" len(cliData) возвращает количетво лет (в т.ч. пустые) """
		return len(self.yList)


	def __contains__(self, item):
		""" обработка оператора in """
		return False if self[item] == None else True


	def eq(self, other):
		"""
		возвращает self==other (аналог __eq__)
		"""
		if self.yList != other.yList:
			return False
		for y in self.yList:
			if self[y].eq(other[y]) == False:
				break
		else:
			return True
		return False


	def clearcache(self):
		"""
		Очищает кэш от сохранённых значений. необходимо вызывать если изменились исходные данные
		"""
		self.res = dict()


	@property
	@cache
	def datapass(self):
		"""
		процент пропущенных данных
		"""
		obs=np.ma.count(self.data)
		passes=np.ma.count_masked(self.data)
		return passes/((obs+passes)/100.)


	def setPeriod(self, yMin, yMax):
		yMin = self.meta['yMin'] if (yMin == -1) or (yMin < self.meta['yMin']) else yMin
		yMax = self.meta['yMax'] if (yMax == -1) or (yMax > self.meta['yMax']) else yMax
		return yMin, yMax, self.timeInds[yMin], self.timeInds[yMax]


	def getSeasonsData(self,seasons):
		"""
		Кэшируюшая функция получения данных по заданым сезонам
		может принимать как словарь {'название сезона': [список месяцов]} так и списоко имён сезонов
		"""
		res=dict()
		if type(seasons) is str: seasons=[seasons]
		if type(seasons) is list: seasons={sn:self.seasonsCache[sn]['mlist'] for sn in seasons}
		for sname,mlist in seasons.items():
			if sname in self.seasonsCache and self.seasonsCache[sname]['mlist']!=mlist:
				# имя сезона есть в списке сохранённых
				# но списко месяцев для не совпадает с заданым, перезаписываем с предупреждением
				print 'Warning! season %s will be redefine. Cache will cleaned :-('%sname
				self.seasonsCache[sname]['mlist']=mlist
				self.seasonsCache[sname]['dat']=self._calcSeasonData(mlist)
				self.clearcache()
			else:
				# сезон используется впервые, добавляем его в кэш
				self.seasonsCache[sname]=dict()
				self.seasonsCache[sname]['mlist']=mlist
				self.seasonsCache[sname]['dat']=self._calcSeasonData(mlist)
			# берём значение из кэша
			res[sname]=self.seasonsCache[sname]['dat']
		return res


	@cache
	@timeit
	def _calcSeasonData(self,mlist):
		"""
		Возвращает значения за сезон
		{'название сезона': [массив значений(маскированный), список лет в массиве]}
		"""
		seasIndList=[]
		iStart,iStop=0,len(self.data)
		sdat=[]
		sYlist=[]
		res=np.zeros(len(self.yList))
		for m in mlist:
			if 1<=m<=12:
				seasIndList.append([0,m-1])
			elif m>12:
				seasIndList.append([1,m-12-1])
				if iStop==len(self.data): iStop-=1
			elif m<0:
				seasIndList.append([-1,12+m])
				if iStart==0: iStart+=1
			else:
				print mlist
				raise ValueError, 'Неверно задан сезон'
		for i in range(0,len(self.data)):
			if i<iStart or i>=iStop:
				sdat.append([None for l,mn in seasIndList])
			else:
				sdat.append([(self.data[i+l,mn] if self.data.mask[i+l,mn]==False else None) for l,mn in seasIndList])
		sdatMasked=np.ma.masked_values(sdat, None)
		np.place(sdatMasked, np.ma.getmaskarray(sdatMasked), [-999.99])
		return sdatMasked


	@cache
	def getSeasonSeries(self, season, yMin= -1, yMax= -1):
		"""
		возвращает ряд средних по сезоном для каждого года в интервале
		Аллиас устаревшей retS_avgData
		"""
		yMin, yMax,i1,i2 = self.setPeriod(yMin, yMax)
		dat,yList=self.getSeasonsData(season)
		return [round(d.mean(), self.precision) for d in dat[i1:i2+1]],yList



#	@cache
#	def retS_avgData(self, yMin= -1, yMax= -1, seasToCalc=False):
#		"""
#		возвращает ряд средних по сезоном для каждого года в интервале
#		"""
#		yMin, yMax = self.setPeriod(yMin, yMax)
#		res = {y.year:y.s_avg() for y in self if ((y.year <= yMax) and (y.year >= yMin))} # and (y.datapass == 0)
#		yList = [key for key in res]
#		return res, yList


#	@cache
#	def retIn2dimArr(self, addNone=False):
#		"""
#		Возвращает все данные в двух одномерных массивах [данные],[время],[даты]
#		Время в сквозной нумерации
#		Для построения графиков, например
#		addNone задаёт должны ли быть пропуски в возвращаемом массиве значений
#		"""
#		from datetime import date
#		dat, time, datearr = [], [], []
#		for y in self:
#			for mn in range(1, 13):
#				if y[mn] != None or addNone: # если значение не пропущено или задана настройка добавление пропусков
#					dat.append(y[mn])
#					time.append(mn + (y.year - self.yMin) * 12)
#					datearr.append(date(y.year, mn, 1))
#		return time, dat, datearr

	@timeit
	@cache
	def norm(self, yMin= -1, yMax= -1):
		"""
		функция считает норму температуры за каждый месяц в заданый период на заданной станции
		in: minY,maxY - начальный и конечный года периода за который считаеться норма. включительно.
		если не заданно расчитываеться за весь период self.data
		out: res(12)  - нормы за каждый месяц
		"""
		yMin,yMax,i1,i2 = self.setPeriod(yMin, yMax)
		res=np.ma.average(self.data[i1:i2+1,:], axis=0)
		return [round(v,self.precision) for v in res]


	@cache
	@timeit
	def s_norm(self, yMin= -1, yMax= -1, seasToCalc=False):
		"""
		Расчитывает среднесезонную норму
		Принимет:
			yMin, yMax - int, года начала и конца периода расчтё нормы
			seasToCalc - list of str, dict сезоны по которым нужно расчитать норму
			при использовании данной ф-ии через altCli_calc необходимо указать ТОЛЬКО один сезон, например ['winter']
		Возвращает:
			res - dict, значение нормы для каждого сезона {сезон: число, ...}
		"""
		if seasToCalc == False:	seasToCalc = [s for s in self.seasonsCache]
		yMin,yMax,i1,i2 = self.setPeriod(yMin, yMax)
		print yMin,yMax,i1,i2
		sdat=self.getSeasonsData(seasToCalc)
		res=dict()
		for sname in seasToCalc:
			dat=sdat[sname]
			res[sname]=round(dat[i1:i2+1,:].mean(), self.precision)
		return res


	@cache
	#TODO: resInList используется неправлиьно, исправить
	def trendParam(self, funct, param, yMin, yMax, converter=None):
		"""
		расчитывает межгодовой тренд какого-либо параметра
		принимает:
			funct - str, имя функции объекта yearData расчитывающей параметр, тренд которого надо вычислить
			param - list, параметры с которой надо вызвать ф-ю funct
			yMin, yMax - int, года начала и конца периода за который расчитывается тренд
			resInList - функция, если ф-я funct возвращает список,
			то результат работы будет передоваться этой функции, которая должна возвращать только одно число
		Возвращает:
			slope - float, slope of the regression line
			intercept - float, intercept of the regression line
			r-value - float, correlation coefficient
			p-value - float, two-sided p-value for a hypothesis test whose null hypothesis is that the slope is zero.
			stderr - float, Standard error of the estimate
			res,time - list, одномерные массивы по которым был расчитан тренд
		"""
		from scipy import stats
		vals, time = [], []
		for y in range(yMin, yMax + 1):
			yobj = self[y]
			if yobj != None:
				f = getattr(yobj, funct)
				res = f(*param)
				if converter is not None:
					res=converter(res)
				if res is not None or res != False:
					vals.append(res)
					time.append(y)
		vals=[v for t,v in zip(time,vals) if v!=None]
		time=[t for t,v in zip(time,vals) if v!=None]
		slope, intercept, r_value, p_value, std_err = stats.linregress(time, vals)
		return slope, (intercept, r_value, p_value, std_err), vals, time



	@cache
	def s_trend(self, yMin= -1, yMax= -1, seasToCalc=False):
		"""
		расчитывает многолетний тренд сезонной температуры
		Принимет:
			yMin, yMax - int, года начала и конца периода расчтё нормы
			seasToCalc - list, список сезонов по которым нужно расчитать норму (если не нужны все сезоны)
		Возвращает:
			res - dict, словарь со значениями для каждого сезона {сезон: (slope, intercept, r_value, p_value, std_err),...}
			где:
				slope - float, slope of the regression line
				intercept - float, intercept of the regression line
				r-value - float, correlation coefficient
				p-value - float, two-sided p-value for a hypothesis test whose null hypothesis is that the slope is zero.
				stderr - float, Standard error of the estimate
		"""
		import math
		from scipy import stats
		if seasToCalc == False:
			seasToCalc = self.cfg.sortedSeasons
		yMin, yMax = self.setPeriod(yMin, yMax)
		yearSeasonAvg, yList = self.retS_avgData(yMin, yMax)
		res = dict()
		for s in seasToCalc:
			dat = [yearSeasonAvg[key][s] for key in yearSeasonAvg if yearSeasonAvg[key][s] != None]
			ylst = [y for key, y in zip(yearSeasonAvg, yList) if yearSeasonAvg[key][s] != None]
			slope, intercept, r_value, p_value, std_err = stats.linregress(ylst, dat)
			if math.isnan(slope):slope = None
			res[s] = (slope, intercept, r_value, p_value, std_err)
		return res


	@cache
	@timeit
	def anomal(self, norm_yMin, norm_yMax, yMin= -1, yMax= -1):
		"""
		Считает аномалии от нормы для каждого месяца каждого года
		Принимает:
			norm_yMin, norm_yMax - за это период расчитывается норма
			yMin, yMax - за этот период расчитываются аномалии (по умолчанию весь доступный период)
		Возвращает:
			res - dict, года - ключи словарая, значения - списки аномалий для каждого месяца этого года
		"""
		#todo: было бы логичнее было бы использовать np.ma.anom(), но оно не работет осям
		# обсуждение топика https://github.com/numpy/numpy/issues/2814
		yMin,yMax,i1,i2 = self.setPeriod(yMin, yMax)
		normList = self.norm(norm_yMin, norm_yMax)
		res=[]
		for y in range(yMin,yMax+1):
			if y in self.timeInds:
				i=self.timeInds[y]
				line=self.data[i]-normList
				res.append([(round(line[m],self.precision) if self.data.mask[i,m]!=True else self.filledValue) for m in range(12)])
			else:
				res.append([self.filledValue]*12)
		return np.ma.masked_values(res, self.filledValue, copy=True)



	@cache
	def s_anomal(self, normMinY, normMaxY, yMin= -1, yMax= -1, seasToCalc=False):
		"""
		Считает сезонные аномалии для каждого года
		Принимает:
			norm_yMin, norm_yMax - за это период расчитывается норма
			yMin, yMax - за этот период расчитываются аномалии (по умолчанию весь доступный период)
			seasToCalc - list of str | dict | str список сезонов по которым нужно расчитать норму
		Возвращает:
			res - dict, {сезон: {год: [список аномалий за каждый месяц], ...}, ...}
		"""
		if seasToCalc == False:	seasToCalc = [s for s in self.seasonsCache]
		sdat=self.getSeasonsData(seasToCalc)
		yMin,yMax,i1,i2 = self.setPeriod(yMin, yMax)
		res=dict()
		for sname in seasToCalc:
			norm=self.s_norm(normMinY, normMaxY, seasToCalc=sname)
			dat=self.getSeasonSeries(sname)
			res[sname]=[[round(dat[i]-norm, self.precision) for i in range(i1,i2+1)]]
		return res


	@cache
	def meanAnomal(self, norm_yMin, norm_yMax, yMin= -1, yMax= -1):
		"""
		 Считает среднемноголетние аномалии для каждого месяца
		 Принимает:
			norm_yMin, norm_yMax - за это период расчитывается норма
			yMin, yMax - за этот период расчитываются аномалии (по умолчанию весь доступный период)
		Возвращает:
			res - list, среднемноголетние аномалии за каждый месяц
		"""
		yMin,yMax,i1,i2 = self.setPeriod(yMin, yMax)
		dat=self.anomal(norm_yMin, norm_yMax, yMin, yMax)
		res=np.ma.average(dat, axis=0)
		return res

	#TODO: убрать одну из ф-ий trend или trendParam
	@cache
	def trend(self, yMin= -1, yMax= -1):
		"""
		 Ф-я рассчитывает наклон многолетнего тренда среднегодовой температуры
		 Возвращает наклон, ряд значений среднегодовой температуры, ряд времени
		 Послдение два возвращаемых значений можно использовать для расчёта
		 slope, intercept, r_value, p_value, std_err = stats.linregress(time,res)
		"""
		from scipy import stats
		yMin, yMax = self.setPeriod(yMin, yMax)
		res, time = [], []
		for tr, tt in [[self[y].avg, y] for y in range(yMin, yMax + 1) if self[y] != None]:
			if tr != None:
				res.append(tr)
				time.append(tt)
		if len(res) < 15:
			return [False, False, False, False]
		else:
			slope, intercept, r_value, p_value, std_err = stats.linregress(time, res)
		return slope, intercept, res, time


	@cache
	def trendMatrix(self, minTrlen=20, season={'year':range(1, 13)}):
		"""
		Расчитывает матрицу зависимости велечины тренда от года начала тренда и его длинны
		Возвращает три двумерные numPy массива x,y,z
		"""
		import numpy as np
		from scipy import stats
		self.cfg.setSeasons(season)
		sesname = season.keys()[0]
		y = range(self.yMin, self.yMax + 1)
		y_minLim = self.yMin
		y_maxLim = self.yMax - minTrlen
		x_minLim = minTrlen
		x_maxLim = self.yMax - self.yMin
		y.reverse()
		ty = []
		for yStart in range(y_minLim, y_maxLim + 1): # для каждого года начала
			tx = []
			for trLen in range(x_minLim, x_maxLim + 1) : # для каждой проболжительности тренда
				if (yStart + trLen) <= self.yMax:
					slope, intercept, r_value, p_value, std_err = self.s_trend(yStart, (yStart + trLen))[sesname]
				else:
					slope = 0
				yi = yStart - y_minLim
				xi = trLen - x_minLim
				tx.append(slope)
			ty.append(tx)
		x = np.array([[tl for tl in range(x_minLim, x_maxLim + 1)] for tyear in range(self.yMin, (self.yMax - minTrlen) + 1)])
		y = np.array([[tyear for tl in range(x_minLim, x_maxLim + 1)] for tyear in range(self.yMin, (self.yMax - minTrlen) + 1)])
		z = np.array(ty)
		return x, y, z

	@cache
	def std(self, yMin= -1, yMax= -1):
		"""
		Считает стандартное отклонение
		Принимает:
			yMin, yMax - период расчёта (по умолчанию весь доступный период)
		Возвращает:
			ndarray, standard deviation, a measure of the spread of a distribution, of the array elements
		"""
		from numpy import std
		#minY, maxY, minInd, maxInd = self.minmaxInd(minY, maxY)
		yMin, yMax = self.setPeriod(yMin, yMax)
		return std([self[year].avg for year in range(yMin, yMax + 1) if self[year] != None and self[year].datapass == 0])

	@cache
	def s_changePoint(self, mpr=30, mintr=0.008, minlen=20, seasToCalc=False):
		"""
		находит критическую точку
		"""
		from scipy.stats import ks_2samp
		from scipy import stats
		if seasToCalc == False:
			if len(self.cfg.seasons) > 1:
				raise ValueError, "если в cfg.seasons > 1 сезона то seasToCalc должен быть задан"
			elif len(self.cfg.seasons) == 1:
				seasToCalc = self.cfg.seasons.keys()[0]
		vals, years = self.retS_avgData(seasToCalc=seasToCalc)
		vals = [v[seasToCalc] for k, v in vals.items()]
		nvals = [v for v in vals if v != None]
		oldnums = [i for i, x in enumerate(vals) if x != None]
		avgv = sum(nvals) / len(nvals)
		cs = []
		csum = 0
		for v in nvals:
			csum = csum + (avgv - v)
			cs.append(csum)
		rescs = max([abs(p) for p in [max(cs), min(cs)] if p != None])
		try:
			rescsind = cs.index(rescs)
		except ValueError:
			rescsind = cs.index(rescs * -1)
		#point = oldnums[rescsind]
		point = years[oldnums[rescsind]]
		##if abs(point-len(vals))<10 or point<10: point=None
		vals1, vals2 = nvals[:rescsind], nvals[rescsind:]
		time1, time2 = oldnums[:rescsind], oldnums[rescsind:]
		if len(vals1) < minlen or len(vals2) < minlen:
			point, zn, kstest, pvalue = None, None, None, None
			slope1, slope2 = None, None
		else:
			slope1, intercept1, r_value1, p_value1, std_err1 = stats.linregress(time1, vals1)
			slope2, intercept3, r_value2, p_value2, std_err2 = stats.linregress(time2, vals2)
			#if max([abs(slope1), abs(slope2)]) < mintr: point = None
			#if (abs(slope1) / 100) * (100 + mpr) > abs(slope2) > (abs(slope1) / 100) * (100 - mpr): point = None
			if slope1 > slope2:
				zn = -1
			else:
				zn = 1
			kstest, pvalue = ks_2samp(vals1, vals2)
		return point, zn, kstest, pvalue, slope1, slope2



class yearData:
	"""
	Класс для работы с данными по одному году.
	свойства:
		year - год, данные за который содержит объект
		stNum - номер станции, данные которой содержит объект
		vals - 12 значений температуры за каждый месяц года в виде списка
		time - номера месяцев (если всё нет ошибок то ==range(1,13))
		data - двумерный массив данных [time,vals]
	ф-ии с декоратором @property перед def: возвращают только одно значение
	и могут вызываться как свойства
	"""
	def __init__(self, year, parent):
		self.__name__ = 'yearData'
		self.year = year
		self.parent = parent
		if year in parent.timeInds:
			self.data=parent.data[parent.timeInds[year]]
		else:
			self.data=np.ma.masked_values([parent.filledValue]*12, parent.filledValue)
		self.res = dict()
		self.precision=parent.precision
		self.meta=self.parent.meta


	def __str__(self):
		rList = list(self.data) # копируем лист!
		rList.insert(0, self.year)
		strList = [str(s) for s in rList]
		resstr = "\t".join(strList)
		resstr = resstr + "\n"
		return resstr


	def __getitem__(self, month):
		"""
		Функция отвечает за обработку оператора извлечения среза [].
		При этом значение месяца может менять в пределах от -12 до 24 исключая ноль
		Отрицательные значения соответсвуют прошлому году, значения больше 12 следующему.
		Не стоит злоупотреблять функцией получения данных по следующему и прошлому году, она медленная.
		"""
		retval = None
		monthDict = {'january':1, 'february':2, 'march':3, 'april':4, 'may':5, 'june':6, 'july':7, 'august':8, 'september':9, 'october':10, 'november':11, 'december':12}
		if type(month) == str:
			rmonth = monthDict[str.lower(month)]
		elif type(month) == int:
			rmonth = month
		else:
			rmonth = int(month)
		assert - 13 < rmonth < 25 and rmonth != 0, "номер месяца должен лежать в промежутке от 1 до 12"
		if 1 <= rmonth <= 12:
			retval = self.data[rmonth - 1]
		else :
			if rmonth >= 13:
				realMonth = rmonth - 12
				realYear = int(self.year + 1)
			elif rmonth < 0:
				realMonth = 13 + rmonth
				realYear = int(self.year - 1)
			if self.parent != None:
				try:
					retval = self.parent[realYear][realMonth]
				except TypeError:
					retval = None
			else:
				retval = None
		return retval if retval!=self.data.fill_value else None


	def getSeasonsData(self,seasons):
		"""
		Возвращает данные по каждому сезону в виде словаря
		{'название сезона': [данные по месяцам в хронологическом порядке]}
		"""
		res=dict()
		for sname,mlist in seasons.item():
			mlist.sort()
			res[sname]=[self[m] for m in mlist]
		return res


	def __iter__(self):
		self.thisInd = 1
		return self


	def __len__(self):
		return 12


	def next(self):
		if self.thisInd > 12: raise StopIteration
		ret = self[self.thisInd]
		self.thisInd += 1
		return ret


	def eq(self, other):
		""" проверяет объекты на идеентичность данных """
		return (not False in (self.data == other.data)) and (self.year == other.year)


	def getMonthVal(self, year, month):
		return self.cfg.get(self.parent.meta['dt'], self.parent.meta['ind'], year, month)


	@property
	def datapass(self):
		return round(self.missedMonth / (12 / 100.0), self.precision)


	@property
	def missedMonth(self):
		if self.data.mask.any():
			r=sum([1 for v in self.data.mask if v==True])
		else:
			r=0
		return r


	def s_ampl(self, seasToCalc=False):
		"""
		Расчитывает амплитуду по сезонам
		"""
		res=dict()
		if seasToCalc==False: seasToCalc=[sn for sn in self.parent.seasonsCache]
		dat=self.parent.getSeasonsData(seasToCalc)
		yInd=self.parent.timeInds[self.year]
		for sname in seasToCalc:
			if dat[sname][yInd].mask.any():
				res[sname]=None
			else:
				res[sname]=cc.ampl(dat[sname][yInd],precision=self.precision)
		return res


	@property
	def ampl(self):
		""" возвращает амплитуду значений за данный год """
		if self.data.mask.any():
			r=None
		else:
			vals=[v if not m else None for v,m in zip(self.data,self.data.mask)]
			r=cc.ampl(vals)
		return r


	def s_avg(self, seasToCalc=False):
		""" возвращает среднюю температуру за каждый сезон """
		res=dict()
		if seasToCalc==False: seasToCalc=[sn for sn in self.parent.seasonsCache]
		dat=self.parent.getSeasonsData(seasToCalc)
		yInd=self.parent.timeInds[self.year]
		for sname in seasToCalc:
			if dat[sname][yInd].mask.any():
				res[sname]=None
			else:
				res[sname]=cc.avg(dat[sname][yInd],precision=self.precision)
		return res


	@property
	def avg(self):
		""" возвращает среднегодовую температуру """
		if self.missedMonth==0:
			r=round(self.data.mean(),self.precision)
		else:
			r=None
		return r


	@saveRes
	def sumMoreThen(self, x):
		""" Возвращает сумму значений больше X """
		r=cc.sumMoreThen([v if not m else None for v,m in zip(self.data, self.data.mask)],x,precision=self.precision)
		return r


	@saveRes
	def sumLessThen(self, x):
		""" Возвращает сумму значений больше X """
		r=cc.sumLessThen([v if not m else None for v,m in zip(self.data, self.data.mask)],x,precision=self.precision)
		return r


	@saveRes
	def s_sumMoreThen(self, x, seasToCalc=False):
		""" Возвращает кортеж значений больше Х для каждого сезона """
		res=dict()
		if seasToCalc==False: seasToCalc=[sn for sn in self.parent.seasonsCache]
		dat=self.parent.getSeasonsData(seasToCalc)
		yInd=self.parent.timeInds[self.year]
		for sname in seasToCalc:
			if dat[sname][yInd].mask.any():
				res[sname]=None
			else:
				res[sname]=cc.sumMoreThen(dat[sname][yInd],x, precision=self.precision)
		return res

if __name__ == "__main__":
	acd=cliData.load('test')
	res,yList=acd.anomal(1961,1990)
	#{'summer':-0.542, 'winter':-29.51, 'year':-16.095}
	#print acd.s_norm(1961,1964, {"year": range(1, 13), "summer": [6, 7, 8], "winter": [-1, 1, 2]})

