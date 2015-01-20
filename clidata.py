# coding=utf-8
"""
Custom types for monthly climate timeseries
"""
__author__ = 'Vasily Kokorev'
__email__ = 'vasilykokorev@gmail.com'

from common import *
import clicomp as cc
import numpy as np
from scipy import stats
from math import isnan
import os
import functools
import logging
import copy

cfg=config()
logging.basicConfig(format = u'%(filename)s[LINE:%(lineno)d]# %(levelname)-8s [%(asctime)s]  %(message)s', level = logging.DEBUG)


def timeit(method):
	def timed(*args, **kw):
		import time
		ts = time.clock()
		result = method(*args, **kw)
		te = time.clock()
		print '%r (%r, %r) %2.2f sec' %(method.__name__, args, kw, te-ts)
		print '%r %3.3f sec' %(method.__name__, te-ts)
		return result
	return timed

def getCacheId(method, *args, **kwargs):
	"""
	decorator that implement caching for cliData
	"""
	dId = method.__name__ + '--'
	for s in args: dId += str(s) + ','
	for s in kwargs: dId += str(s) + ','
	return dId[0:-1]

def cache(method):
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

# def saveRes(method):
# 	"""
# 	deprecated version of @cache
# 	"""
# 	@functools.wraps(method)
# 	def wrapper(self, *args, **kwargs):
# 		dictId = getSaveResId(method, *args, **kwargs)
# 		result = method(self, *args, **kwargs)
# 		if self.__name__ == 'yearData':
# 			# если функцию вызвал объект yearData не имеющий родителся
# 			# то сохраняем результат в self.res и на этом заканчиваем
# 			# если self имеет родителя
# 			# то сохраняем результат в self.res и в self.parent.res
# 			# при этом во втором случае ключ словаря имеет приставку 'year-%i-' % self.year
# 			if self.parent == None:
# 				self.res.update({dictId:result})
# 			else:
# 				self.res.update({dictId:result})
# 				dictId = 'year-%i-' % self.year + dictId
# 				self.parent.res.update({dictId:result})
# 		else:
# 			self.res.update({dictId:result})
# 		return result
# 	return wrapper


class noDataException(Exception):
	"""
	missing data exception. To be implemented
	"""
	def __init__(self, yMin,yMax):
		self.yMin = yMin
		self.yMax = yMax
	def __str__(self):
		return "There is no date avaliable in %i - %i interval on this station"%(self.yMin,self.yMax)




class cliData:
	"""
	Custom data type for monthly climate data in a point
	"""
	def __init__(self, meta, gdat, fillValue=None):
		"""
		meta - basic metadata dictionary, should contain at least 'dt' and 'ind' keys for climate parameter and station index
		'ind' could be None for region mean data etc
		'lat' and 'lon' parameters are recommended
		meta={'ind':20274, 'dt':'temp', ...}
		gdat - monthly data
		gdat=[[year, [val1, val2, ..., val12]], [...]]
		fillValue - missing data flag for gdat array
		cfg=config() - exist mostly for backwards compatibility reasons
		"""
		#todo: принимать numpy array в качестве gdat
		# if cfg == None: cfg = config()
		# self.cfg = cfg
		self.__name__ = 'cliData'
		self.res = dict()
		# self.setSeasons = self.cfg.setSeasons
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
		self.meta = meta
		self.filledValue=-999.99 if fillValue is None else fillValue
		d=[ln for ln in gdat if not np.all(np.equal(ln[1], fillValue))]
		try:
			self.data=np.ma.masked_values([strdat[1] for strdat in d], fillValue)
			#self.noGaps=False
		except TypeError:
