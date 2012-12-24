# coding=utf-8
"""
Общие функции геометрии и картографии
"""

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