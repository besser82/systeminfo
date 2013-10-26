import string

class TableTemplate:
        _template = ''
        _iteration = 0
        _maxInfo = {}

        def __init__(self, tableRows, tplstring):
                self.header = tableRows[0]
                self.tableData = tableRows
                self._template = tplstring
                for key, value in self.header.iteritems():
                        self._maxInfo[key] = [len(value)]
                        self._maxInfo[key+'Max'] = len(value)

                for cpunum, info in enumerate(self.tableData):
                        if len(info.keys()) > 0:
                                for key, value in self.header.iteritems():
                                    if key not in self.tableData[cpunum]:
                                        self.tableData[cpunum][key] = 'N/A'

                                    if self.tableData[cpunum][key] is None or self.tableData[cpunum][key] == '':
                                        self.tableData[cpunum][key] = 'N/A'

                                    if max(self._maxInfo[key]) < len(self.tableData[cpunum][key]):
                                        self._maxInfo[key+'Max'] = len(self.tableData[cpunum][key])

                                    self._maxInfo[key].append(len(str(self.tableData[cpunum][key])))
            
        def __str__(self):
                length = 0
                output = "\n"
                for i, v in enumerate(self.tableData):
                        if len(v.keys()) > 0:
                                output = output + self._template % self + "\n"
                                if self._iteration == 0:
                                        length = len(output)
                                        output = output + '=' * length + "\n"
                                self._iteration = self._iteration + 1

                output = '=' * length + output + '=' * length
                self._iteration = 0
                return output

        def __getitem__(self, key):
                el = key.split("|")
                if len(el) == 1:
                        return self.tableData[self._iteration][key]
                else:
                        return getattr(string, el[1])(self.tableData[self._iteration][el[0]], self._maxInfo[el[0]+'Max'])

            
            