#			print 'It look like there is no gaps in your data. Are you sure??'
			self.data=np.ma.masked_values([strdat[1] for strdat in d], -999.99)
			#raise
			# если нет пропусков
			#self.data=np.array([strdat[1] for strdat in d])
			#self.noGaps=True
		if fillValue is None: np.place(self.data, np.ma.getmaskarray(self.data), [self.filledValue])
		#маска всегда должны быть массивом, иначе сложно проверить не пропущено ли значение
		self.data.mask=np.ma.getmaskarray(self.data)
		self.yList=[strdat[0] for strdat in d]
		if len(self.yList) == 0: raise ValueError, 'Не пропущенные значения отсутствуют'
		self.timeInds={y:i for i,y in enumerate(self.yList)}
		self.yMin, self.yMax = int(min(self.yList)), int(max(self.yList))
		self.meta['yMin'] = self.yMin
		self.meta['yMax'] = self.yMax
		self.meta['comment'] = ''


	def __getitem__(self, item):
		"""
		returns yearData instance for single year and cliData instance for slice
		"""
		def createYearDataObj(self, item):
			"""
			Функция определяет какой класс использовать при создании объекта yearData в зависимости от типа данных
			"""
			if self.meta['dt'] in ['prec', 'pr']:
				r=prec_yearData(item,self)
			elif self.meta['dt'] in ['temp', 'tas']:
				r=temp_yearData(item,self)
			else:
				r=yearData(item,self)
			return r

		if isinstance(item, slice):
			start = item.start if item.start >= self.yMin else self.yMin
			stop = item.stop if item.stop <= self.yMax else self.yMax
			yMin,yMax,i1,i2=self._setPeriod(start,stop)
			dat=self.data[i1:i2+1].copy()
			yList=self.yList[i1:i2+1]
			gdat=[[y,list(dat[i].data)] for i,y in enumerate(yList)]
			cdo=cliData(dict(self.meta), gdat, fillValue=self.filledValue) #cfg=self.cfg,
			return cdo
		else:
			if item in self.timeInds:
				if item in self.yearObjects:
					val=self.yearObjects[item]
				else:
					val=createYearDataObj(self,item)
					self.yearObjects[item]=val
			else:
				logging.warning("нет данных для года " + str(item) + " на станции" + str(self.meta['ind']))
				val=createYearDataObj(self,item)
				self.yearObjects[item]=val
		return val


	#TODO: add __deepcopy__ function
