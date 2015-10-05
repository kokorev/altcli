# coding=utf-8
"""
Collection of classes that allows one to load different data formats to altCli
New class should be inherited from dataConnection class
"""
__author__ = 'Vasily Kokorev'
__email__ = 'vasilykokorev@gmail.com'

from clidataSet import createCliDat
from common import elSynom
from geocalc import cLon
import os.path
import netCDF4 as nc
from netCDF4 import num2date
import numpy as np
from glob import glob
import itertools
import logging
from pyhdf import SD
import datetime

logging.basicConfig(format = u'%(filename)s[LINE:%(lineno)d]# %(levelname)-8s [%(asctime)s]  %(message)s', level = logging.DEBUG)


class dataConnection():
	"""
	shows what methods dataConnection class should implement
	"""
	def __init__(self, dbPointer):
		""" Should be overridden
		@param dbPointer: file name, etc
		@return:
		"""
		self.cliSetMeta=None #dict()
		raise NotImplementedError, "dataConnection.__init__() must be implemented"

	def getAllMetaDict(self):
		"""	Should be overridden
		return dictionary of meta information for every station or point in dataset	"""
		raise NotImplementedError, "dataConnection.getAllMetaDict() must be implemented"

	def getPoint(self, ind):
		""" Should be overridden
		return cliData instanse of point with given index """
		raise NotImplementedError, "dataConnection.getPoint(ind) must be implemented"


class netcdfConnection(dataConnection):
	"""
	allow one to use original CMIP5 data in netCDF format
	"""
	def __init__(self, fn, convert=False):
		fn=os.path.abspath(fn)
		try:
			self.f=nc.Dataset(fn)
		except RuntimeError:
			raise IOError, "no such file or dir %s"%fn
		# определяем основную переменную в массиве, это так которая зависит от трёх других
		self.setMainVariable()
		self.setConverter(convert)
		self.setLatLon()
		self.cliSetMeta = {'calendar':self.f.variables['time'].calendar, 'source':fn,'dt':self.dt}
		self.setDateConverter()


	def setConverter(self, convert=False):
		"""
		define function for conversion to standard units
		@return:
		"""
		if self.dt=='temp' and convert is True:
			from tempConvert import kelvin2celsius
			self.convertValue=lambda val,year,month: kelvin2celsius(val)
			self.convertArray=lambda arr: np.subtract(arr,273.15)
		elif self.dt=='prec' and convert is True:
			if self.var.units.lower()=='kg/m^2/s' and self.f.frequency=='day':
				from precConvert import si2mmPerDay
				self.convertValue=si2mmPerDay
			elif self.var.units.lower()=='kg/m^2/s' and self.f.frequency=='mon':
				from precConvert import si2mmPerMonth
				self.convertValue=si2mmPerMonth
				self.convertArray=np.vectorize(lambda val: val*86400*30.5, otypes=[np.float])
			elif self.var.units.lower()=='cm':
				from precConvert import cm2mm
				self.convertValue=cm2mm
				self.convertArray=np.vectorize(lambda val: val/10., otypes=[np.float])
		else:
			self.convertValue=lambda val,year,month: val
			self.convertArray=lambda arr: arr
