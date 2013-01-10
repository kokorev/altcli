# coding=utf-8
"""
Модуль содержит функции вычисляющие простейшие параметры приминительно к
климатическим данным. Все функции имеют корректную обработку пропусков.
Пропуски обозначаются как None.
данные ф-ии не входя в класс cliDat или в какой-либо другой класс altCli т.к.
не не требуют никакой информации о данных, и используются намного чаще чем cliData
"""

def ampl(d, precision=2):
	"""
	Принимает одномерный список.
	вычисляет амплитуды значений списка
	"""
	assert type(d[0]) != list
	return round(abs(max(d) - min(d)), precision)


def sumMoreThen(d, x, precision=2):
	"""
	Принимает одномерный список.
	Возвращает сумму значений больше X из списка d
	Обработка пропусков - если ни одно из соседних с пропуском
	значений удоволетворяет условию и не больше одного пропуска подряд, игнорируем пропуск"""
	if None in d:
		pm = [n for n, v in enumerate(d) if v == None]
		for mm in pm:
			if mm == 0 or mm == len(d) - 1: continue # если пропущен первый или последний элемент
			if d[mm + 1] > x or d[mm - 1] > x or d[mm + 1] == None or d[mm - 1] == None: # если два None подряд или None рядом с нужным числом
				r = None
				break
		else:
			r = round(sum([m for m in d if m > x and m != None]), precision)
	else:
		r = round(sum([m for m in d if m > x]), precision)
	return r


def sumLessThen(d, x, precision=2):
	"""
	Принимает одномерный список.
	Возвращает сумму значений больше X из списка d
	Обработка пропусков - если два соседних с пропуском
	значения не удоволетворяют условию, игнорируем пропуск"""
	if None in d:
		pm = [n for n, v in enumerate(d) if v == None]
		for mm in pm:
			if mm == 0 or mm == len(d) - 1: continue
			if d[mm + 1] < x or d[mm - 1] < x or d[mm + 1] == None or d[mm - 1] == None:
				r = None
				break
		else:
			r = round(sum([m for m in d if m < x and m != None]), precision)
	else:
		r = round(sum([m for m in d if m < x]), precision)
	return r


def avg(d, precision=2):
	"""
	Принимает одномерный список.
	возвращает среднее значение по списку """
	vals = [m for m in d if m != None]
	if len(vals) > 0:
		res = round(sum(vals) / float(len(vals)), precision)
	else:
		res = None
	return res

def movingAvg(dat,time, x, allowNone=0, precision=2):
	"""
	расчитывет скользящее среднее в окне x Лет
	Принимет:
		dat - ряд значений
		time - ряд времени
		x - длинна интервала сглаживания, должно быть не чётным
		allowNone - при каком количестве пропусков на участке x,
		среднее ещё может быть посчитано. По умолчанию - 0
	Возвращает:
		d - сглаженный ряд значений
		t - ряд времени
	"""
	dat,time=insertNone(dat,time)
	half=(x-1)/2
	t,d=[],[]
	for i in range(len(dat)):
		try:
			vals=dat[i-half:i+half+1]
		except IndexError:
			continue
		else:
			if len([k for k in vals if k!=None])<x: #-x/5
				d.append(None)
				t.append(None)
			else:
				d.append(avg(vals,precision=precision))
				t.append(time[i])
	return d,t


def insertNone(vals,time):
	"""
	Вставляет пропуски в ряд данных так чтобы шаг по времени был равен 1
	принимает:
		vals - значения
		time - время
	возвращает:
		значения, время со вставлеными пропусками
	"""
	rv,rt=[],[]
	for tind,t in enumerate(time):
		if tind!=0 and t != time[tind-1]+1:
			nn=t-(time[tind-1]+1)
			for i in range(nn):
				rv.append(None)
				rt.append(time[tind-1]+1+i)
		rv.append(vals[tind])
		rt.append(t)
	return rv,rt
