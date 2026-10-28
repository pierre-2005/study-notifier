"""Keep exported text from becoming a spreadsheet formula when opened."""
import csv,re
_NUMERIC=re.compile(r'^[+-]?\d+(?:\.\d+)?$')
def csv_cell(value):
    if isinstance(value,str) and not _NUMERIC.fullmatch(value):
        text=value.lstrip(' \t\r\n')
        if text.startswith(('=','+','-','@')):return "'"+value
    return value
class CsvWriter:
    def __init__(self,stream):self.writer=csv.writer(stream)
    def writerow(self,values):return self.writer.writerow([csv_cell(v) for v in values])
