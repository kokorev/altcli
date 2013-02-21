# coding=utf-8
"""

"""

def getRedBlueCM(segments=100,reverse=False):
	"""
	Возвращает красно-синюю палетку разбитую на заданое число сегментов
	Параметры:
		segments=100 - число равных отреков в палетке
		reverse=False - красный положительные значения, синие отрицательные. Если True то наоборот
	"""
	from matplotlib import colors
	bv=((0.0, 1.0, 1.0),(0.5, 1.0, 1.0),(1.0, 0.0, 0.0))
	rv=((0.0, 0.0, 0.0),(0.5, 1.0, 1.0),(1.0, 1.0, 1.0))
	gv=((0.0, 0.0, 0.0),(0.5, 1.0, 1.0),(1.0, 0.0, 0.0))
	if not reverse:
		cdict = {'blue': bv,'green': gv,'red':rv}
	else:
		cdict = {'blue': rv,'green': gv,'red':bv}
	cm = colors.LinearSegmentedColormap('my_colormap', cdict, segments)
	return cm


def interannualVariability(vals,time,trend=[None,None],fn=None,smoothing=None, xLim=[None,None], yLim=[None,None]):
	"""
	Строит график изменения величины со временем. Одна линия + тренд + скользящее среднее
	Параметры:
		vals,time - 1d массивы значений и времени, пропуски должны быть в виде None
		trend=[None,None] - границы линии тренда None - тренд не строится, -1 автоматически задаётся
			максимальная/минимальная граница, Другое - граница расчёта тренда
		fn=None - имя файла с результатом, None - показать график не сохраняя, если задано имя то график сохраняется
			под таким именем, должно быть указано расширение
		smoothing=None - сглаживание, None - линия не проводится. Если задано число то проводится линия с
			осреднением в заданое чило лет. Должно быть целым.
		xLim=[None,None], yLim=[None,None] - границы осей на графике. None - задать автоматически,
			иначе используются заданые значения.
	"""
	import matplotlib.pyplot as plt
	from altCli.clicomp import movingAvg,removeNone
	from scipy import stats
	fig=plt.figure(facecolor='w', edgecolor='k',figsize=(10,6),frameon=False)#,dpi=300
	ax=fig.add_subplot(111)
	ax.grid(True)
	# set value
	yMin,yMax=xLim[0] if xLim[0] else min(time), xLim[1] if xLim[1] else max(time)
	ax.plot(time, vals, '-', color='#5ab3f8', linewidth=1.5)
	if smoothing is not None:
		av,at=movingAvg(vals,time, smoothing)
		ax.plot(at, av, '-', color='#fb2e2e', linewidth=2.5)
	if not None in trend:
		if trend[0]==-1: trend[0]=min(time)
		if trend[1]==-1: trend[1]=max(time)
		ind1=time.index(trend[0])
		ind2=time.index(trend[1])
		valsT = vals[ind1:ind2+1]
		timeT = time[ind1:ind2+1]
		if None in vals:
			valsT,timeT=removeNone(valsT,timeT)
		if len(valsT)>10:
			sl2, inter2, r_value2, p_value2, std_err2 = stats.linregress(timeT, valsT)
			ax.plot([yMin, yMax], [inter2+sl2*yMin, sl2*max(time)+inter2], '--', color='black', linewidth=2)
		else:
			print 'Not enough data to estimate trend'
	# set axis limits
	x1,x2,y1,y2 = ax.axis()
	ax.axis((xLim[0] if xLim[0] else x1, xLim[1] if xLim[1] else x2,
	         yLim[0] if yLim[0] else y1, yLim[1] if yLim[1] else y2))
	#setfontsize and label positions
	fontsize=20
	for tick in ax.xaxis.get_major_ticks():
		tick.label1.set_fontsize(fontsize)
		tick.label1.set_position((0,-0.03))
	for tick in ax.yaxis.get_major_ticks():
		tick.label1.set_fontsize(fontsize)
		tick.label1.set_position((-0.03,0))
	# save file or show figure
	if fn:
		plt.savefig(fn)
	else:
		plt.show()
	plt.close(fig)