#			print "Warning! There is no converter for data type = '%s'"%self.dt

	def setLatLon(self, latName='lat', lonName='lon'):
		self.lat=self.f.variables[latName]
		self.latvals=[self.lat[l] for l in range(self.lat.size)]
		self.lon=self.f.variables[lonName]
		self.lonvals=[cLon(self.lon[l]) for l in range(self.lon.size)]


	def setMainVariable(self, dt=None, fillValue=None):
		"""
		setting main variable in dataset. It is the one that depends on three other or defined by user in dt parameter
		@return:
		"""
		varName=None
		self.fillValue=fillValue
		if dt is None:
			dtList=list()
			for v in self.f.variables:
				if v in elSynom:
					dtList.append(v)
					varName=v
					continue
				try:
					if self.f.variables[v].standard_name in elSynom:
						dtList.append(self.f.variables[v].standard_name)
						varName=v
				except AttributeError:
					pass
				else:
					continue
				try:
					if self.f.variables[v].long_name in elSynom:
						dtList.append(self.f.variables[v].long_name)
						varName=v
				except AttributeError:
					pass
				else:
					continue
			assert len(dtList)==1, "Please specify the main variable"
			self.dt=elSynom[dtList[0]]
			self.var=self.f.variables[varName]
		else:
			try:
				self.dt=elSynom[dt]
			except KeyError:
				self.dt=dt
			self.var=self.f.variables[dt]

		if self.fillValue is None:
			try:
				self.fillValue=self.var._FillValue
			except AttributeError:
				pass
			try:
				self.fillValue=self.var.missing_value
			except AttributeError:
				pass


	def setDateConverter(self):
		"""

		@return:
		"""
		if self.f.variables['time'].units=='days since 1-01-01 00:00:00':
			self.timeUnits='days since 0001-01-01 00:00:00'
		elif self.f.variables['time'].units=='days since  850-1-1 00:00:00':
			self.timeUnits='days since 0850-1-1 00:00:00'
		else:
			self.timeUnits=self.f.variables['time'].units
		try:
			self.startDate=nc.num2date(self.f.variables['time'][0], self.timeUnits, self.cliSetMeta['calendar'])
		except ValueError:
			logging.error('Warning! failed to parse date string -%s. Model id - %s. startDate set to 0850-1-1 assuming model is MPI'%(self.f.variables['time'].units,self.f.model_id))
			raise
		self.startYear = int(self.startDate.year)
		self.startMonth = int(self.startDate.month)


	def getPoint(self, item):
		"""
		self[(latInd,lonInd)] возвращает объект cliData
		item could be either point index or (latIndex, lonIndex) but not (lat, lon). Use self.latlon2latIndlonInd()
		"""
		try:
			latInd, lonInd = item
		except TypeError:
			latInd, lonInd = self.ind2latindlonind(item)
		except:
			print self.f.model_id, item
			raise
		meta={'ind':self.latlonInd2ind(latInd, lonInd), 'lat':self.latvals[latInd], 'lon':self.lonvals[lonInd],
			  'dt':self.dt}
		vals=self.var[:,latInd,lonInd]
		gdat=[]
		for yn,i in enumerate(range(0,len(vals),12)):
			tyear=self.startYear+yn
			lineVals=vals[i:i+12]
			if len(lineVals)==12:
				gdat.append([tyear, self.convertArray(lineVals)])
		return createCliDat(meta=meta, gdat=gdat,fillValue=self.fillValue)


	def getArray(self,yMin=None,yMax=None,month=None,latMin=None,lonMin=None,latMax=None,lonMax=None):
		"""
		Возвращает трехмерный numpy массив значений, ограниченный заданными широтами и временем
		"""
		date=num2date(self.f.variables['time'][:], self.timeUnits, self.cliSetMeta['calendar'])
		var=np.array(self.var)
		timeArr=np.array([(v.year,v.month, v.day) for v in date],
						 dtype=[('year','i4'), ('month','i2'), ('day','i2')])
		timeMask=np.ones(timeArr['year'].shape,dtype=bool)
		if yMin is not None:
			timeMask = timeMask & (timeArr['year'] >= yMin)
		if yMax is not None:
			timeMask = timeMask & (timeArr['year'] <= yMax)
		if month is not None:
			timeMask = timeMask & (timeArr['month']==month)
		var=var[timeMask,:,:]
		lat=np.array(self.lat)
		latMask=np.ones(lat.shape,dtype=bool)
		if latMin is not None:
			latMask = latMask & (lat >= latMin)
		if latMax is not None:
			latMask = latMask & (lat <= latMax)
		var=var[:,latMask,:]
		lon=np.array(self.lon)
		lonMask=np.ones(lon.shape,dtype=bool)
		if lonMin is not None:
			lonMask = lonMask & (lon >= lonMin)
		if lonMax is not None:
			lonMask = lonMask & (lon <= lonMax)
		var=var[:,:,lonMask]
		return var

	def getAllMetaDict(self):
		"""
		Возвращает словарь метаданных для всех узлов сетки
		"""
		res=dict()
		ind=0
		for lat,lon in itertools.product(self.latvals,self.lonvals):
			res[ind]={'ind':ind, 'lat':lat, 'lon':lon, 'dt':self.dt}
			ind+=1
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


