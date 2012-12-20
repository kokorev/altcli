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
__version__ = '2.0 beta'

from clidata import *

class tempData(cliData):
	"""
	Класс релизующий функции расчёта показателей спечифичных для температуры воздуха
	"""

	def ddt(self, minY=0, maxY=0):
		minY, maxY, minInd, maxInd = self.minmaxInd(minY, maxY)
		res = [cc.sumMoreThen(y[1].vals, 0) for y in self.data[minInd:maxInd + 1]]
		time = [y[0] for y in self.data[minInd:maxInd + 1]]
		return res,time


#TODO: нужно тщательно продумать поведение cfg при создании занулять ф-ии неправильно, нужно чтобы cfg при создании не пыталась подключиться к базе
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



#TODO: сделать простой путь создания экземпляра metaData из списка объектов cliData
class metaData:
	"""
	класс для работы с наборами метеостанций
	реализует различные ф-ии выборки метеостанций - по гео. положению, по длинне рядов и т.п.
	большинство ф-й возвращают self.stList который содержит список обектов metaSt
	"""
	def __init__(self, meta, cfgObj=None):
		self.stList = []
		self.__name__ = 'metaData'
		try:
			meta['dt'] = cfg.elSynom[meta['dt']]
		except KeyError:
			print "в meta не указано ind или dt"
			raise KeyError
		self.meta = meta
		self.cfg = cfgObj if cfgObj != None else config()
		self.minInd = 0
		self.maxInd = len(self.stList)


	def __getitem__(self, ind):
		"""
		Системная функция отвечающая за обработки оператора []
		возвращает экземпляр yearData
		"""
		if type(ind)!=int: ind = int(ind)
		try:
			slist = [s.meta['ind'] for s in self.stList]
			i = slist.index(ind)
		except ValueError:
			self.cfg.logThis("Станции " + str(ind) + " нет в списке")
			return False
		else:
			return self.stList[i]


	def __delitem__(self, ind):
		"""
		Системная функция отвечающая за обработки оператора del.
		Удаяет из объекта metaData станцию с индексом ind
		возвращает self
		"""
		assert type(ind) is int , "in metaData[ind] ind must be an integer"
		try:
			slist = [s.meta['ind'] for s in self.stList]
			i = slist.index(ind)
		except ValueError:
			self.cfg.logThis("Станции " + str(ind) + " нет в списке")
			return False
		else:
			del self.stList[i]
			self.maxInd = len(self.stList)
			return True

	def __len__(self):
		return len(self.stList)

	def __iter__(self):
		self.thisInd = self.minInd
		return self


	def next(self):
		if self.thisInd >= len(self.stList): raise StopIteration
		ret = self.stList[self.thisInd]
		self.thisInd += 1
		return ret

	#=================

	def addStToList(self, stListToAdd, meta):
		""" добавляет станции в self.stList если их ещё там нет """
		try:
			yMin, yMax = meta['yMin'], meta['yMax']
		except KeyError:
			yMin, yMax = self.cfg.yMin, self.cfg.yMax
			meta['yMin'], meta['yMax'] = yMin, yMax
		dataTypesList = self.cfg.dtList
		stToAdd = list(set(stListToAdd) - set([s.ind for s in self.stList]))
		for st in stToAdd:
			try:
				m = dict(meta)
				m.update({'ind':int(st)})
				r = createCliDat(m, gdat=None, cfg=self.cfg)
			except LookupError:
				continue # отсутствие данных записывается в лог уровнем ниже при попытке создания экземпляра cliData
			else:
				self.stList.append(r)
		self.maxInd = len(self.stList)
		return self.stList

	def __str__(self):
		"""
		ф-я обработки объекта этого класса ф-й str()? возвращает список станций через табуляцию
		"""
		res = ""
		for s in self.stList:
			res += str(s.meta['ind']) + '\t'
		return res


	def getByCond(self, cond=''):
		"""
		Выбора по из базы по собственному условию
		возвращается список станций, атоматически с этим спиком станций ничего не происходит.
		Запрос пока не экранируеться
		"""
		if cond != False: cond = 'WHERE ' + cond
		#TODO экранирование
		q = "SELECT ind FROM `" + self.cfg.di.meta + "` " + cond
		self.cfg.di.c.execute("SELECT ind FROM `" + self.cfg.di.meta + "`")
		lst = self.cfg.di.c.fetchall()
		lstr = [int(s[0]) for s in lst]
		return lstr


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

	@staticmethod
	def calcDist(lat1, lon1, lat2, lon2):
		"""
		ф-я расчёта растояния и азиматульного угла между двумя точками по их гео координатам
		растояние считаетсья в метрах, результат округляеться до целых метров ф-ей int()
		"""
		import math
		rad = 6372795. # радиус сферы (Земли)
		#косинусы и синусы широт и разницы долгот
		cl1 = math.cos(lat1 * math.pi / 180.)
		cl2 = math.cos(lat2 * math.pi / 180.)
		sl1 = math.sin(lat1 * math.pi / 180.)
		sl2 = math.sin(lat2 * math.pi / 180.)
		##delta = lon2*math.pi/180. - lon1*math.pi/180.
		cdelta = math.cos(lon2 * math.pi / 180. - lon1 * math.pi / 180.)
		sdelta = math.sin(lon2 * math.pi / 180. - lon1 * math.pi / 180.)
		#вычисления длины большого круга
		y = math.sqrt(math.pow(cl2 * sdelta, 2) + math.pow(cl1 * sl2 - sl1 * cl2 * cdelta, 2))
		x = sl1 * sl2 + cl1 * cl2 * cdelta
		ad = math.atan2(y, x)
		dist = ad * rad
		#вычисление начального азимута
		x = (cl1 * sl2) - (sl1 * cl2 * cdelta)
		y = sdelta * cl2
		z = math.degrees(math.atan(-y / x))
		if (x < 0):
			z = z + 180.
		z2 = (z + 180.) % 360. - 180.
		z2 = -math.radians(z2)
		anglerad2 = z2 - ((2 * math.pi) * math.floor((z2 / (2 * math.pi))))
		angledeg = (anglerad2 * 180.) / math.pi
		return int(dist), round(angledeg, 2)

	@staticmethod
	def setPolygon(polyFileName):
		"""
		вспмогательная ф-я, читает файл с полигоном в список вида [[x1,y1],[x2,y3]...[xN,yN]]
		используеться классом metaData
		"""
		polyFile = open(polyFileName, 'r')
		polygon = []
		for line in polyFile:
			sLine = line.split(',')
			x = float(sLine[0])
			y = float(sLine[1])
			polygon.append([x, y])
		polyFile.close()
		return polygon
	## ========================================================================================##

	@staticmethod
	def point_in_poly(x, y, poly):
		"""
		впомогательная ф-я, проверяет нахдиться ли точка (x,y) внутри полигона Poly
		использует ray casting алгоритм. (не работает в точках лежащих на линии плоигона (может вернуть как true так и false))
		используеться классом metaData
		"""
		n = len(poly)
		inside = False
		p1x, p1y = poly[0]
		for i in range(n + 1):
			p2x, p2y = poly[i % n]
			if y > min(p1y, p2y):
				if y <= max(p1y, p2y):
					if x <= max(p1x, p2x):
						if p1y != p2y:
							xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
						if p1x == p2x or x <= xinters:
							inside = not inside
			p1x, p1y = p2x, p2y
		return inside

	def setStInPoly(self, polygon=None, polyfile=None):
		"""
		Функция возвращает список станций попадающий в полигон из файла polyfile или в полигон polygon=[[lat1,lon1], [lat2,lon2], ...]
		"""
		##TODO: Придумать более быстрый алгоритм (нужна какая-то придварительная отборка быстрым способом)
		assert polygon != None or polyfile != None, "необходимо задать полигон или имя файла с полигоном"
		if polyfile != None:
			polygon = self.setPolygon(polyfile)
		elif polygon != None:
			polygon = polygon
		else:
			raise BaseException
		res = []
		for st in self.cfg.di.getAllMeta():
			if self.point_in_poly(st['lat'], st['lon'], polygon):
				res.append(int(st['ind']))
		return res

	def setRegAvgData(self, yMin=0, yMax=0, weight=lambda st: 1, mpr=0):
		"""
		вычисляет осреднеённый ряд по региону, овзвращает объект класса stData
		по умолчанию алгоритм составляет составляет ряд для периода за который наблюдения есть на всех осредняемых станциях
		для использование осреднения с весами надо передать в необязательном элементе weight ф-ю которая принимает объект станции и возвращает её вес
		принимает
			yMin,yMax - int, необязательный - границы периода осреднения
			weight - ф-я, функция вычисления веса станции.
			mpr - максимальный процент пропуска (??)
		"""
		import math
		assert len(self.stList) > 1, 'one or less st in list, impossible to get avg reg'
		stl = self.stList
		if yMin == 0:
			yMin = max([k.yMin for k in stl])
		if yMax == 0:
			yMax = min([k.yMax for k in stl])
		datRes = []
		weights = {st.meta['ind']:weight(st) for st in stl}
		# сколько минимально должнобыть станций
		minLenofvals = len(stl) - (len(stl) / 100.) * mpr
		for year in range(yMin, yMax + 1):
			thisYearRes = [None for i in range(0, 12)]
			for month in range(1, 13):
				ltoavg = []
				indtoavg=[]
				for m in stl:
					if m[year] != None and m[year][month] != None:
						ltoavg.append(m[year][month] * weights[m.meta['ind']])
						indtoavg.append(m.meta['ind'])
				vavg = sum(ltoavg) / sum([weights[stind] for stind in indtoavg]) if len(ltoavg) >= minLenofvals else None
				thisYearRes[month - 1] = round(vavg, 2) if vavg != None else None
			if thisYearRes.count(None) < len(thisYearRes):
				datRes.append([year, thisYearRes])
		lat = cc.avg([s.meta['lat'] for s in stl])
		lon = cc.avg([s.meta['lon'] for s in stl])
		meta = dict({'ind':False, 'dt':self.meta['dt'], 'yMin':int(yMin), 'yMax':int(yMax), 'lat':lat, 'lon':lon})
		return createCliDat(meta, gdat=datRes)

