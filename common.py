"""
Общие функции и классы, имеющие чисто техническое значение
Основа - класс config определяющий глобальные настройки
"""
__author__ = 'Vasily Kokorev'
__email__ = 'vasilykokorev@gmail.com'
__version__ = '1.0'

class getDataMysql():
    """
    Класс чтнеия данных из базы. По индексу и году возвращает массив данных
    для создания экземпляра cliData/yearData
    """
    
    def __init__(self, cfg, inifilename="mysqlcfg.ini"):
        self.cfg = cfg
        self.readini(inifilename)
        self.c = self.connect()
        self.cd = self.connectDict()

        
    def getYear(self, ind, year, dt):
        """
        читаем из базы данные по одному году.
        """
        assert type(dt) is str, "dataType - Должен быть строкой. %s" % dt
        time = [i for i in range(1, 13)]
        vals = [None for i in range(1, 13)]
        status = True
        dt = self.cfg.elSynom[dt]
        table = self.data
        q = "SELECT MONTH(date),%s FROM `%s` WHERE ind=%i and YEAR(date) = '%4i'" % (dt, table, ind, year)
        try:
            qRetNum = self.c.execute(q)
            if qRetNum == 0: status = False # если база вернула ноль строк значит такой станции нету
        except Exception:
            print q
            raise
        for qr in self.c.fetchall():
            if qr[1] != None:
                vals[qr[0] - 1] = qr[1]
                data = [self.time, self.vals]
        return [vals, data], status
    
    def getMonth(self, ind, year, month, dt):
        dt = self.cfg.elSynom[dt]
        table = self.data
        q = "SELECT MONTH(date),%s FROM `%s` WHERE ind=%i and YEAR(date) = '%4i' and MONTH(date)='%i'" % (dt, table, ind, year, month)
        try:
            qRetNum = self.c.execute(q)
        except Exception:
            print q
            raise
        else:
            r = self.c.fetchall()
            if qRetNum == 0:
                res = None
            else:
                res = r[0][0]
        return res
    
    
    def getInd(self, ind, dt, yMin= -1, yMax= -1):
        """
        Принимает:
            cfgObj - указатель на экземпляр config
            stNum - номер станции
            usyMin=0,usyMax=0 - Начальный и конечный год за который необходимо считать данные. Если значение равно нулю то присваиваеться максимальное или минимальное значение соответсвенно
        """
        assert type(yMin) is int and type(yMax) is int , "начальный и конечный года должны быть целыми числами"
        assert type(dt) is str, "dataType - Должен быть строкой"
        ##assert type(stNum) is int , "номер станции должен быть целым числом"
        ##assert type(cfgObj) is instance , "глобальные настройки должны быть переданы в виде экземпляра класса config"
        dt = self.cfg.elSynom[dt]
        self.minInd = 0
        if yMin == -1 or yMax == -1:
            q = 'SELECT YEAR(MIN(DATE)),YEAR(MAX(DATE)) FROM `%s` WHERE ind=%i AND %s IS NOT NULL' % (self.data, ind, dt)
            self.c.execute(q)
            qres = self.c.fetchall()
            dbMinY, dbMaxY = qres[0][0], qres[0][1]
            if yMin == -1: yMin = dbMinY
            if yMax == -1: yMax = dbMaxY
        res = []
        try:
            assert yMin != None , "для станции " + str(ind) + " отсутствуют данные"
        except AssertionError:
            raise LookupError
        else:
            ##==    реализация быстрого алгоритма чтения    ==##
            query = "SELECT YEAR(date),MONTH(date),%s FROM `%s` WHERE ind=%i and YEAR(DATE)>=%i and YEAR(DATE)<=%i" % (dt, self.data, ind, yMin, yMax)
            qRetNum = self.c.execute(query)
            if qRetNum == 0: raise LookupError
            for qr in self.c.fetchall():
                try:
                    thisY = res[-1][0]
                except IndexError:    # если список пуст добавляем строку
                    res.append([int(qr[0]), [None for i in range(1, 13)]])
                    thisY = res[-1][0]
                else: # если год закончился добавляем ещё строку, меняем значение текущего года
                    if thisY != qr[0]:
                        thisY = qr[0]
                        res.append([int(qr[0]), [None for i in range(1, 13)]])
                finally:    # выставляем значение данного месяца
                    if qr[2] != None:
                        res[-1][1][qr[1] - 1] = qr[2]
                ##self.data=res
        return res
    
    def getMeta(self, dt, ind):
        r = dict()
        dt=cfg.elSynom[dt]
        q = 'SELECT YEAR(MIN(DATE)),YEAR(MAX(DATE)) FROM `%s` WHERE ind=%i AND %s IS NOT NULL' % (self.data, ind, dt)
        self.c.execute(q)
        qres = self.c.fetchall()
        r['existMinY'], r['existMaxY'] = qres[0][0], qres[0][1]
        q = "SELECT * FROM `%s` WHERE ind=%i" % (self.meta, ind)
        self.cd.execute(q)
        qres = self.cd.fetchone()
        if qres!=None:
            r.update(qres)
        else:
            r=None
        return r
    
    def getAllMeta(self):
        q = "SELECT * FROM `%s`" % (self.meta)
        self.cd.execute(q)
        qres = self.cd.fetchall()
        return qres
        
    
    def get(self, dt, ind, year= -1, month= -1, yMin= -1, yMax= -1):
        if year == -1 and month == -1:
            r = self.getInd(ind, dt, yMin, yMax)
        elif month == -1:
            r = self.getYear(ind, year, dt)
        else:
            r = self.getMonth(ind, year, month, dt)
        return r
    
    def readini(self, inifilename="mysqlcfg.ini"):
        """ читает настройки из конфигурационного файла """
        import ConfigParser
        ini = ConfigParser.ConfigParser()
        ini.read(self.cfg.src + "\\resources\\" + inifilename)
        self.host = ini.get("mysql", "host")
        self.user = ini.get("mysql", "user")
        self.pasw = ini.get("mysql", "password")
        self.db = ini.get("mysql", "database")
        self.meta = ini.get("tables", "metaTable")
        self.data = ini.get("tables", "mTempTable")
        
    def connect(self):
        """ возвращает указатель на подключение к бд """
        import MySQLdb
        try:
            c = MySQLdb.connect(self.host, self.user, self.pasw, self.db).cursor()
        except:
            import subprocess
