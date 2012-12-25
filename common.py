# coding=utf-8
"""
Общие функции и классы, имеющие чисто техническое значение
Основа - класс config определяющий глобальные настройки
"""
__author__ = 'Vasily Kokorev'
__email__ = 'vasilykokorev@gmail.com'

class config:
    """
    класс config определяет все глобальные настройки 
    такие как логин пароль подключения к базе, используемые шрифты и т.д.
    также загружет необходимые библиотеки.
    Свойства:
        host - адрес для подключения к БД
        user    - имя пользователя для подключения к БД
        pasw    - пароль для подключения к БД (Храниться в открытом виде в ini файле!)
        db        - имя используемой базы данных
        meta    - имя таблицы с метаинформацией
        mtemp    - имя таблицы с месячными значениями температуры
        font    - имя файла используемого шрифта (без расширения!)
    """
    def __init__(self, filename="cfg.ini"):
        import os
        import dummy
        self.src = os.path.split(dummy.__file__)[0]
        self.readini(filename)
        self.setLogs(self.logFileName)
        self.makePythonRusFriendly()
#        self.c=self.connect()
        self.setElList()
        global cfg
        cfg = self
        self.yMin, self.yMax = -1, -1
        self.elSynom = self.getElementsSynom()

        
    def __str__(self):
        # TODO: функция сохранения cfg как ini
        pass


    def setElList(self, fl='dbstructure.ini'):
        import ConfigParser
        self.dtList = []
        ini = ConfigParser.ConfigParser()
        ini.read(self.src + "\\resources\\" + fl)
        elLst = ini.get("elements", "elementsList").split(',')
        self.dtList = elLst



    def readini(self, inifilename):
        """ читает настройки из конфигурационного файла """
        import ConfigParser
        ini = ConfigParser.ConfigParser()
        ini.read(self.src + "\\resources\\" + inifilename)
        self.font = ini.get("font", "standart")
        self.logFileName = ini.get("logs", "logfile")



    def makePythonRusFriendly(self):
        """ делает настройки для поддержки русских шрифтов """
        import matplotlib.pyplot as plt, matplotlib.font_manager as fm
        global fp1
        plt.rcParams["text.usetex"] = False
        fp1 = fm.FontProperties(fname=self.src + '//resources//' + self.font + ".ttf")
        self.fp1 = fp1


    @staticmethod
    def setLogs(logFileName):
        """ Заготовка функции. открывает Log файл на перезапись """
        global logFile
        try:
            if type(logFile) != file:
                pass
        except NameError:
            pass
        finally:
            logFile = open(logFileName, 'w+')



    def logThis(self, messg):
        """
        Записывает сообщение messg и время в log файл.
        """
        import time
        if type(logFile) != file:
            config.setLogs('logfile.txt')
        timeStemp = time.strftime("%d.%m.%Y %H:%M:%S", time.localtime())
        logFile.write(timeStemp + "\t- " + messg + "\r")


    def setSeasons(self, usrFmtSeas={"year": range(1, 13)}):
        """ ф-я проверяет правильность формата в котором были заданы сезоны """
        self.sortedSeasons = []
        for key in usrFmtSeas:
            try:
                if len(usrFmtSeas[key]) == 0:
                    usrFmtSeas.pop(key)
                    self.logThis("Сезон " + key + " задан неверно и удалён из списка сезонов")
                #usrFmtSeas[key]=[i-1 for i in usrFmtSeas[key]]
            except TypeError:
                usrFmtSeas.pop(key)
                self.logThis("Сезон " + key + " задан неверно и удалён из списка сезонов")
        if len(usrFmtSeas) == 0:
            self.logThis("массив сезонов был задан неверно, выполнение программы прервано")
            raise ValueError("Некорректно задан формат сезонов")
        else:
            seasStr = ""
            for key in usrFmtSeas:
                seasStr += str(key) + ": " + str(usrFmtSeas[key]) + ", "
                self.sortedSeasons.append(key)
            self.logThis("Заданы сезоны " + seasStr)
            self.seasons = usrFmtSeas
        return self.seasons


    def getElementsSynom(self, dbfile='dbstructure.ini'):
        import ConfigParser
        ini = ConfigParser.ConfigParser()
        ini.read(self.src + "\\resources\\" + dbfile)
        elLst = ini.get("elements", "elementsList").split(',')
        synDict = dict()
        for el in elLst:
            synLst = ini.get("elements", el + "Synonyms").split(',')
            for syn in synLst:
                synDict.update({syn:el})
        return synDict

    def elSynom(self, dt):
        dct = self.getElementsSynom
        return dct[dt]


    def endprog(self):
        """
        Записывает время окончания программы и закрывает лог файл
        В будущем будет делать ещё что-то. Наверное...
        """
        self.logThis("program exec ended")
        logFile.close()


def getSaveResId(method, *args, **kwargs):
    """
    функция принимает метод и его аргументы, а возвращает индификатор под которым
    результаты расчёта этого метода с этими параметрами были записаны в словарь
    Ключ слваря составляетьс по форме "имя функции--список значений аргументов через запятую"
    """
    dId = method.__name__ + '--'
    for s in args: dId += str(s) + ','
    for s in kwargs: dId += str(s) + ','
    return dId[0:-1]