class cmip5connection(dataConnection):
	"""
	allow one to use original CMIP5 data in netCDF format
	"""
	def __init__(self, fn, convert=True):
		fn=os.path.abspath(fn)
		try:
			self.f=nc.Dataset(fn)
		except RuntimeError:
			raise IOError, "no such file or dir %s"%fn
		if self.f.project_id!='CMIP5':
			print 'projet_id is "%s" not "CMIP5"'%self.f.project_id
		# определяем основную переменную в массиве, это так которая зависит от трёх других
		dtList=[v for v in self.f.variables if self.f.variables[v].ndim==3]
		if len(dtList)>1:
			dtList=[tmpDt for tmpDt in dtList if tmpDt in elSynom]
			if len(dtList)>1: raise TypeError, "Unknown data type in nc file"
		self.dt=dtList[0]
		if self.dt=='tas' and convert is True:
			from tempConvert import kelvin2celsius
			self.convertValue=lambda val,year,month: kelvin2celsius(val)
			self.convertArray=lambda arr: np.subtract(arr,273.15)
		elif self.dt=='pr' and convert is True:
			if self.f.frequency=='day':
				from precConvert import si2mmPerDay
				self.convertValue=si2mmPerDay
			elif self.f.frequency=='mon':
				from precConvert import si2mmPerMonth
				self.convertValue=si2mmPerMonth
				self.convertArray=np.vectorize(lambda val: val*86400*30.5, otypes=[np.float])
		else:
			self.convertValue=lambda val,year,month: val
			self.convertArray=lambda arr: arr
#			print "Warning! There is no converter for data type = '%s'"%self.dt
		self.var=self.f.variables[self.dt]
		self.lat=self.f.variables['lat']
		self.latvals=[self.lat[l] for l in range(self.lat.size)]
		self.lon=self.f.variables['lon']
		self.lonvals=[cLon(self.lon[l]) for l in range(self.lon.size)]
		if self.f.variables['time'].units=='days since 1-01-01 00:00:00':
			self.timeUnits='days since 0001-01-01 00:00:00'
		elif self.f.variables['time'].units=='days since  850-1-1 00:00:00':
			self.timeUnits='days since 0850-1-1 00:00:00'
		else:
			self.timeUnits=self.f.variables['time'].units
		try:
			self.startDate=nc.num2date(self.f.variables['time'][0], self.timeUnits,
									   self.f.variables['time'].calendar)
		except ValueError:
			raise
			print 'Warning! failed to parse date string -%s. Model id - %s. startDate set to 0850-1-1 assuming model is MPI'%(self.f.variables['time'].units,self.f.model_id)
			# if self.f.variables['time'].units=='days since 1-01-01 00:00:00':
			# 	self.startDate=datetime(1,1,1)
			# else:
			# 	print 'Warning! failed to parse date string -%s. Model id - %s. startDate '\
			# 	  'set to 0850-1-1 assuming model is MPI'%(self.f.variables['time'].units,self.f.model_id)
			# 	self.startDate=datetime(850,1,1)
		self.startYear = int(self.startDate.year)
		self.startMonth = int(self.startDate.month)
		self.warningShown = False
		self.cliSetMeta = {'modelId':self.f.model_id, 'calendar':self.f.variables['time'].calendar, 'source':fn,
						   'scenario':self.f.experiment_id, 'dt':self.dt}


	def getPoint(self, item):
		"""
		self[(latInd,lonInd)] возвращает объект cliData
		item could be either point index or (latIndex, lonIndex) but not (lat, lon). Use self.latlon2latIndlonInd()
		"""
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
		vals=self.var[:,latInd,lonInd]
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
				lineVals=vals[i:i+12]
				if len(lineVals)==12:
					#TODO: сделать нормальное заполнение пропусками, У некоторыйх модлей (EC_EARTH) в последнем году расчёта только 11 месяцев, пропускаем такие года
					gdat.append([tyear, self.convertArray(lineVals)])
		return createCliDat(meta=meta, gdat=gdat)


	def getArray(self,yMin=None,yMax=None,month=None,latMin=None,lonMin=None,latMax=None,lonMax=None):
		"""
		Возвращает трехмерный numpy массив значений, ограниченный заданными широтами и временем
		"""
		date=num2date(self.f.variables['time'][:], self.timeUnits, self.f.variables['time'].calendar)
		var=np.array(self.var)
		timeArr=np.array([(v.year,v.month, v.day) for v in date],
						 dtype=[('year','i4'), ('month','i2'), ('day','i2')])
		timeMask=np.ones(timeArr['year'].shape,dtype=bool)
		if yMin is not None:
			timeMask = timeMask & (timeArr['year'] >= yMin)
		if yMax is not None:
			timeMask = timeMask & (timeArr['year'] <= yMax)
		if month is not None:
			timeMask = timeMask & (timeArr['month']==month)
		var=var[timeMask,:,:]
		lat=np.array(self.lat)
		latMask=np.ones(lat.shape,dtype=bool)
		if latMin is not None:
			latMask = latMask & (lat >= latMin)
		if latMax is not None:
			latMask = latMask & (lat <= latMax)
		var=var[:,latMask,:]
		lon=np.array(self.lon)
		lonMask=np.ones(lon.shape,dtype=bool)
		if lonMin is not None:
			lonMask = lonMask & (lon >= lonMin)
		if lonMax is not None:
			lonMask = lonMask & (lon <= lonMax)
		var=var[:,:,lonMask]
		return var

	def getAllMetaDict(self):
		"""
		Возвращает словарь метаданных для всех узлов сетки
		"""
		res=dict()
		ind=0
		for lat,lon in itertools.product(self.latvals,self.lonvals):
			res[ind]={'ind':ind, 'lat':lat, 'lon':lon, 'dt':self.dt, 'modelId':self.f.model_id}
			ind+=1
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