##            print 'starting'
            pipe = subprocess.Popen(self.cfg.src + '\\startMySQL.bat', stdout=subprocess.PIPE)
            c = MySQLdb.connect(self.host, self.user, self.pasw, self.db).cursor()
        return c
    
    def connectDict(self):
        import MySQLdb
        try:
            c = MySQLdb.connect(self.host, self.user, self.pasw, self.db).cursor(cursorclass=MySQLdb.cursors.DictCursor)
        except:
            import subprocess
##            print 'starting'
            pipe = subprocess.Popen(self.cfg.src + '\\startMySQL.bat', stdout=subprocess.PIPE)
            c = MySQLdb.connect(self.host, self.user, self.pasw, self.db).cursor(cursorclass=MySQLdb.cursors.DictCursor)
        return c

    


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
#        try:
#            self.di = getDataMysql(self)
#            self.get = self.di.get
#            self.getMeta = self.di.getMeta 
#        except:
#            pass

        
        
    def __str__(self):
        # TODO: функция сохранения cfg как ini
        pass
    
    
    def enableMySql(self):
        self.di = getDataMysql(self)
        self.get = self.di.get
        self.getMeta = self.di.getMeta


    def connect(self):
        """ возвращает указатель на подключение к бд """
        import MySQLdb
        try:
            c = MySQLdb.connect(self.host, self.user, self.pasw, self.db).cursor()
        except:
            import subprocess
##            print 'starting'
            pipe = subprocess.Popen(self.src + '\\startMySQL.bat', stdout=subprocess.PIPE)
            c = MySQLdb.connect(self.host, self.user, self.pasw, self.db).cursor()
        return c


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


config()





    
    
    
    