#	def __deepcopy__(self):
#		"""	Возвращает копию объекта """
#		from copy import deepcopy

	@staticmethod
	def load(fn, results=False):
		"""
		load cliData instance from altCli plaintext internal format *.acd
		"""
		if fn[-4:] != '.acd': fn += '.acd'
		f = open(fn, 'r')
		# убирём строчки с коментариями из метоинформации
		txt = '\n'.join([line for line in f.readlines() if line.strip()[0]!='#'])
		stxt = txt.split('}')       # отделяем метаинформацию от данных
		metatxt = '\n'.join([line for line in stxt[0].split('\n')]) + '}'
		meta = eval(metatxt)
		dataInd=1
		if len(stxt)==3 and results:
			restxt = '\n'.join([line for line in stxt[0].split('\n')]) + '}'
			res = eval(restxt)
			dataInd=2
		else:
			res=dict()
		dat = []
		for line in stxt[dataInd].split('\n'):
			ln = line.strip()
			if ln == '': continue
			arr = [(float(v) if v != 'None' else -999.99) for v in ln.split('\t')]
			dat.append([int(arr[0]), arr[1:]])
		aco = cliData(meta, gdat=dat,fillValue=-999.99)
		aco.res=res
		return aco


	def save(self,fn, replace=False, results=False):
		"""
		save cliData instance to *.acd
		"""
		if fn[-4:] != '.acd': fn += '.acd'
		if os.path.exists(fn):
			if replace == False:
				raise IOError, 'File %s already exist. Change file name or use replace=True argument' % fn
		r = str(self.meta) + '\n'
		if results and len(self.res)>0:
			r+=str(self.res) + '\n'
		for y in self:
			if y.datapass==100:continue
			r += str(y)
		f = open(fn, 'w')
		f.write(r)
		f.close()


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
		for y in self:
			resStr += str(y)
		return resStr


	def __len__(self):
		""" len(cliData) возвращает количетво лет (в т.ч. пустые) """
		return len(self.yList)


	def __contains__(self, item):
		""" обработка оператора in """
		return item in self.yList


	def eq(self, other):
		"""
		возвращает self==other (аналог __eq__)
		"""
		if self.yList != other.yList:
			r=False
		if (self.data!=other.data).any():
			r=False
		else:
			r=True
		return r


	def timeMerge(self, other, breakingPoint=None, useSelfIfOverlap=None):
		"""
		Обединяет два объекта в один. Методанные копируются из объекта self
		@param other: cliData object
		@return:
		"""
		ml=self.yList+other.yList
		gdat1=[[y,list(v.filled(-999.99))] for y,v in zip(self.yList,self.data)]
		gdat2=[[y,list(v.filled(-999.99))] for y,v in zip(other.yList,other.data)]
		if gdat1[0][0]>gdat2[0][0]:
			gdat1,gdat2=gdat2,gdat1
		if useSelfIfOverlap is not None and breakingPoint is not None:
			raise ValueError, 'breakingPoint and useSelfIfOverlap could not be used together'
		if useSelfIfOverlap is True:
			breakingPoint=gdat1[-1][0]+1
		elif useSelfIfOverlap is False:
			breakingPoint=gdat2[0][0]
		if breakingPoint is not None:
			gdat1=[v for v in gdat1 if v[0]<breakingPoint]
			gdat2=[v for v in gdat2 if v[0]>=breakingPoint]
		gdat=gdat1+gdat2
		newYlist=[v[0] for v in gdat]
		assert len(set(newYlist))==len(newYlist), 'duplicating years'
		gdat.sort(key=lambda a:a[0])
		meta=dict(self.meta)
		meta['comment']+='merged with objects %s ; '%str(other.meta)
		return cliData(meta,gdat)



	def clearcache(self):
		"""
		There are only two hard things in Computer Science: cache invalidation and naming things.
		-- Phil Karlton

			That's why we just clear all of it if we suspect something.
		"""
		#todo: write an actual cache invalidation algorithm (very low priority)
		self.res = dict()


	@property
	@cache
	def datapass(self):
		"""
		percent of missing data
		"""
		obs=np.ma.count(self.data)
		passes=np.ma.count_masked(self.data)
		return passes/((obs+passes)/100.)


	def _setPeriod(self, yMin, yMax):
		"""
		@param yMin:
		@param yMax:
		@return:
		"""
		userYMin,userYMax=yMin,yMax
		yMin = self.meta['yMin'] if (yMin == -1) or (yMin < self.meta['yMin']) else yMin
		yMax = self.meta['yMax'] if (yMax == -1) or (yMax > self.meta['yMax']) else yMax
		while yMin not in self.timeInds:
			if not yMin<yMax: raise noDataException(userYMin,userYMax)
			yMin+=1
		iMin=self.timeInds[yMin]
		while yMax not in self.timeInds:
			if not yMin<yMax: raise noDataException(userYMin,userYMax)
			yMax-=1
		iMax=self.timeInds[yMax]
		return yMin, yMax, iMin, iMax


	def getSeasonsData(self,seasons):
		"""
		@param seasons: {'seasonName':[monthNumber1, monthNumber2, ...], 'seasonName2'}
		monthNumber [-12,0), (0,+24]
		monthNumber=1 January
		monthNumber=12 December
		monthNumber=-1 December, year-1
		monthNumber=13 January, year+1
		example {'winter':[-1,1,2], year:range(1,13)}
		@return: {seasName:{'dat':[[values for each month in season for each], ...], 'mlist':seasons[seasName]}, ... }
		"""
		res=dict()
		def workStrSeas(seas):
			if type(seas) is str:
				if seas in self.seasonsCache:
					season={seas:None}
				else:
					raise KeyError, "There is no season %s in seasonsCache. Set seasons in dict not string form"%seas
			return season
		teastedSeas=dict()
		if type(seasons) is list:
			for val in seasons:
				if type(val) is str:
					val=workStrSeas(val)
					teastedSeas.update(val)
				else:
					raise ValueError, "Seasons should be a list of string or dict"
		elif type(seasons) is str:
			teastedSeas.update(workStrSeas(seasons))
		elif type(seasons) is dict:
			for sname, mlist in seasons.items():
				if sname in self.seasonsCache:
					if mlist==self.seasonsCache[sname]['mlist']:
						teastedSeas.update({sname:None})
					else:
						print 'Warning! season %s will be redefine. Cache will cleaned :-('%sname
						self.seasonsCache[sname]=dict()
						self.clearcache()
				else:
					teastedSeas.update({sname:mlist})
		else:
			raise ValueError, "Seasons should be string, list of string or dict"
		for sname,mlist in teastedSeas.items():
			if mlist is not None:
				self.seasonsCache[sname]=dict()
				self.seasonsCache[sname]['mlist']=mlist
				self.seasonsCache[sname]['dat']=self._calcSeasonData(mlist)
			res[sname]=self.seasonsCache[sname]['dat']
		return res


	def setSeasons(self,seasons):
		"""	alias for backwards compatibility """
		self.getSeasonsData(seasons)


	@cache
	def _calcSeasonData(self,mlist):
		"""
		Возвращает значения за сезон (маскированный) индексы в котором соответствуют self.timeInds
		"""
		seasIndList=[]
		iStart,iStop=0,len(self.data)
		sdat=[]
		for m in mlist:
			if 1<=m<=12:
				seasIndList.append([0,m-1])
			elif 12<m<=24:
				seasIndList.append([1,m-12-1])
				if iStop==len(self.data): iStop-=1
			elif -12<=m<0:
				seasIndList.append([-1,12+m])
				if iStart==0: iStart+=1
			else:
				print mlist
				raise ValueError, 'Неверно задан сезон'
		for i,year in enumerate(self.yList):
			if i<iStart or i>=iStop:
				sdat.append([self.filledValue for l,mn in seasIndList])
			else:
				if not np.ma.all(self.data.mask):
					line=[(self.data[i+l,mn] if self.data.mask[i+l,mn]==False else self.filledValue) for l,mn in seasIndList]
				else:
					line=[self.data[i+l,mn] for l,mn in seasIndList]
				sdat.append(line)
		sdatMasked=np.ma.masked_values(sdat, self.filledValue)
		return sdatMasked


	def getSeasonsSeries(self, seasons):
		""" return mean season value for each year (sum if precip)
		"""
		dat=self.getSeasonsData(seasons)
		res=dict()
		for sn,d in dat.items():
			if self.meta['dt']=='prec':
				r=d.sum(axis=1)
			else:
				r=d.mean(axis=1)
			res[sn]=r
		return res


	def getParamSeries(self,functName, params=[], yMin=-1, yMax=-1, converter=None):
		"""
		return function value for each year
		@param functName: yearData method name
		@param params:  yearData method parameters
		@param yMin: start from year
		@param yMax: go till year
		@param converter: function to apply to result
		@return: [yearData.functName(*params),], [year, ..]
		"""
		yMin, yMax,i1,i2 = self._setPeriod(yMin, yMax)
		res,time=[],[]
		for y in range(yMin,yMax+1):
			yobj=self[y]
			f = getattr(yobj, functName)
			try:
				r=f(*params)
			except TypeError:
				r=f
			if converter is not None: r=converter(r)
			res.append(r)
			time.append(yobj.year)
		return res,time


	@cache
	def norm(self, yMin= -1, yMax= -1):
		"""
		Climatic norm for some period
		@param yMin:
		@param yMax:
		@return: [JanValue, ..., DecValue]
		"""
		yMin,yMax,i1,i2 = self._setPeriod(yMin, yMax)
		a=self.data[i1:i2+1]
		try:
			if not a.mask.any():
				res=np.array(a).mean(axis=0)
			else:
				res=np.ma.mean(a, axis=0)
		except:
			raise
		return [round(v,self.precision) for v in res]


	@cache
	def s_norm(self, yMin= -1, yMax= -1, seasToCalc=False):
		"""
		climatic norm for given season
		@param yMin:
		@param yMax:
		@param seasToCalc: season definition
		@return: {'seasonName': value}
		"""
		if seasToCalc == False:	seasToCalc = [s for s in self.seasonsCache]
		yMin,yMax,i1,i2 = self._setPeriod(yMin, yMax)
		sdat=self.getSeasonsData(seasToCalc)
		res=dict()
		for sname in sdat:
			dat=list(sdat[sname][i1:i2+1,:])
			res[sname]=round(np.ma.mean(dat), self.precision) if np.ma.any(dat) else None
		return res


	#TODO: написать юниттесты для ф-ий trend и trendParam
	@cache
	def trend(self, yMin= -1, yMax= -1, precision=None):
		"""
		annual trend parameters
		@param yMin:
		@param yMax:
		@param precision:
		@return: slope, intercept, values, time
		"""
		if precision is None: precision=self.precision+2
		yMin,yMax,i1,i2 = self._setPeriod(yMin, yMax)
		res=self.getSeasonsSeries({'y':range(1,13)})['y']
		res=res[i1:i2+1]
		time=self.yList[i1:i2+1]
		slope, intercept, r_value, p_value, std_err = stats.linregress(time, res)
		if isnan(slope): slope = None
		return round(slope, precision), round(intercept,precision), res.round(self.precision), time


	def s_trend(self,yMin= -1, yMax= -1, seasToCalc=False, precision=None):
		"""
		Seasonal trend parameters
		@param yMin:
		@param yMax:
		@param seasToCalc:
		@param precision:
		@return: {'seasonName': [slope, intercept, values, time]}
		"""
		if precision is None: precision=self.precision+2
		yMin,yMax,i1,i2 = self._setPeriod(yMin, yMax)
		allSdat = self.getSeasonsSeries(seasToCalc)
		res=dict()
		for sn,vals in allSdat.items():
			time=self.yList[i1:i2+1]
			val=vals[i1:i2+1]
			slope, intercept, r_value, p_value, std_err = stats.linregress(time, val)
			if isnan(slope): slope = None
			res[sn]=[round(slope, precision), round(intercept,precision), val.round(self.precision), time]
		return res


	@cache
	def trendParam(self, functName, params, yMin, yMax, converter=None, precision=None):
		"""
		Custom parameter trend
		@param functName: yearData method name
		@param params: yearData method parameters
		@param yMin:
		@param yMax:
		@param converter: function to apply to yearData.method(*parameters) result
		@param precision:
		@return: slope, intercept, values, time
		"""
		from scipy import stats
		from math import isnan
		if precision is None: precision=self.precision+2
		yMin,yMax,i1,i2 = self._setPeriod(yMin, yMax)
		res,time=self.getParamSeries(functName, params, yMin, yMax, converter)
		res,time=cc.removeNone(res,time)
		slope, intercept, r_value, p_value, std_err = stats.linregress(time, res)
		if isnan(slope): slope = None
		return round(slope, precision), round(intercept,precision), [round(v, self.precision) for v in res], time


	@cache
	def anomal(self, norm_yMin, norm_yMax, yMin= -1, yMax= -1):
		"""
		Считает аномалии от нормы для каждого месяца каждого года
		Принимает:
			norm_yMin, norm_yMax - за это период расчитывается норма
			yMin, yMax - за этот период расчитываются аномалии (по умолчанию весь доступный период)
		Возвращает:
			res - dict, года - ключи словарая, значения - списки аномалий для каждого месяца этого года
		"""
		#todo: было бы логичнее было бы использовать np.ma.anom(), но оно не работет по осям
		# обсуждение топика https://github.com/numpy/numpy/issues/2814
		yMin,yMax,i1,i2 = self._setPeriod(yMin, yMax)
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
		yMin,yMax,i1,i2 = self._setPeriod(yMin, yMax)
		res=dict()
		for sname in sdat:
			norm=self.s_norm(normMinY, normMaxY, seasToCalc=sname)[sname]
			dat=sdat[sname][i1:i2+1]
			res[sname]=[round(v.mean()-norm , self.precision) if v is not None else None for v in dat]
		time=self.yList[i1:i2+1]
		return res,time


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
		yMin,yMax,i1,i2 = self._setPeriod(yMin, yMax)
		dat=self.anomal(norm_yMin, norm_yMax, yMin, yMax)
		res=np.ma.average(dat, axis=0)
		return res


	def getAnomalCdo(self, norm_yMin, norm_yMax):
		"""
		Возвращает объект cliData в котором все значения данного объекта переведены в аномалии от заданного периода
		@return: cliData object
		"""
		yMin,yMax,i1,i2 = self._setPeriod(norm_yMin, norm_yMax)
		gdat=[[y,list(v.filled(-999.99))] for y,v in zip(self.yList,self.anomal(norm_yMin, norm_yMax))]
		meta=dict(self.meta)
		meta['comment']="converted to anomalys from norm %i - %i"%(yMin,yMax)
		return cliData(meta,gdat)


	def calcTask(self,task):
		"""
		for automation and multithreading
		@param task: {'taskName':{'fn':cliDataMethodName, 'param':parameters, 'converter':lambda}, ...}
		@return: {'taskName':value, ...}
		"""
		priorTasks = [v for v in task if task[v]['fn'] in ['setSeasons']]
		res = dict()
		for t in priorTasks:
			funct = getattr(self, task[t]['fn'])
			fr = funct(*task[t]['param'])
		for fnInd, tsk in task.items():
			if fnInd in priorTasks: continue
			funct = getattr(self, tsk['fn'])
			try:
				fr = funct(*tsk['param'])
				try:
					fr=tsk['converter'](fr)
				except KeyError:
					pass # конвертр не задан, это нормально
				except TypeError:
					raise TypeError, "конвертр результата расчёта не является функцией"
				finally:
					res[fnInd]=fr
			except:
				print '%s has failed for st %s'%(fnInd, str(self.meta))
				res[fnInd]=None
		self.res.update(res)
		return res

	@cache
	def trendMatrix(self, minTrlen=20):
		"""
		every possible annual trend longer than minTrlen
		Расчитывает матрицу зависимости велечины тренда от года начала тренда и его длинны
		Возвращает три двумерные numPy массива x,y,z
		"""
		import numpy as np
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
					slope, intercept, r_value, p_value,  = self.trend(yStart, (yStart + trLen))
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
			self.data=copy.deepcopy(parent.data[parent.timeInds[year]])
			# todo: разобраться в каких случаях срабатывает условие ниже и почему. Попадалось при работе с данными tas historical EC-Earth
			if type(self.data) is list: self.data=np.ma.masked_values(self.data, parent.filledValue)
		else:
			self.data=np.ma.masked_values([parent.filledValue]*12, parent.filledValue)
		self.data.mask=np.ma.getmaskarray(self.data)
		self.res = dict()
		self.precision=parent.precision
		self.meta=self.parent.meta


	def __str__(self):
		rList = list([round(v,self.precision)  if v!=self.parent.filledValue else None for v in self.data]) # копируем лист!
		while len(rList)<12: rList.append(None)
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
		#todo: определиться с использованием или не использованием масок
		return round(retval,self.precision) if retval!=self.data.fill_value and retval!=None else None


	def getSeasonsData(self,seasons):
		"""
		Возвращает данные по каждому сезону в виде словаря
		{'название сезона': [данные по месяцам в хронологическом порядке]}
		"""
		res=dict()
		for sname,mlist in seasons.items():
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
		return self.parent[year][month]


	@property
	def datapass(self):
		return round(self.missedMonth / (12 / 100.0), self.precision)


	@property
	def missedMonth(self):
		r=0
		try:
			if self.data.mask.any():
				r=sum([1 for v in self.data.mask if v==True])
		except AttributeError:
			pass
		return r


	def s_ampl(self, seasToCalc=False):
		"""
		Расчитывает амплитуду по сезонам
		"""
		res=dict()
		if seasToCalc==False: seasToCalc=[sn for sn in self.parent.seasonsCache]
		dat=self.parent.getSeasonsData(seasToCalc)
		yInd=self.parent.timeInds[self.year]
		for sname in dat:
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
		if seasToCalc==False:
			seasToCalc=[sn for sn in self.parent.seasonsCache]
		dat=self.parent.getSeasonsData(seasToCalc)
		if self.year in self.parent.timeInds:
			yInd=self.parent.timeInds[self.year]
			for sname in dat:
				if dat[sname][yInd].mask.any():
					res[sname]=None
				else:
					res[sname]=cc.avg(dat[sname][yInd],precision=self.precision)
		else:
			for sname in seasToCalc:
				res[sname]=None
		return res


	@property
	def avg(self):
		""" возвращает среднегодовую температуру """
		if self.missedMonth==0:
			r=round(self.data.mean(),self.precision)
		else:
			r=None
		return r


