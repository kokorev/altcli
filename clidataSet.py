# coding=utf-8
"""
Классы для добавления функций уникальных для данного элемента, сложных в расчёте
или нужных в рамках какой-то одной работы.
Использует абстрактные классы климатических данных описаные в модуле altCliData.
Класс tempData представляет собой пример класса функций уникальных для данного элемента.
Класс stData хранит метаинформацию о станции, а также классы данных по каждой метео величине.
"""
__author__ = 'Vasily Kokorev'
__email__ = 'vasilykokorev@gmail.com'

from clidata import *
from common import timeit

class tempData(cliData):
	"""
	Класс релизующий функции расчёта показателей спечифичных для температуры воздуха
	"""

	def ddt(self, minY=0, maxY=0):
		minY, maxY, minInd, maxInd = self.minmaxInd(minY, maxY)
		res = [cc.sumMoreThen(y[1].vals, 0)*30.5 for y in self.data[minInd:maxInd + 1]]
		time = [y[0] for y in self.data[minInd:maxInd + 1]]
		return res,time


def createCliDat(meta, gdat=None, cfg=None):
	if cfg == None:
		cfg = config()
		cfg.get = None # Зануляем ф-ю загрузки новых данных
		cfg.getMeta = None # И ф-ю загрузки методанных
	dt = cfg.elSynom[meta['dt']]
	if dt == 'temp':
		dataObj = tempData(meta, gdat, cfg)
	else:
		dataObj = cliData(meta, gdat, cfg)
	return dataObj