class cliGisConnection(dataConnection):
	"""
	climate data format for State Hydrological Institute
	"""
	def __init__(self, dataFn, metaFn, fillValue=-999., dt=None):
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


class GRDCConnection(dataConnection):
	"""
	GRDC river runoff ascii format
	"""
	def __init__(self, dataFolder, dt='runoff'):
		self.cliSetMeta={'source':'GRDC'}
		self.dataFolder=dataFolder
		self.dt=dt
		self.fnList=glob(os.path.join(dataFolder, '*.mon'))
		self.meta={int(os.path.split(fn)[1].split('.')[0]):None for fn in self.fnList}
		self.cdos={ind:None for ind in self.meta}


	def getPoint(self, item):
		if item not in self.meta: raise KeyError, "wrong data index"
		if self.cdos[item] is None:
			fn=os.path.join(self.dataFolder, '%i.mon'%item)
			with open(fn,'r') as f: lines=f.readlines()
			dat=np.loadtxt(lines,comments='#', delimiter=';',skiprows=41,
						   dtype={'names':['date','hh:mm','original','calculated','flag'],'formats':['S10','S5','f4', 'f4', 'f4']})
			dat=np.array([[int(ym[0]), int(ym[1]), v] for ym,v in zip( [v.split('-') for v in dat['date']] , dat['original'])])
			gdat=[]
			years=list(set(dat[:,0]))
			for y in years:
				gdatline=list(dat[dat[:,0]==y][:,2])
				assert len(gdatline)==12
				gdat.append([y,gdatline])
			meta=self.parseMeta(lines)
			meta['yMin']=min(years)
			meta['yMax']=max(years)
			cdo=createCliDat(gdat=gdat,meta=meta)
			self.cdos[item]=cdo
			self.meta[item]=meta
		else:
			cdo=self.cdos[item]
		return cdo


	def parseMeta(self,lines):
		lns=[[v.strip() for v in ln.split(':')] for ln in lines[:40]]
		lnsd={ln[0][2:]:ln[1] for ln in lns if len(ln)>1}
		meta=dict()
		meta['dt']=self.dt
		meta['river']=lnsd['River']
		meta['lon']=float([lnsd[k] for k in lnsd if 'Longitude' in k][0])
		meta['lat']=float([lnsd[k] for k in lnsd if 'Latitude' in k][0])
		meta['ind']=int(lnsd['GRDC-No.'])
		meta['catchment area (kmІ)']=float([lnsd[k] for k in lnsd if 'Catchment area' in k][0])
		try:
			meta['next d/s station']=int(lnsd['Next d/s station'])
		except ValueError:
			meta['next d/s station']=None
		meta['station']=lnsd['Station']
		meta['alt']=float(lnsd['Altitude (m.a.s.l)'])
		meta['file generation data']=lnsd['file generation data']
		meta['last update']=lnsd['Last update']
		meta['country']=lnsd['Country']
		meta['unit']=lnsd['Unit']
		return meta

	def getAllMetaDict(self):
		"""
		Возвращает словарь метаданных для всех узлов сетки
		"""
		for ind in self.meta:
			if self.meta[ind] is not None: continue
			self.getPoint(ind)
		return self.meta


