# coding=utf-8
"""
Программа ранжирования моделей, по набору регионов и параметров.
Управляющий класс - ModelsEvaluation, создаём его экземпляр
>>> me=ModelsEvaluation(r'P:\Dropbox\proj\strl_modelCompForNCity\prj', 'tas')
Добавляем регион сравнения
>>> me.addRegion(r'reg02','E:\\data\\_arc_bank\\reg17\\17reg02.shp')
Добавляем даныне по одной модели
>>> me.addModel(r'E:\data\cmip5\data\tas\historical\CanESM2_historical.nc')
Добавляем задание расчёта
Годовой тренд
>>> me.addTask({'trend70-99': {'fn': 'trend', 'param': [1970, 1999], 'converter': lambda a: round(a[0] * 100, 2)}})
сумма положительных температур
>>> me.addTask({'ddt70-99': {'fn': 'trendParam', 'param': ['conditionalSum',[0], 1970, 1999, lambda a: a[0], 3], 'converter':lambda a: a[0]*100}})
Тренд зимних температур
>>> me.addTask({'winterTrend':{'fn': 's_trend', 'param': [1970, 1999, {'w':[-1,1,2]}, 3], 'converter':lambda a: a['w'][0]*100}})
Расчтиать задание по добавленым моделям
>>> ro=me.getResultsObj()
Вывести результаты сравнения модели в виде таблицы, также записывается в *.csv файл
>>> print ro.getParametrTable('trend70-99')
Таблица рангов моделей
>>> ro.getParametrRank('trend70-99')
Сохранить проект
>>> me.save()
"""

import dill
import pickle
import shutil
import os
import logging
import glob
from altCli.dataConnections import cmip5connection as c5c
from altCli import metaData
from altCli import cliData
from altCli.geocalc import shpFile2shpobj
from altCli import cc
from altCli.common import timeit

logging.basicConfig(format = u'%(filename)s[LINE:%(lineno)d]# %(levelname)-8s [%(asctime)s]  %(message)s', level = logging.DEBUG)

class Model(object):
	"""

	@param source:
	"""

	def __init__(self, source):
		"""
		если source - строка указывающая файл с данными cmip5 то при инициализации создаётся объект metaData
		если source словарь вида {'source':sourceSrc, } то объект metaData создаётся при первом обращении,
		а остальные данные из словаря переносятся в self.meta
		"""
		if type(source) is str:
			self.source = source
		elif type(source) is dict:
			assert 'source' in source, "initializing dictionary should have 'source' key in it"
			self.source = source['source']
		self.fullyInit=False

	def __late_init__(self):
		cdo, conn = self.getCDO(self.source)
		self.cdo = cdo
		self.conn = conn
		self.meta = conn.cliSetMeta
		self.fullyInit=True

	@staticmethod
	def getCDO(source):
		"""

		@param source:
		@return: @raise:
		"""
		try:
			conn = c5c(source)
		except:
			logging.critical( 'Failed to load model %s' % source )
			raise
		else:
			cdo = metaData(meta={'dt': conn.cliSetMeta['dt']}, dataConnection=conn)
		return cdo, conn

	def __getitem__(self, key):
		if not self.fullyInit: self.__late_init__()
		if key in self.meta:
			result = self.meta[key]
		elif key == 'cdo':
			if self.cdo is None: self.cdo, self.conn = self.getCDO(self.source)
			result = self.cdo
		elif key == 'conn':
			if self.cdo is None: self.cdo, self.conn = self.getCDO(self.source)
			result = self.conn
		return result

	def save(self):
		if self.fullyInit:
			res=self.meta
		else:
			res={'source':self.source}
		return res


	@staticmethod
	def load(saved):
		return Model(saved)