class metaData:
	"""
	класс для работы с наборами метеостанций
	реализует различные ф-ии выборки метеостанций - по гео. положению, по длинне рядов и т.п.
	большинство ф-й возвращают self.stInds который содержит список обектов metaSt
	"""
	def __init__(self, meta, cfgObj=None, stList=None, dataConnection=None):
		self.__name__ = 'metaData'
		self.dataConnection=dataConnection
		self.clidatObjects=dict() if stList is None else {st.meta['ind']:st for st in stList}
		if self.dataConnection is None:
			self.stMeta=dict() if stList is None else {st.meta['ind']:st.meta for st in stList}
		else:
			self.stMeta=self.dataConnection.getAllMetaDict()
		if stList is None:
			if dataConnection is None:
				self.stInds=list()
			else:
				self.stInds=[ind for ind in self.stMeta]
		else:
			self.stInds=[st.meta['ind'] for st in stList]

		self.cfg = config() if cfgObj is None else cfgObj
		try:
			meta['dt'] = self.cfg.elSynom[meta['dt']]
		except KeyError:
			print meta['dt']
			raise KeyError, "dt field is not exist or has unknown value"
		if self.dataConnection is not None:
			meta.update(self.dataConnection.cliSetMeta)
		self.meta = meta
		self.minInd = 0

	#todo: добавить функцию добавления станций из подключённых данных

	@staticmethod
	def load(fn):
		import os.path
		if fn[-4:] != '.acl': fn += '.acl'
		abspath = os.path.abspath(fn)
		pth, filename = os.path.split(abspath)
		f = open(fn, 'r')
		# убирём строчки с коментариями из метоинформации
		txt = '\n'.join([line for line in f.readlines() if line.strip()[0]!='#'])
		stxt = txt.split('}')       # отделяем метаинформацию от данных
		meta = eval(stxt[0] + '}')
		cliDataList=list()
		for source in [l.strip() for l in stxt[1].split(',')]:
			if not os.path.isabs(source):
				source=pth+os.sep+source
			try:
				cdo=cliData.load(source)
				cliDataList.append(cdo)
			except IOError:
				raise IOError, 'fail to load %s'%source
		cfg = config()
		cfg.get = None # Зануляем ф-ю загрузки новых данных
		cfg.getMeta = None # И ф-ю загрузки методанных
		acl = metaData(meta)
		acl.addSt(cliDataList)
		return acl

	def save(self, fn, replace=False, ignoreExisting=False):
		"""
		сохраняет набор данных.
		Покаждому объекту acd + acr (данные + метаинформация + результаты расчётов)
		"""
		import os.path
		if fn[-4:] != '.acl': fn += '.acl'
		if os.path.exists(fn):
			if replace == False:
				raise IOError, 'File %s already exist. Change file name or use replace=True argument' % fn
		if not os.path.isabs(fn): fn = os.path.abspath(fn)
		pth, filename = os.path.split(fn)
		f = open(fn, 'w')
		stl = ','.join([str(st.meta['ind']) for st in self])
		txt = "# %s \n%s \n%s \n" % ("набор данных без описания", str(self.meta), stl)
		f.write(txt)
		f.close()
		for st in self:
			try:
				scrfn = pth + '\\' + str(st.meta['ind'])
				st.save(scrfn, replace)
			except IOError:
				if ignoreExisting == True:
					continue
				else:
					raise IOError, 'File %s already exist. Use ignoreExisting=True or replace=True argument' % scrfn


	def __getitem__(self, ind):
		"""
		Системная функция отвечающая за обработки оператора []
		возвращает экземпляр yearData
		"""
		if type(ind)!=int: ind = int(ind)
		try:
			cdo=self.clidatObjects[ind]
		except KeyError:
			if ind in self.stInds and self.dataConnection is not None:
				cdo=self.dataConnection.getPoint(ind)
			else:
				raise KeyError, "There is no index %i in index list"%ind
		return cdo


	def __delitem__(self, ind):
		"""
		Системная функция отвечающая за обработки оператора del.
		Удаяет из объекта metaData станцию с индексом ind
		возвращает self
		"""
		if type(ind)!=int: ind = int(ind)
		try:
			del self.clidatObjects[ind]
			self.stInds.remove(ind)
		except KeyError, ValueError:
			raise KeyError, "Станции %i нет в списке"%ind
		return True

	def __len__(self):
		return len(self.stInds)

	def __iter__(self):
		self.thisInd = self.minInd
		return self


	def next(self):
		if self.thisInd >= len(self.stInds): raise StopIteration
		ret = self.stInds[self.thisInd]
		self.thisInd += 1
		if self.dataConnection is None and len(self.clidatObjects)==0: raise ValueError, "unable to iterate - self.clidatObjects is empty"
		res=self[ret]
		return res


	def addSt(self, stListToAdd):
		""" добавляет станции в self.stInds если их ещё там нет """
		for st in stListToAdd:
			ind=st.meta['ind']
			if ind not in self.stInds:
				self.clidatObjects[int(ind)]=st
				self.stInds.append(int(ind))
				self.stMeta[int(ind)]=st.meta
		return self.stInds

	def __str__(self):
		"""
		ф-я обработки объекта этого класса ф-й str()? возвращает список станций через табуляцию
		"""
		res = ""
		for s in self.stInds:
			res += str(self[s].meta['ind']) + '\t'
		return res


	def findXnearest(self, x, lat, lon, yMin=0, yMax=0):
		"""
		ф-я нахождения Х ближайших станций от данной точки
		Возвращает список с номерами станций
		"""
		res = []
		for st in self: #tSt
			m=st.meta
			dist, angl = self.calcDist(lat, lon, m['lat'], m['lon'])
			res.append([dist, m['ind']])
		res = sorted(res, key=lambda a:a[0])
		return res[:x]


	def setStInShape(self,shpfile):
		"""
		Функция возвращает список станций попадающий в полигон(ы) из шэйпфайла файла
		"""
		import shapefile as shp
		import geocalc
		from shapely.geometry import Polygon,Point
		res=[]
		sf = shp.Reader(shpfile)
		for sp in sf.shapes():
			res_tmp=[]
			lonmin,latmin,lonmax,latmax=sp.bbox
			lonmin,lonmax=geocalc.cLon(lonmin),geocalc.cLon(lonmax)
			if lonmin<0 or lonmax<0:
				polygonPoints=[[geocalc.cLon(cors[0]),cors[1]] for cors in sp.points]
			else:
				polygonPoints=sp.points
			poly=Polygon(polygonPoints)
			indsInBox=[ind for ind in self.stInds if lonmin<=geocalc.cLon(self.stMeta[ind]['lon'])<=lonmax and latmin<=self.stMeta[ind]['lat']<=latmax]
			for ind in indsInBox:
				lat,lon=self.stMeta[ind]['lat'], geocalc.cLon(self.stMeta[ind]['lon'])
				pnt=Point(lon,lat)
				if poly.contains(pnt): res_tmp.append(ind)
			res=res+res_tmp
		return list(set(res))

	#TODO: функция нахождения станция прилежащих к полигону

	def setRegAvgData(self, yMin=None, yMax=None, weight=None, greedy=False, mpr=0):
		"""
		вычисляет осреднеённый ряд по региону, овзвращает объект класса stData
		по умолчанию алгоритм составляет составляет ряд для периода за который наблюдения есть на всех осредняемых станциях
		для использование осреднения с весами надо передать в необязательном элементе weight ф-ю которая принимает объект станции и возвращает её вес
		принимает
			yMin,yMax - int, необязательный - границы периода осреднения
			weight - ф-я, функция вычисления веса станции.
			mpr - максимальный процент пропуска (??)
		"""
		yMinArr=[st.meta['yMin'] for st in self]
		yMaxArr=[st.meta['yMax'] for st in self]
		if yMin is None:
			yMin=max(yMinArr) if greedy==False else min(yMinArr)
		elif yMin<min(yMinArr):
			yMin=min(yMinArr)
		if yMax is None:
			yMax=min(yMaxArr) if greedy==False else max(yMaxArr)
		elif yMax>max(yMaxArr):
			yMax=max(yMaxArr)
		gdat=[]
		for year in range(yMin,yMax+1):
			allDat=[]
			for ind in self.stInds:
				vals=list(self[ind][year].data.data)
				allDat.append(vals)
			dat=np.ma.masked_values(allDat, -999.99, copy=True)
			ws=[weight[ind] for ind in self.stInds] if weight is not None else None
			if dat.mask.all():continue
			r=np.ma.average(dat,axis=0, weights=ws)
			gdat.append([year,list(r.data)])
		numStUsed=sum([1 for i in weight if weight[i]!=0]) if weight is not None else len(self)
		cdo=cliData({'dt':self.meta['dt'],'ind':0,'lat':0,'lon':0, 'stUsed':numStUsed}, gdat)
		return cdo


	def interpolate(self, dt, valn, method='linear'):
		"""
		Функция интерполяции между всеми станциями набора.
		Принимает имя велечины в словаре результатов и метод интерполяции
		возвращает функцию
		"""
		from scipy.interpolate import Rbf
		x = [s.meta['lon'] for s in self if s[dt].res[valn] != None]
		y = [s.meta['lat'] for s in self if s[dt].res[valn] != None]
		z = [s[dt].res[valn] for s in self if s[dt].res[valn] != None]
		return Rbf(x, y, z, function=method)

if __name__ == "__main__":
	import numpy as np
	from dataConnections import cmip5connection
	conn=cmip5connection(r'D:\data\CMIP5\pr\historical\HadGEM-ES_pr_historical.nc')
	cda=metaData({'dt':conn.dt}, dataConnection=conn)
	pass

	#st=cda[22641]
	#print st.data.mask
	#res=cda.setRegAvgData(yMin=1961,yMax=2012)
	#print res


##=====================        </Конец класса metaData>     ======================================##
##/////////////////////////////////////////////////////////////////////////////////////////////##        
##=======================    </конец Классов>    ===============================================##
##/////////////////////////////////////////////////////////////////////////////////////////////##
