"""Run: python test_folder.py"""
import io
import zipfile
import numpy as np
import pandas as pd
from folder_upload import split_folders,zip_folder,batch_sources
from batch_processing import batch_one_zip,batch_derived,batch_stats
from hall_core import compute_repeats,summarize_samples
class Uploaded:
    def __init__(self,name,content): self.name=name; self.content=content
    def getvalue(self): return self.content

items=[]
for folder,scale in [('1',1.0),('2',1.04),('2t',0.97),('10',1.1)]:
    for basename,ohms in [('i1-v23',14),('i2-v34',15),('i3-v41',14.1),('i4-v12',15.1),
                         ('i13-v24_Bpos',-.4),('i13-v24_Bneg',-.7),('i24-v13_Bpos',-.7),('i24-v13_Bneg',-.4),
                         ('i13-v24_offset',-.55),('i24-v13_offset',-.55)]:
        df=pd.DataFrame({'I1':[-1e-7,1e-7],'VDIFF':[-ohms*scale*1e-7, ohms*scale*1e-7]})
        items.append(Uploaded(f'Hall Measurements/{folder}/{basename}.csv',df.to_csv(index=False).encode()))
sources=batch_sources([],items,'폴더')
assert [x[0] for x in sources]==['Hall Measurements/1','Hall Measurements/2','Hall Measurements/2t','Hall Measurements/10']
raw=[]
for ix,(name,payload) in enumerate(sources,1):
    r,w=batch_one_zip(payload,name,'Sample_01',ix,1e-7,True)
    assert len(r)==10,(name,len(r),w)
    raw.append(r)
reps,problems=compute_repeats(pd.concat(raw,ignore_index=True),1.08,163)
assert len(reps)==4
reps=batch_derived(reps)
summary,_=summarize_samples(reps,163,1.08)
stats=batch_stats(reps)
assert len(stats)==5
assert summary.iloc[0]['N Rs']==4
assert summary.iloc[0]['N Hall']==4
assert np.isfinite(reps['mu_each_cm2_Vs']).all()
assert len(batch_sources([],items[:10],'폴더'))==1
# Same filename in different measurement folder must not overwrite
assert len(split_folders(items))==4
print('PASS: 4 uncompressed folders (1,2,2t,10), identical Excel-style file names, 40 files -> 4 repeats + 5 statistics')