class ncep2Connection(netcdfConnection):
	"""
	NCEP/DOE AMIP-II Reanalysis format
	"""
	def __init__(self, fn, convert=True):
		fn=os.path.abspath(fn)
		try:
			self.f=nc.Dataset(fn)
		except RuntimeError:
			raise IOError, "no such file or dir %s"%fn
		# определяем основную переменную в массиве, это так которая зависит от трёх других
		self.setMainVariable()
		self.setConverter(convert)
		self.setLatLon()
		self.cliSetMeta = {'calendar':self.f.variables['time'].calendar, 'source':fn, 'dt':self.dt}
		self.setDateConverter()

	def getPoint(self, item):
		"""
		self[(latInd,lonInd)] возвращает объект cliData
		item could be either point index or (latIndex, lonIndex) but not (lat, lon). Use self.latlon2latIndlonInd()
		"""
		try:
			latInd, lonInd = item
		except TypeError:
			latInd, lonInd = self.ind2latindlonind(item)
		except:
			print self.f.model_id, item
			raise
		meta={'ind':self.latlonInd2ind(latInd, lonInd), 'lat':self.latvals[latInd], 'lon':self.lonvals[lonInd],
			  'dt':self.dt}
		vals=self.var[:,0,latInd,lonInd]
		gdat=[]
		for yn,i in enumerate(range(0,len(vals),12)):
			tyear=self.startYear+yn
			lineVals=vals[i:i+12]
			if len(lineVals)==12:
				gdat.append([tyear, self.convertArray(lineVals)])
		return createCliDat(meta=meta, gdat=gdat)

class CRUTEMP4Connection(netcdfConnection):
	"""

	"""
	def __init__(self, fn):
		fn=os.path.abspath(fn)
		try:
			self.f=nc.Dataset(fn)
		except RuntimeError:
			raise IOError, "no such file or dir %s"%fn
		# определяем основную переменную в массиве, это так которая зависит от трёх других
		self.setMainVariable('temperature_anomaly')
		self.setConverter(False)
		self.setLatLon(latName='latitude', lonName='longitude')
		self.warningShown = False
		self.cliSetMeta = {'calendar':self.f.variables['time'].calendar, 'source':fn, 'dt':self.dt}
		self.setDateConverter()

class CRUTS3Connection(netcdfConnection):
	"""

	"""
	def __init__(self, fn):
		fn=os.path.abspath(fn)
		try:
			self.f=nc.Dataset(fn)
		except RuntimeError:
			raise IOError, "no such file or dir %s"%fn
		# определяем основную переменную в массиве, это так которая зависит от трёх других
		self.setMainVariable()
		self.setConverter(False)
		self.setLatLon()
		self.warningShown = False
		self.cliSetMeta = {'calendar':self.f.variables['time'].calendar, 'source':fn, 'dt':self.dt}
		self.setDateConverter()

