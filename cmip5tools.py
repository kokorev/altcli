# coding=utf-8
"""
Инструменты для работы с наборами моделей CMIP5
"""
import clidataSet as clidat
from dataConnections import cmip5connection as c5c

class modelSet():
	"""
	Класс набора моделей, реалезующий ф-ии сравнения моделей и построения ансамблей
	"""
	def __init__(self,modList,dt):
		self.models=dict()
		self.dt={'dt':dt}
		for fn in modList:
			conn=c5c(fn,dt)
			self.models[conn.modelId]=clidat.metaData(meta={'dt':dt},dataConnection=conn)
		self.regionsDict=dict()
		self.regionsAvg=dict()
		self.results={mod:dict() for mod in self.models}


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
				self.results[modName].update({reg:res})
		return None


	def printModRegFunctValTable(self,fname):
		"""
		Выводит таблицу значенией функции для каждого регионаб для каждой модели
		"""
		txt='\t' + '\t'.join([str(reg) for reg in self.regionsAvg]) + '\n'
		for mod in self.models:
			txt+=mod+'\t'.join([str(self.results[mod][reg][fname]) for reg in self.regionsAvg])+'\n'
		return txt







