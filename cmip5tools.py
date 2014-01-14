# coding=utf-8
"""
Инструменты для работы с наборами моделей CMIP5
"""
import clidataSet as clidat
from clidata import cliData
from dataConnections import cmip5connection as c5c

class modelSet():
	"""
	Класс набора моделей, реалезующий ф-ии сравнения моделей и построения ансамблей
	"""
	def __init__(self,dt):
		self.models=dict()
		self.dt={'dt':dt}
		self.regionsDict=dict()
		self.regionsAvg=dict()
		self.results=dict()
		self.scenario=None

	def setModelData(self,modList,dt):
		"""
		Подключаем исходные данные моделей
		"""
		scenariosList=list()
		for fn in modList:
			conn=c5c(fn,dt)
			self.models[conn.modelId]=clidat.metaData(meta={'dt':dt},dataConnection=conn)
			scenariosList.append(self.models[conn.modelId].meta['scenario'])
		if len(set(scenariosList))>1: raise StandardError, "different scenarios used in different files"
		if self.scenario is None: self.scenario=scenariosList[0]
		if scenariosList[0]!=self.scenario:
			raise StandardError, "scenario set as %s, you trying to load %s"%(self.scenario, scenariosList[0])
		self.results={mod:dict() for mod in self.models if mod not in self.results}
		pass

	def loadRegionMeanData(self,fn):
		cdo=cliData.load(fn)
		reg,mod=cdo.meta['region'], cdo.meta['model']
		if reg not in self.regionsAvg: self.regionsAvg[reg]=dict()
		try:
			self.regionsAvg[reg][mod]=cdo
		except KeyError:
			print 'cliData object should have "region" and "model" keys in the meta dictionary'
			raise
		else:
			self.models[mod]=None
			self.results[mod]=dict()
		pass

	def addRegion(self,shp,name):
		"""
		Добавляем в словарь узлы сетки попадающие в данный полигон для каждой модели
		"""
		self.regionsDict[name]={modName:modObj.setStInShape(shp) for modName,modObj in self.models.items()}
		self.regionsAvg[name]={modName:None for modName in self.models}

	def getRegionMean(self,region,model):
		"""
		Кэшируюшая ф-я получения среднерегионального ряда для какой-либо модели
		"""
		if self.regionsAvg[region][model] is None:
			dots=self.regionsDict[region][model]
			stList=[self.models[model][d] for d in dots]
			cso=clidat.metaData({'dt':self.dt}, stList=stList)
			cdo=cso.setRegAvgData()
			self.regionsAvg[region][model]=cdo
			r=cdo
		else:
			r=self.regionsAvg[region][model]
		return r

	def calcRegParam(self,task,region=None):
		"""
		расчитывает задание в формате {уникальное имя:{fn:имя функции, param:[параметры]}}
		для каждого среднерегионального каждой модели и сохраняет результат в self.results
		"""
		rList=[region] if region is not None else [r for r in self.regionsAvg]
		for modName, modObj in self.models.items():
			for reg in rList:
				res=self.regionsAvg[reg][modName].calcTask(task)
				if modName not in self.results: print self.results
				self.results[modName].update({reg:res})
		return self.results

	def printModRegFunctValTable(self,fname):
		"""
		Выводит таблицу значенией функции для каждого регионаб для каждой модели
		"""
		txt='\t' + '\t'.join([str(reg) for reg in self.regionsAvg]) + '\n'
		for mod in self.models:
			txt+=mod+'\t'.join([str(self.results[mod][reg][fname]) for reg in self.regionsAvg])+'\n'
		return txt