class ModelsEvaluation(object):
	"""
	Класс для приложения по сравнению моделей
	"""
	#todo: добавить поддержку разных метеовеличин.
	# Видимо необходимо объединять наборы данные для разных величин на более высоком уровне,
	# иначе надо будет указывать лишком много всего для доступа к каждому объекту,
	# к тому же большая часть функция работает только для одного типа данных
	#todo: тестировать

	def __init__(self,project,dt):
		head, tail=os.path.split(project)
		self.projectName=tail
		self.homesrc = os.path.abspath(head)+'\\'
		self.dt = dt
		self.scenario='historical'
		self.createFoldersTree()
		self.regions = dict()
		self.models = dict()
		self.regionMeanData = dict()
		self.tasks = dict()
		self.obsDataSet=None
		self.obsMeanData=dict()
		self.obsResults=dict()


	def createFoldersTree(self):
		""" создать необходимые папки под проект
		"""
		for src in [r'\data\models\%s\%s'%(self.dt,self.scenario), r'\data\obs\%s'%self.dt, r'\regshp',r'\results\%s'%self.dt]:
			try:
				os.makedirs(self.homesrc+src)
			except WindowsError:
				continue


	@property
	def cliDataObjList(self):
		return [[self.getModelRegionMean(reg, mod),reg,mod] for mod in self.models for reg in self.regions]


	def addRegion(self, name, shpFl):
		""" Добавление региона в проект
		"""
		assert name not in self.regions, "This region name have already exist"
		try:
			shpFile2shpobj(shpFl)
		except:
			logging.critical( "%s shapefile load have failed"%shpFl )
			raise
		else:
			head, tail=os.path.split(shpFl)
			oldFn, ext=tail.split('.')
			for fn in glob.glob(head+'\\'+oldFn+'.*'):
				ext=fn.split('.')[-1]
				shutil.copy2(shpFl, self.homesrc + 'regshp\\%s.%s' % (name,ext))
			self.regions[name] = {}
			self.regionMeanData[name] = dict()
		self.updateRegionalMeans()


	def loadRegion(self,name):
		""" Загрузку региона шэйп которого уже был добавлен в проект
		@param name:
		"""
		assert name not in self.regions, "This region name have already exist"
		shpFl='.\\regshp\\%s.shp'%name
		try:
			shpFile2shpobj(shpFl)
		except:
			logging.critical( "%s shapefile load have failed"%shpFl )
			raise
		else:
			self.regions[name] = {}
			self.regionMeanData[name] = dict()
		self.updateRegionalMeans()


	def addModels(self, source):
		"""

		@param source:
		"""
		if type(source) is str:
			source=os.path.normpath(source)
			if os.path.isdir(source):
				modelsLst=glob.glob(source+'\*.nc')
			else:
				modelsLst=[source]
			for ms in modelsLst:
				mo = Model(ms)
				self.models[mo['modelId']] = mo
			self.updateRegionalMeans()
		elif hasattr(source, '__iter__'):
			for el in source:
				self.addModels(el)


	def addTask(self,task):
		"""
		Добавляет задание(я) в словарь заданий
		:param task: task dictionary
		 Example 'trend70-99': {'fn': 'trend', 'param': [1970, 1999], 'converter': lambda a: round(a[0] * 100, 2)}
		"""
		assert type(task) is dict
		self.tasks.update(task)


	def setObsData(self, inpt):
		"""

		@param inpt:
		@return:
		"""
		if type(inpt) is str:
			try:
				self.obsDataSet=metaData.load(inpt)
			except:
				pass
		else:
			self.obsDataSet=inpt



	def calcRegionalMean(self, reg, mod, replace=False):
		assert reg in self.regions, "Region have not been added"
		assert mod in self.models, "Model have not been added"
		modObj = self.models[mod]['cdo']
		shp = self.homesrc + 'regshp\\%s.shp' % reg
		dots = modObj.setStInShape(shp)
		if len(dots)>0:
			regModelObj = metaData(modObj.meta, stList=[modObj[d] for d in dots])
			cdo = regModelObj.setRegAvgData()
			cdo.save(self.getModelDataSrc(reg,mod), replace=replace)
		else:
			cdo=None
			logging.warning('no model data for region %s for model %s'%(str(reg),mod))
		self.regionMeanData[reg][mod] = cdo
		return cdo

	def calcObsRegMean(self,reg, replace=False):
		shp = self.homesrc + 'regshp\\%s.shp' % reg
		dots = self.obsDataSet.setStInShape(shp)
		if len(dots)>0:
			regObsObj = metaData(self.obsDataSet.meta, stList=[self.obsDataSet[d] for d in dots])
			cdo = regObsObj.setRegAvgData(greedy=True)
			cdo.save(self.getObsDataSrc(reg), replace=replace)
		else:
			cdo=None
			logging.warning('no observations for region %s'%str(reg))
		self.obsMeanData[reg]=cdo
		return cdo

	def getModelDataSrc(self, reg, mod):
		assert type(mod) is str or type(mod) is unicode
		if type(reg) is not str: reg=str(reg)
		src=self.homesrc+r"data\models\%s\%s\%s_%s.acd"%(self.dt, self.scenario, mod, reg)
		return src

	def getObsDataSrc(self,reg):
		if type(reg) is not str: reg=str(reg)
		return self.homesrc+r"data\obs\%s\%s.acd"%(self.dt, reg)


	def getModelRegionMean(self, reg, mod):
		"""
		Получает среднерегиональный ряд для конкретной модели.
		Проверяет нет ли нужного объекта в словаре или в файле, если нет, то рассчитывает
		:param reg: region name
		:param mod: model ID
		:return: cliData object
		"""
		try:
			cdo = self.regionMeanData[reg][mod]
		except KeyError:
			fn=self.getModelDataSrc(reg,mod)
			try:
				cdo=cliData.load(fn,results=True)
				self.regionMeanData[reg][mod] = cdo
			except IOError:
				cdo = self.calcRegionalMean(reg, mod)
		return cdo


	def getObsRegionMean(self, reg):
		"""

		:param reg:
		:return: :raise AttributeError:
		"""
		try:
			cdo = self.obsMeanData[reg]
		except KeyError:
			fn=self.getObsDataSrc(reg)
			try:
				cdo=cliData.load(fn,results=True)
				self.obsMeanData[reg] = cdo
			except IOError:
				if self.obsDataSet is None: raise AttributeError, "please set observation data source"
				cdo = self.calcObsRegMean(reg)
		return cdo


	def getTaskResult(self,reg,mod,taskId):
		"""
		Возвращает результат расчёта одного задания для конкретного ряда. Кэширующая.
		:param reg:
		:param mod:
		:param taskId:
		:return:
		"""
		cdo=self.getModelRegionMean(reg,mod)
		try:
			ans=cdo.res[taskId]
		except KeyError:
			ans=cdo.calcTask(self.tasks[taskId])
		return ans


	def getResultsObj(self):
		return Results(self)


	def calcAllTasks(self):
		modRes= dict([(reg, dict()) for reg in self.regions])
		obsRes=dict()
		for cdo,reg,mod in self.cliDataObjList:
			if cdo is not None:
				modRes[reg][mod]=cdo.calcTask(self.tasks)
			else:
				modRes[reg][mod]=None
		for reg,cdo in self.obsMeanData.items():
			if cdo is not None:
				obsRes[reg]=cdo.calcTask(self.tasks)
			else:
				obsRes[reg]=None
		return modRes,obsRes

	def updateRegionalMeans(self, reCalcAll=False):
		"""
		Расчитывает и записывает средние ряды для каждой модели и наблюдений для каждого региона
		если они не были расчитаны ранее
		"""
		#self.regionMeanData[reg][mod]
		for reg in self.regions:
			isRegOld=reg in self.regionMeanData
			for mod in self.models:
				if reCalcAll:
					cdo=self.calcRegionalMean(reg,mod,replace=True)
					self.regionMeanData[reg][mod] = cdo
				elif isRegOld:
					if mod in self.regionMeanData[reg]: continue
				else:
					self.getModelRegionMean(reg, mod)
			if reCalcAll and self.obsDataSet is not None:
				cdo=self.calcObsRegMean(reg,replace=True)
				self.obsMeanData[reg]=cdo
			else:
				self.getObsRegionMean(reg)

	def save(self,fn=None):
		fn=self.projectName if fn is None else fn
		modelsSaveDict = {mn:mo.save() for mn, mo in self.models.items()}
		regionsSaveDict = self.regions
		saveDict = {'models': modelsSaveDict, 'regions': regionsSaveDict, 'tasks':self.tasks, 'homesrc': self.homesrc, 'dt':self.dt, }
		print fn,self.homesrc
		pickle.dump(saveDict, open(self.homesrc + fn, 'w'))
		for cdo,reg,mod in self.cliDataObjList:
			cdo.save(self.getModelDataSrc(reg,mod),replace=True, results=False)

	@staticmethod
	@timeit
	def load(fn):
		fn=os.path.abspath(fn)
		head, tail=os.path.split(fn)
		sd = pickle.load(open(fn,'r'))
		loaded = ModelsEvaluation(tail, sd['dt'])
		loaded.models = {k:Model(v) for k,v in sd['models'].items()}
		loaded.regions = sd['regions']
		loaded.obsMeanData=dict()
		for reg in sd['regions']:
			loaded.regionMeanData[reg]=dict()
		loaded.homesrc = sd['homesrc']
		loaded.tasks = sd['tasks']
		loaded.dt=sd['dt']
		loaded.updateRegionalMeans()
		return loaded


