from io import BytesIO
from pathlib import Path
from zipfile import ZipFile
from folder_upload import individual_folder_sources

class Upload:
    def __init__(self, name, data):
        self.name=name
        self.data=data
    def getvalue(self): return self.data

def group(n):
    return [Upload(f'{n}/{filename}', f'{n}-{filename}'.encode()) for filename in ['i1-v23.xls','i2-v34.xls','i3-v41.xls','i4-v12.xls','i13-v24_Bpos.xls','i13-v24_Bneg.xls','i13-v24_offset.xls','i24-v13_Bpos.xls','i24-v13_Bneg.xls','i24-v13_offset.xls']]

slots=[(j,group(str(j))) for j in range(1,11)]
sources=individual_folder_sources(slots)
assert len(sources)==10
for idx,(name,payload) in enumerate(sources,1):
    assert name.endswith(str(idx))
    with ZipFile(BytesIO(payload)) as z:
        assert len(z.namelist())==10
        assert z.read('i1-v23.xls')==f'{idx}-i1-v23.xls'.encode()
assert len(individual_folder_sources([(1,group('2t')),(2,group('2t'))]))==2
try:
    individual_folder_sources([(1,group('1')+group('2'))])
    raise AssertionError('mixed directories must fail')
except ValueError:
    pass
print('individual folder tests passed')