#===============================================================================
#    def drawStMap(self):
#        """
#        демонстрационная ф-я, наности станции на карте полушерия в ортогональной проекции
#        """
#        from mpl_toolkits.basemap import Basemap
#        import numpy as np, matplotlib.pyplot as plt
#        latList = [st.lat for st in self.stList]
#        lonList = [st.lon for st in self.stList]
# #        indList=[str(st.ind) for st in self.stList]
#        avgLat = sum(latList) / len(latList)
#        avgLon = sum(lonList) / len(lonList)
#        map = Basemap(projection='ortho', lat_0=avgLat, lon_0=avgLon, resolution='l', area_thresh=1000.)
#        map.drawcoastlines()
#        x, y = map(lonList, latList)
#        # plot filled circles at the locations of the cities.
#        map.plot(x, y, 'bo')
#        # plot the names of those five cities.
#        for xpt, ypt in zip(x, y):
#            plt.text(xpt + 50000, ypt + 50000, '')
#        map.drawmeridians(np.arange(0, 360, 30))
#        map.drawparallels(np.arange(-90, 90, 30))
#        plt.show()
#===============================================================================

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


##=====================        </Конец класса metaData>     ======================================##
##/////////////////////////////////////////////////////////////////////////////////////////////##        
##=======================    </конец Классов>    ===============================================##
##/////////////////////////////////////////////////////////////////////////////////////////////##
