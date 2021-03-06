﻿# coding=utf-8
"""
Классы для добавления функций уникальных для данного элемента, сложных в расчёте
или нужных в рамках какой-то одной работы.
Использует абстрактные классы климатических данных описаные в модуле altCliData.
Класс tempData представляет собой пример класса функций уникальных для данного элемента.
Класс stData хранит метаинформацию о станции, а также классы данных по каждой метео величине.

>>> from dataConnections import cmip5connection
>>>	conn=cmip5connection(r'.\HadGEM-ES_pr_historical.nc')
>>> cda=metaData({'dt':conn.dt}, dataConnection=conn)
"""
__author__ = 'Vasily Kokorev'
__email__ = 'vasilykokorev@gmail.com'

from clidata import *
from geocalc import calcDist
from common import timeit
from common import elSynom


class tempData(cliData):
	"""
	Класс релизующий функции расчёта показателей спечифичных для температуры воздуха
	"""

	def ddt(self, minY=0, maxY=0):
		minY, maxY, minInd, maxInd = self.minmaxInd(minY, maxY)
		res = [cc.sumMoreThen(y[1].vals, 0)*30.5 for y in self.data[minInd:maxInd + 1]]
		time = [y[0] for y in self.data[minInd:maxInd + 1]]
		return res,time


def createCliDat(meta, gdat=None, fillValue=None):
	dt = elSynom[meta['dt']]
	if dt == 'temp':
		dataObj = tempData(meta, gdat, fillValue=fillValue)
	else:
		dataObj = cliData(meta, gdat, fillValue=fillValue)
	return dataObj



class metaData:
	"""
	класс для работы с наборами метеостанций
	реализует различные ф-ии выборки метеостанций - по гео. положению, по длинне рядов и т.п.
	большинство ф-й возвращают self.stInds который содержит список обектов metaSt
	"""
	def __init__(self, meta, stList=None, dataConnection=None):
		"""

		@param meta:
		@param stList: create metaData instans from list of cliData instances
		@param dataConnection: connection to 'database'; dataConnection instance
		@return:
		"""
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
		try:
			meta['dt'] = elSynom[meta['dt']]
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
				pass
				#raise IOError, 'fail to load %s'%source
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


	def calcTask(self, task):
		"""
		Просчитывает задание для каждой станции набора
		"""
		result=dict()
		for st in self:
			r=st.calcTask(task)
			result[st.meta['ind']]=r
		return result


	def findXnearest(self, x, lat, lon, yMin=0, yMax=0):
		"""
		ф-я нахождения Х ближайших станций от данной точки
		Возвращает список с номерами станций
		"""
		res = []
		for st in self: #tSt
			m=st.meta
			dist, angl = calcDist(lat, lon, m['lat'], m['lon'])
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

	def setRegAvgData(self, yMin=None, yMax=None, weight=None, greedy=False):
		"""
		вычисляет осреднеённый ряд по региону, овзвращает объект класса stData
		по умолчанию алгоритм составляет составляет ряд для периода за который наблюдения есть на всех осредняемых станциях
		для использование осреднения с весами надо передать в необязательном элементе weight ф-ю которая принимает объект станции и возвращает её вес
		принимает
			yMin,yMax - int, необязательный - границы периода осреднения
			weight - словарь весов станцийб если не задан то арифметическое осреднение
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
				if year in self[ind].timeInds:
					ti = self[ind].timeInds[year]
					vals=self[ind].data[ti].filled(-999.99)
				else:
					vals=np.array([-999.99]*12)
				allDat.append(vals)
			dat=np.ma.masked_values(allDat, -999.99, copy=True)
			ws=[weight[ind] for ind in self.stInds] if weight is not None else None
			if dat.mask.all():continue
			try:
				r=np.ma.average(dat,axis=0, weights=ws)
				gdat.append([year,r.tolist(fill_value=-999.99)])
			except ZeroDivisionError:
				gdat.append([year,[-999.99]*12])
			except TypeError:
				r=np.average(dat,axis=0, weights=ws)
				gdat.append([year,r.tolist()])
		numStUsed=sum([1 for i in weight if weight[i]!=0]) if weight is not None else len(self)
		meta=dict(self.meta)
		meta.update({'ind':0,'lat':0,'lon':0, 'stUsed':numStUsed})
		cdo=cliData(meta, gdat)
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


	def correlationMatrix(self,yMin=-1,yMax=-1,season=None,function='s_avg'):
		"""
		Матрица корреляций для станций из набора
		"""
		from scipy import stats
		series=dict()
		inds=[st.meta['ind'] for st in self]
		if season is None: season={'y':range(1,13)}
		snames=season.keys()
		assert len(snames)==1, "this function work with one season at the time"
		sname=snames[0]
		for st in self:
			r=st.getParamSeries(function,[season],yMin=yMin,yMax=yMax, converter=lambda a:a[sname])
			series[st.meta['ind']]=r
		#corMatrix=np.corrcoef(series)
		corMatrix={ind:dict() for ind in series}
		cmList=list()
		cRegMeanCorr=list()
		for ind1 in series:
			cmListRow=list()
			for ind2 in series:
				if ind1!=ind2:
					try:
						c=corMatrix[ind2][ind1]
					except KeyError:
						tYmin=max([min(series[ind1][1]),min(series[ind2][1])])
						tYmax=min([max(series[ind1][1]),max(series[ind2][1])])
						d1=series[ind1][0][series[ind1][1].index(tYmin) : series[ind1][1].index(tYmax)]
						d2=series[ind2][0][series[ind2][1].index(tYmin) : series[ind2][1].index(tYmax)]
						d=[[v1,v2] for v1,v2 in zip(d1,d2) if v1 is not None and v2 is not None]
						c=stats.pearsonr([v[0] for v in d],[v[1] for v in d])[0]
						c=round(c,3)
						cRegMeanCorr.append(c)
				else:
					c=1
				corMatrix[ind1][ind2]=c
				cmListRow.append(c)
			cmList.append(cmListRow)
		return corMatrix, [inds,cmList], cc.avg(cRegMeanCorr,3)


if __name__ == "__main__":
	pass