class ERAInterimConnection(netcdfConnection):
	"""
	ERA-Interim reanalysis
	"""
	def __init__(self, fn):
		fn=os.path.abspath(fn)
		try:
			self.f=nc.Dataset(fn)
		except RuntimeError:
			raise IOError, "no such file or dir %s"%fn
		# определяем основную переменную в массиве, это так которая зависит от трёх других
		self.setMainVariable()
		self.setConverter(True)
		self.setLatLon(latName='latitude', lonName='longitude')
		self.warningShown = False
		self.cliSetMeta = {'calendar':self.f.variables['time'].calendar, 'source':fn, 'dt':self.dt}
		self.setDateConverter()

class DelawareConnection(netcdfConnection):
	"""
	"""
	def __init__(self, fn):
		fn=os.path.abspath(fn)
		try:
			self.f=nc.Dataset(fn)
		except RuntimeError:
			raise IOError, "no such file or dir %s"%fn
		# определяем основную переменную в массиве, это так которая зависит от трёх других
		self.setMainVariable()
		self.setConverter(False)
		self.setLatLon()
		self.cliSetMeta = {'calendar':'standard', 'source':fn,'dt':self.dt}
		self.setDateConverter()


class CH4flaskNOAA():
	""" read NOAA CH4 methane concentration data """

	def __init__(self, dataPath, metaFilePath):
		self.dataPath = dataPath
		self.meta, self.codes = self.readMeta(metaFilePath)
		self.cliSetMeta = {'dt':'ch4', 'codes':self.codes}

	def getFn(self,code):
		return self.dataPath + r'\ch4_%s_surface-flask_1_ccgg_month.txt' % (code.lower())

	def readDataFile(self, code):
		fn = self.dataPath + r'\ch4_%s_surface-flask_1_ccgg_month.txt' % (code.lower())
		dat = np.genfromtxt(fn, comments='#', usecols=[1, 2, 3])
		years = list(set(dat[:, 0]))
		years.sort()
		gdat = []
		for y in years:
			tyv = dat[dat[:, 0] == y]
			if len(tyv) == 12:
				d = list(tyv[:, 2])
			else:
				d = [None] * 12
				for ln in tyv:
					d[int(ln[1] - 1)] = ln[2]
			gdat.append([y, [round(v, 2) if v is not None else None for v in d]])
		return gdat

	def getPoint(self, ind):
		if type(ind) is str:
			ind = self.codes[ind]
		else:
			ind = int(ind)
		tm = self.meta[ind]
		gdat = self.readDataFile(tm['code'])
		return createCliDat(meta=tm, gdat=gdat, fillValue=None)

	def readMeta(self, fn):
		files=os.listdir(self.dataPath)
		ma = np.genfromtxt(fn, delimiter=';', skip_header=1, dtype=None)
		names = ['ind', 'code', 'isDiscontinued', 'name', 'country', 'lat', 'lon', 'elevation', 'timeZone']
		meta = dict()
		codes = dict()
		for ln in ma:
			d = {k: v for k, v in zip(names, ln)}
			dataFn  =r'ch4_%s_surface-flask_1_ccgg_month.txt' % (d['code'].lower())
			if dataFn in files:
				meta[d['ind']] = d
				meta[d['ind']]['dt'] = 'ch4'
				codes[d['code']] = d['ind']
		return meta, codes

	def getAllMetaDict(self):
		return self.meta


