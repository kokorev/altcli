# coding=utf-8
class readCMIP5nc:
	"""
	Класс чтения netCDF данных CMIP5
	для работы с данными экперимента historical
	"""
	def __init__(self, fn, dt):
		import netCDF4 as nc
		from datetime import datetime
		self.dt=dt
		self.f=nc.Dataset(fn)
		self.var=self.f.variables[self.dt]
		self.lat=self.f.variables['lat']
		self.latvals=[self.lat[l] for l in range(self.lat.size)]
		self.lon=self.f.variables['lon']
		self.lonvals=[self.lon[l] for l in range(self.lon.size)]
		try:
			self.startDate=nc.num2date(self.f.variables['time'][0], self.f.variables['time'].units,
			                           self.f.variables['time'].calendar)
		except ValueError:
			print 'Warning! failed to parse date string -%s. Model id - %s. startDate ' \
			      'set to 0850-1-1 assuming model is MPI'%(self.f.variables['time'].units,self.f.model_id)
			self.startDate=datetime(850,1,1)
		self.startYear = int(self.startDate.year)
		self.startMonth = int(self.startDate.month)
		self.warningShown = False


	def __getitem__(self, item):
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


	def convertValue(self,val, **keywords):
		"""
		Переводит велечины в традиционный вид. Температуры в градусы цельсия, осадки в мм в месяц
		"""
		k=273.15
		if self.dt=='tas':
			r=round(val-k,2)
		elif self.dt=='pr':
			import calendar
			numD=calendar.monthrange(keywords['year'], keywords['month'])[1]
			r=val*86400*numD
		return r


	def closestDot(self, lat, lon):
		"""
		считает индексы ячеек из координат
		!Внимание! индексы ячеек разные для разных моделей(сеток) разные
		"""
		if lon<0: lon += 360
		lonlist=[[i,abs(v-lon)] for i,v in enumerate(self.lonvals)]
		lonlist.sort(key=lambda a: a[1])
		lonInd=lonlist[0][0]
		latlist=[[i,abs(v-lat)] for i,v in enumerate(self.latvals)]
		latlist.sort(key=lambda a: a[1])
		latInd=latlist[0][0]
		return latInd, lonInd

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
		return latInd*self.lon.size+lonInd

	def ind2latindlonind(self, ind):
		""" переводит номер узла в индексы массива """
		latInd=int(ind/self.lon.size)
		lonInd=ind - latInd*self.lon.size
		return latInd, lonInd

	def get_pointsList(self):
		"""
		Возвращает список координат узлов сетки в формате
		[[lat, lon], ...]
		"""
		res=[]
		for lat in self.latvals:
			for lon in self.lonvals:
				res.append([lat,lon])
		return res

	def get_gridProjection(self,task,pointList=None):
		"""
		Calc task for every point in pointList
		"""
		from altCli_automation import altCliCalc
		if pointList is None:
			pointList=self.get_pointsList()
		stList=[]
		for ind in pointList:
			stList.append(self[ind])
		acc=altCliCalc(task,stList)
		res=acc.calcTask()
		for res in ind:
			res[ind]['lat']=self[ind].meta['lat']
			res[ind]['lon']=self[ind].meta['lon']
			res[ind]['ind']=ind
		return res
#
#	def get_dotProjection(self,task,pointList=None):
#		"""
#		Calc average value for point in pointList
#		"""
#		def w(cdo):
#			""" функция определения веса станции """
#			from math import cos,radians
#			return cos(radians(cdo.meta['lat']))
#		from altCli_automation import altCliCalc
#		from altCliCore import metaData
#		if pointList is None:
#			pointList=self.get_pointsList()
#		stList=[]
#		for ind in pointList:
#			stList.append(self[ind])
#		pl=metaData({'dt':self.dt, 'modelId':self.f.model_id})
#		pl.stList=stList
#		pl.maxInd=len(stList)
#		cdo=pl.setRegAvgData(weight=w)
#		acc=altCliCalc(task,cdo)
#		res=acc.calcTask()
#		return res[0]

if __name__ == "__main__":
	pass