class Results(object):
	"""
	Класс обработки результатов сравнения моделей
	"""
	def __init__(self, parent):
		modRes,obsRes=parent.calcAllTasks()
		self.parent=parent
		self.dt=parent.dt
		self.modr=modRes
		self.obsr=obsRes
		self.regions=list(self.obsr.keys())
		self.regions.sort()
		self.models=list(self.modr[self.regions[0]].keys())
		self.models.sort()
		self.rankFunction=lambda m,o: (m-o)/float((m+o)) if (m is not None) and (o is not None) else None
		self.rankSumFunction=lambda val: cc.avg([abs(v) if v is not None else None for v in val],2)
		self.mr=dict() # modelsRanks


	def listtable2txt(self, table):
		return '\n'.join([';'.join([str(v) for v in ln]) for ln in table])


	def calcRanks(self,taskName):
		if taskName not in self.mr:
			self.mr[taskName]=dict()
			self.mr[taskName]['reg']=dict()
			self.mr[taskName]['total']=dict()
			rf=self.rankFunction
			for m in self.models:
				rs={r:rf(self.modr[r][m][taskName],self.obsr[r][taskName]) if self.modr[r][m] is not None and self.obsr[r] is not None else None for r in self.regions}
				self.mr[taskName]['reg'][m]=rs
				self.mr[taskName]['total'][m]=self.rankSumFunction(rs.values())


	def getParametrTable(self,taskName, converter=lambda a: round(a,2) if a is not None else None):
		head=['model']+self.regions
		obsline=['_obs']+[converter(self.obsr[r][taskName]) if self.obsr[r] is not None else 'None' for r in self.regions]
		arr=[head, obsline]
		for m in self.models:
			line=[m]+[converter(self.modr[r][m][taskName]) if self.modr[r][m] is not None else 'None' for r in self.regions]
			arr.append(line)
		txt=self.listtable2txt(arr)
		with open(self.parent.homesrc+'results\\%s\\%s_%s_values.csv'%(self.dt,self.parent.projectName,taskName),'w') as f: f.write(txt)
		return txt


	def getParametrRank(self,taskName):
		self.calcRanks(taskName)
		table=list()
		for m in self.models:
			table.append([m, self.mr[taskName]['total'][m]])
		table.sort(key=lambda a:a[1])
		txt=self.listtable2txt(table)
		with open(self.parent.homesrc+'results\\%s\\%s_%s_ranks.csv'%(self.dt,self.parent.projectName,taskName),'w') as f: f.write(txt)
		return txt


	def getTotalRank(self,tasksList):
		table=list()
		for t in tasksList:
			self.calcRanks(t)
		for m in self.models:
			v=self.rankSumFunction([self.mr[t]['total'][m] for t in tasksList])
			table.append([m,v])
		table.sort(key=lambda a:a[1])
		txt=self.listtable2txt(table)
		with open(self.parent.homesrc+'results\\%s\\TotalRank_%s_%s_ranks.csv'%(self.dt,self.parent.projectName,str(tasksList)),'w') as f: f.write(txt)