class AIRSconnection(dataConnection):

	def __init__(self, pth, lev=1, varName='CH4_VMR_A', yMax=2015):
		self.pth=pth
		self.firstObservation = datetime.datetime(2002,9,1)
		self.dt = 'ch4'
		self.yMax=yMax
		self.dataObjects = dict()
		self.lev=lev
		self.varName=varName
		self.setLatLon()
		self.cliSetMeta={'dt':'ch4'}

	def parsfn(self,fn):
		a=fn.split('.')
		year,month,day=int(a[1]), int(a[2]), int(a[3])
		lev,name,version=a[4:7]
		return year,month,day,lev,name,version

	def getFn(self,year,mon):
		""" Возвращает имя файла для данного месяца данного года
		"""
		fns=glob(self.pth+r'\%i\AIRS.%i.%02i.01.L3.RetStd0*.v6.0.9.0.*.hdf'%(year,year,mon))
		assert len(fns)<=1, "more then one file found"
		fn=fns[0] if len(fns)==1 else None
		return fn

	def getDataObj(self,year, mon):
		if year not in self.dataObjects:
			self.dataObjects[year]=[None]*12
		if self.dataObjects[year][mon-1] is None:
			fn=self.getFn(year, mon)
			if fn is not None:
				f=SD.SD(fn)
				d=f.select(self.varName)
				r=d.get()
			else:
				f,r=None,None
			self.dataObjects[year][mon-1] = [f,r]
		else:
			f, r = self.dataObjects[year][mon-1]
		return f,r

	def closeObj(self,year,mon):
		if year in self.dataObjects:
			if self.dataObjects[year][mon-1] is not None:
				self.dataObjects[year][mon-1][0].end()
				self.dataObjects[year][mon-1] = [None, None]

	def setLatLon(self, year=None, month=None):
		f, r = self.getDataObj(self.firstObservation.year, self.firstObservation.month)
		self.lat = f.select('Latitude')
		self.latvals = self.lat.get()[:,0]
		self.lon = f.select('Longitude')
		self.lonvals = [cLon(v) for v in self.lon.get()[0,:]]
		self.seaLandMask = f.select('LandSeaMask').get()
		return self.latvals, self.lonvals


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

	def __specifyInd__(self, item):
		try:
			latInd, lonInd = item
		except TypeError:
			latInd, lonInd = self.ind2latindlonind(item)
		except:
			print item
			raise
		return latInd, lonInd

	def latlonInd2ind(self, latInd, lonInd):
		"""
		Расчитывает индекс ячейки из индексов по x,y
		"""
		return int(latInd*len(self.lonvals)+lonInd)

	def ind2latindlonind(self, ind):
		""" переводит номер узла в индексы массива """
		latInd=int(ind/len(self.lonvals))
		lonInd=ind - latInd*len(self.lonvals)
		return latInd, lonInd

	def getNearestPoint(self, lat, lon):
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
		return self.latlonInd2ind(latInd, lonInd)

	def getNeighboring(self, item, lev=1):
		latInd, lonInd = self.__specifyInd__(item)
		vals = [[latInd+1,lonInd-1],[latInd+1,lonInd],[latInd+1,lonInd+1],[latInd,lonInd-1],[latInd,lonInd],
				[latInd,lonInd+1],[latInd-1,lonInd-1],[latInd-1,lonInd],[latInd+1,lonInd-1]]
		r = [self.latlonInd2ind(*v) for v in vals]
		if lev>1:
			for i in range(1,lev):
				tmp = set()
				for ind in r:
					tmp.union(set(self.getNeighboring(ind)))
				r=list(set(r).union(tmp))
		return r

	def getPoint(self, item):
		latInd, lonInd = self.__specifyInd__(item)
		meta={'ind':self.latlonInd2ind(latInd, lonInd), 'lat':self.latvals[latInd], 'lon':self.lonvals[lonInd],
			  'dt':self.dt}
		gdat=[]
		for year in range(self.firstObservation.year, self.yMax):
			ln=[-999.99]*12
			for mon in range(1,13):
				f, r = self.getDataObj(year,mon)
				if r is not None:
					v=r[self.lev-1,latInd,lonInd]
					if v < 0 :continue
					ln[mon-1]=float(v * 10 ** 9)
			gdat.append([year,ln])
		return createCliDat(meta=meta, gdat=gdat, fillValue=-999.99)

	def getAllMetaDict(self):
		res=dict()
		ind=0
		for lat,lon in itertools.product(self.latvals,self.lonvals):
			res[ind]={'ind':ind, 'lat':lat, 'lon':lon, 'dt':self.dt}
			ind+=1
		return res