#	@saveRes
#	def sumLessThen(self, x):
#		""" Возвращает сумму значений больше X """
#		r=cc.sumLessThen([v if not m else None for v,m in zip(self.data, self.data.mask)],x,precision=self.precision)
#		return r


#	@saveRes
#	def s_sumMoreThen(self, x, seasToCalc=False):
#		""" Возвращает кортеж значений больше Х для каждого сезона """
#		res=dict()
#		if seasToCalc==False: seasToCalc=[sn for sn in self.parent.seasonsCache]
#		dat=self.parent.getSeasonsData(seasToCalc)
#		yInd=self.parent.timeInds[self.year]
#		for sname in dat:
#			if dat[sname][yInd].mask.any():
#				res[sname]=None
#			else:
#				res[sname]=cc.sumMoreThen(dat[sname][yInd],x, precision=self.precision)
#		return res


class temp_yearData(yearData):
	"""
	Функции спецефичные для рядов температуры
	"""
	def crossingPoints(self, x):
		"""
		Расчитывает даты перехода через заданное значение линейной интерполяцией
		"""
		from datetime import datetime,timedelta
		points=[]
		y=self.year
		dat=[[datetime(y,m,15), self[m]] for m in range(1,13)]
		if None in [v[1] for v in dat]:	return None
		dat+=[[datetime(y-1,12,15), self.parent[y-1][12]],[datetime(y+1,1,15), self.parent[y+1][1]]]
		dat.sort(key=lambda a:a[0])
		for i in range(len(dat)-1):
			d1,v1=dat[i]
			d2,v2=dat[i+1]
			if v1 is None or v2 is None: continue
			if v1<x<=v2 or v1>x>=v2:
				time=(d2-d1).days
				vs=[v1,v2]
				sp=(max(vs)-min(vs))/float(time)
				addTime=abs((v1-x)/float(sp))
				pt=d1+timedelta(days=addTime)
				if pt.year==y: points.append(pt)
		points.sort()
		return points


	def ddt_simple(self):
		return cc.sumMoreThen(self.data,0,2)*30.5


	@cache
	def conditionalSum(self,x, c='GT'):
		"""
		Уточнённый алгоритм расчёта градусо дней
		"""
		#todo: уточнить логику работы в случаях когда точки перехода встречаются не каждый год
		from datetime import datetime as dt
		if c=='GT':
			ct=lambda v: v>x
			ce=lambda v: v>=x
		elif c=='LT':
			ct=lambda v: v<x
			ce=lambda v: v<=x
		else:
			raise ValueError, "c = GT | LT"
		y=self.year
		dat=[]
		for yObj in [self, self.parent[y+1]]:
			dat+=[[dt(yObj.year,m,15), yObj[m]] for m in range(1,13) if yObj[m] is not None]
			points=yObj.crossingPoints(x)
			if points is None and yObj.year==y:
				return None,None
			elif points is None and yObj.year!=y:
				continue
			else:
				dat+=[[p,x] for p in points]
		#массив дат и значений точек переходов и наблюдений за этот и следующий год, отсортированый по времени
		dat.sort(key=lambda a:a[0])
		psum=0
		tsum=0
		start=False
		for i in range(len(dat)-1):
			d1,v1=dat[i]
			d2,v2=dat[i+1]
			if v1==x and ce(v2):
				if d1.year==y:
					start=True
				else:
					break
			if not start:continue
			t=(d2-d1).days
			if (ce(v1) and ct(v2)):
				# начало или продолжение
				psum+=(t*abs(v2-v1))/2. + t*abs(min([v2,v1]))
				tsum+=t
			elif (ct(v1) and v2==x):
				#если промежуток от этотой точки до следующей попадает под условие
				psum+=(t*abs(v2-v1))/2. + t*abs(min([v2,v1]))
				tsum+=t
				if (v2==x and d2.year>y):break # если период заканчивается в следующем году
			elif v1<x<v2 or v1>x>v2:
				# если пропущена точка перехода
				psum,tsum=None,None
				break
			else:
				continue
		else:
			psum,tsum=None,None
		if psum is not None: psum= round(psum, self.precision)
		return psum,tsum


class prec_yearData(yearData):
	"""

	"""
	@cache
	def sumMoreThen(self, x):
		""" Возвращает сумму значений больше X """
		r=cc.sumMoreThen([v if not m else None for v,m in zip(self.data, self.data.mask)],x,precision=self.precision)
		return r


	def sumInPeriod(self,start,end):
		"""
		Функция возвращает сумму осадков за период между start и end
		"""
		from datetime import datetime,timedelta
		from calendar import monthrange
		#thisMonthLen=monthrange(start)[1]
		y=self.year
		periodLen=(end-start).days
		psum=0
		d=0
		while d<periodLen:
			today=start+timedelta(days=d)
			thisMonthLen=monthrange(today.year, today.month)[1]
			pl=thisMonthLen-today.day+1
			if today.year==y:
				psum+=self[today.month]/float(thisMonthLen)*pl
			elif today.year==y+1:
				psum+=self[12+today.month]/float(thisMonthLen)*pl
			else:
				psum=None
				break
			d+=pl
		if psum is not None: psum=round(psum,self.precision)
		return psum


if __name__ == "__main__":
	pass

