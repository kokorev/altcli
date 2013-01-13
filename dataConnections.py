# coding=utf-8
"""
Содержит классы подключений к различным базам и массивам данных.
Каждый класс должен реализовывать следующие функции
	getAllMetaDict() - возвращает словарь метаданных для всех станция в массиве
	getPoint(ind) - возвращает экземпляр cliData для станции(точки) с данным индексом
"""
__author__ = 'Vasily Kokorev'
__email__ = 'vasilykokorev@gmail.com'


class cmip5connection():
	"""
	Реализует чтение .nc файлов с данными cmip5 месячного разрешения
	"""
	def __init__(self, fn):
		import netCDF4 as nc
		from datetime import datetime
		from geocalc import cLon
		self.f=nc.Dataset(fn)
		if self.f.project_id!='CMIP5':
			print 'projet_id is "%s" not "CMIP5"'%self.f.project_id
		# определяем основную переменную в массиве, это так которая зависит от трёх других
		self.dt=[v for v in self.f.variables if self.f.variables[v].ndim==3][0]
		if self.dt=='tas':
			from tempConvert import kelvin2celsius
			self.convertValue=lambda val,year,month: kelvin2celsius(val)
		elif self.dt=='pr':
			from precConvert import si2mmPerMonth
			self.convertValue=si2mmPerMonth
		else:
			self.convertValue=lambda val,year,month: val
			print "Warning! There is no converter for data type = '%s'"%self.dt
		self.var=self.f.variables[self.dt]
		self.lat=self.f.variables['lat']
		self.latvals=[self.lat[l] for l in range(self.lat.size)]
		self.lon=self.f.variables['lon']
		self.lonvals=[cLon(self.lon[l]) for l in range(self.lon.size)]
		try:
			self.startDate=nc.num2date(self.f.variables['time'][0], self.f.variables['time'].units,
									   self.f.variables['time'].calendar)
		except ValueError:
			print 'Warning! failed to parse date string -%s. Model id - %s. startDate '\
				  'set to 0850-1-1 assuming model is MPI'%(self.f.variables['time'].units,self.f.model_id)
			self.startDate=datetime(850,1,1)
		self.startYear = int(self.startDate.year)
		self.startMonth = int(self.startDate.month)
		self.warningShown = False
		self.cliSetMeta = {'modelId':self.f.model_id, 'calendar':self.f.variables['time'].calendar}


	def getPoint(self, item):
		"""
		self[(latInd,lonInd)] возвращает объект cliData
		После долго путанцы было решено, что ф-я может принимать либо номер яцейки либо индексы координат,
		но не сами координаты
		"""
		from altCliCore import cliData
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
		return cliData(meta=meta, gdat=gdat)


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
