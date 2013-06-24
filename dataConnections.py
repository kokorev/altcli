# coding=utf-8
"""
Содержит классы подключений к различным базам и массивам данных.
Каждый класс должен реализовывать следующие функции
	getAllMetaDict() - возвращает словарь метаданных для всех станция в массиве
	getPoint(ind) - возвращает экземпляр cliData для станции(точки) с данным индексом
"""
__author__ = 'Vasily Kokorev'
__email__ = 'vasilykokorev@gmail.com'

from clidata import cliData
from clidataSet import createCliDat

class cmip5connection():
	"""
	Реализует чтение .nc файлов с данными cmip5 месячного разрешения
	"""
	def __init__(self, fn, convert=True):
		import netCDF4 as nc
		from datetime import datetime
		from geocalc import cLon
		self.f=nc.Dataset(fn)
		if self.f.project_id!='CMIP5':
			print 'projet_id is "%s" not "CMIP5"'%self.f.project_id
		# определяем основную переменную в массиве, это так которая зависит от трёх других
		self.dt=[v for v in self.f.variables if self.f.variables[v].ndim==3][0]
		if self.dt=='tas' and convert is True:
			from tempConvert import kelvin2celsius
			self.convertValue=lambda val,year,month: kelvin2celsius(val)
		elif self.dt=='pr' and convert is True:
			from precConvert import si2mmPerMonth
			self.convertValue=si2mmPerMonth
		else:
			self.convertValue=lambda val,year,month: val
#			print "Warning! There is no converter for data type = '%s'"%self.dt
		self.var=self.f.variables[self.dt]
		self.lat=self.f.variables['lat']
		self.latvals=[self.lat[l] for l in range(self.lat.size)]
		self.lon=self.f.variables['lon']
		self.lonvals=[cLon(self.lon[l]) for l in range(self.lon.size)]
		try:
			self.startDate=nc.num2date(self.f.variables['time'][0], self.f.variables['time'].units,
									   self.f.variables['time'].calendar)
		except ValueError:
			if self.f.variables['time'].units=='days since 1-01-01 00:00:00':
				self.startDate=datetime(1,1,1)
			else:
				print 'Warning! failed to parse date string -%s. Model id - %s. startDate '\
				  'set to 0850-1-1 assuming model is MPI'%(self.f.variables['time'].units,self.f.model_id)
				self.startDate=datetime(850,1,1)
		self.startYear = int(self.startDate.year)
		self.startMonth = int(self.startDate.month)
		self.warningShown = False
		self.cliSetMeta = {'modelId':self.f.model_id, 'calendar':self.f.variables['time'].calendar, 'source':'CMIP5 nc file'}


	def getPoint(self, item):
		"""
		self[(latInd,lonInd)] возвращает объект cliData
		После долго путанцы было решено, что ф-я может принимать либо номер яцейки либо индексы координат,
		но не сами координаты
		"""
		try:
			try:
				latInd, lonInd = item
				if self.warningShown==False:
					print 'Warning! (lat, lon) is no more a valid argument. Please check your code and'
					print 'use latlon2latIndlonInd or closestDot function to get coordinate indexes'
					self.warningShown = True
			except TypeError:
				latInd, lonInd = self.ind2latindlonind(item)
		except:
			print self.f.model_id, item
			raise
		meta={'ind':self.latlonInd2ind(latInd, lonInd), 'lat':self.latvals[latInd], 'lon':self.lonvals[lonInd],
			  'dt':self.dt, 'modelId':self.f.model_id}
		vals=list(self.var[:,latInd,lonInd])
		gdat=[]
		if self.startMonth!=1:
			# весь огород ниже из-за моделей которые начинают год не с января
			# нормальный вариант для большинства моделей - тот что в else
			fyl=12-(self.startMonth-1)
			for yn,i in enumerate(range(fyl,len(vals)-12,12)):
				tyear=self.startYear+yn
				gdline=[self.convertValue(v, year=tyear, month=mn+1) for mn,v in enumerate(vals[i:i+12])]
				gdat.append([self.startYear+yn+1, gdline])
			gdatline=[self.convertValue(v, year=tyear, month=mn+1) for mn,v in enumerate(vals[i+12:])]
			gdatline=gdatline+[None]*(12-len(gdatline))
			gdat.append([self.startYear+yn,gdatline])
		else:
			for yn,i in enumerate(range(0,len(vals),12)):
				tyear=self.startYear+yn
				gdat.append([tyear, [self.convertValue(v, year=tyear, month=mn+1) for mn,v in enumerate(vals[i:i+12])]])
		return createCliDat(meta=meta, gdat=gdat)


	def getAllMetaDict(self):
		"""
		Возвращает словарь метаданных для всех узлов сетки
		"""
		res=dict()
		for latInd,lat in enumerate(self.latvals):
			for lonInd,lon in enumerate(self.lonvals):
				ind=self.latlonInd2ind(latInd, lonInd)
				res[ind]={'ind':ind, 'lat':lat, 'lon':lon, 'dt':self.dt, 'modelId':self.f.model_id}
		return res


	def latlon2latIndlonInd(self, lat, lon):
		"""
		считает индексы ячеек из координат
		!Внимание! индексы ячеек разные для разных моделей(сеток) разные
		"""
		try:
			if lon<0: lon += 360
			lonInd=self.lonvals.index(lon)
			latInd=self.latvals.index(lat)
		except ValueError:
			print 'Valid lat indexes are -'
			print self.latvals
			print 'Valid lon indexes are -'
			print self.lonvals
			raise
		return latInd, lonInd

	def latlonInd2ind(self, latInd, lonInd):
		"""
		Расчитывает индекс ячейки из индексов по x,y
		"""
		return int(latInd*self.lon.size+lonInd)

	def ind2latindlonind(self, ind):
		""" переводит номер узла в индексы массива """
		latInd=int(ind/self.lon.size)
		lonInd=ind - latInd*self.lon.size
		return latInd, lonInd



class cliGisConnection():
	"""
	Реализует чтение формата данных использовашегося в cliGis
	"""
	def __init__(self, dataFn, metaFn, fillValue=-999., dt=None):
		import os.path
		self.cliSetMeta={'source':'cliGis'}
		self.fillValue=fillValue
		if dt is None:
			head, tail=os.path.split(dataFn)
			dt=tail[0:1]
			if dt not in ['T', 'P']: raise IOError, "Can't detect data type"
		self.dt=dt
		f=open(dataFn, 'r')
		self.dat=[[float(v) if float(v)!=self.fillValue else None for v in l.split()] for l in f.readlines()]
		f.close()
		unicInds=list(set([v[0] for v in self.dat]))
		f=open(metaFn, 'r')
		m=[[float(v) for v in l.split()[:3]] for l in f.readlines()[1:]]
		f.close()
		self.meta=dict()
		for ln in m:
			ind=int(ln[0])
			if ind not in unicInds: continue
			self.meta[ind]={'ind':ind, 'lat':ln[1], 'lon':ln[2], 'dt':self.dt}


	def getPoint(self, item):
		""" return object for selected station """
		if item not in self.meta: raise KeyError, "wrong data index"
		gdat=[[int(ln[1]),ln[2:]] for ln in self.dat if ln[0]==item]
		gdat.sort(key=lambda a: a[0])
		m=self.meta[item]
		return createCliDat(gdat=gdat,meta=m)


	def getAllMetaDict(self):
		"""
		Возвращает словарь метаданных для всех узлов сетки
		"""
		return self.meta


