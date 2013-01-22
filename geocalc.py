# coding=utf-8
"""
Общие функции геометрии и картографии
"""
from voronoi import *

def cLon(lon):
	""" Convert longitude to 181+ format """
	if lon<0:
		lon=360+lon
	return lon


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

def isPointInPoly(x, y, poly):
	"""
	Устаревшая - рекомендуется использовать встроенную ф-ю библиотеки shapely

	впомогательная ф-я, проверяет нахдиться ли точка (x,y) внутри полигона Poly
	использует ray casting алгоритм. (не работает в точках лежащих на линии плоигона (может вернуть как true так и false))
	используеться классом metaData
	"""
	#TODO: Добавить аругмент box, для предпроверки попадения точки в регион полигона
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


def shpFile2shpobj(fn):
	"""
	Читает shp файл, возвращает объект shapely или список объектов
	В настоящий момент пытается считать всё в полигоны
	"""
	#TODO: Сделать проверку на тип информации в файле (полигон, линия, точки) и читать каждый тип в правлиьный объект
	import shapefile as shp
	from shapely.geometry import Polygon
	sf = shp.Reader(fn)
	if len(sf.shapes())>1:
		res=[]
	for sp in sf.shapes():
		lonmin,latmin,lonmax,latmax=sp.bbox
		lonmin,lonmax=cLon(lonmin),cLon(lonmax)
		if lonmin<0 or lonmax<0:
			polygonPoints=[[cLon(cors[0]),cors[1]] for cors in sp.points]
		else:
			polygonPoints=sp.points
		poly=Polygon(polygonPoints)
		if len(sf.shapes())>1:
			res.append(poly)
		else:
			res=poly
	return res


def voronoi(cdl,maskPoly):
	"""
	Расчитывает полигоны тиссена для каждой станции из cdl ограниченые контуром полигона
	Возвращает словарь {индекс станции: Полигон shapely}
	Если у станции нету полигона внутри задоного контура, будет стоять None
	"""
	from voronoi import voronoi_poly
	from shapely.geometry import Point
	from clidataSet import metaData
	import shapely.geos
	pl=dict()
	if type(cdl)==dict:
		pl=cdl
	elif isinstance(cdl, metaData):
		pl={ind:(meta['lon'], meta['lat']) for ind,meta in cdl.stMeta.items()}
	else:
		raise ValueError, "First argument should be {ind:(lat, lon)} dict or metaData instance"
	lats=[meta['lat'] for ind,meta in cdl.stMeta.items()]
	lons=[meta['lon'] for ind,meta in cdl.stMeta.items()]
	box=list(maskPoly.bounds) #(minx, miny, maxx, maxy) [90, -180, -90, 180]
	bbox=[max(lats) if max(lats)>box[3] else box[3],min(lons) if min(lons)<box[0] else box[0],
	      min(lats) if min(lats)<box[1] else box[1],max(lons) if max(lons)>box[2] else box[2]]
	vl=voronoi_poly.VoronoiPolygons(pl, PlotMap=False, BoundingBox=bbox)
	result=dict()
	for ind, r in vl.items():
		try:
			res=maskPoly.intersection(r['obj_polygon'])
		except shapely.geos.TopologicalError:
			result[r['info']]=None
			continue
		if res.geom_type=='MultiPolygon':
			point=Point(r["coordinate"][0],r["coordinate"][1])
			for ply in res.geoms:
				if ply.contains(point):
					res=ply
					break
			else:
				plylist=[v for v in res.geoms]
				plylist.sort(key=lambda a: a.area)
				res=plylist[-1]
		elif res.geom_type=='GeometryCollection':
			if res.is_empty:
				res=None
			else:
				print res
		elif res.geom_type=='Polygon':
			pass
		else:
			print res
		result[r['info']]=res
	return result