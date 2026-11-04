"""Quick tests: python test_core.py"""
import io
import zipfile
import numpy as np
import pandas as pd
from hall_core import read_zip, compute_repeats, summarize_samples, van_der_pauw


def f(kind, rp, rn, rep="Repeat_001", sample="A"):
    df=pd.DataFrame({"I1":[-0.001,0.001],"VDIFF":[-rn*0.001,rp*0.001]})
    return f"{sample}/{rep}/{kind}.csv",df.to_csv(index=False).encode()

assert np.isclose(van_der_pauw(100,100),np.pi*100/np.log(2))
entries=[]
for sample,scale in [("A",1),("B",2)]:
  for rep in ["Repeat_001","Repeat_002","Repeat_003"]:
    if rep=="Repeat_001":
      entries += [f("i1-v23",100*scale,100*scale,rep,sample),f("i2-v34",100*scale,100*scale,rep,sample)]
    entries += [f("i13-v24_Bpos",.1*scale,.1*scale,rep,sample),f("i13-v24_Bneg",-.1*scale,-.1*scale,rep,sample)]
    entries += [f("i24-v13_Bpos",-.1*scale,-.1*scale,rep,sample),f("i24-v13_Bneg",.1*scale,.1*scale,rep,sample)]
with io.BytesIO() as data:
  with zipfile.ZipFile(data,"w") as z:
    for name,b in entries:z.writestr(name,b)
  raw,w=read_zip(data.getvalue(),1,True)
assert len(raw)==28 and not w,(len(raw),w)
rep,_=compute_repeats(raw,1.08,15,"i1-v23","i2-v34")
summ,det=summarize_samples(rep,15,1.08)
assert len(summ)==2 and list(summ["N Hall"])==[3,3] and list(summ["N Rs"])==[1,1]
assert np.all(np.isfinite(summ["Hall mobility (cm²/V·s)"]))
print('PASS: 2 samples, 3 repeats each, Rs sparse repeats, independent sample means')
