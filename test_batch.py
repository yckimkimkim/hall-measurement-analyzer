"""Run: python test_batch.py. Synthetic two-ZIP repeat test with scientific-current input."""
import io
import zipfile
import numpy as np
import pandas as pd
from batch_processing import batch_one_zip, batch_derived, batch_stats
from hall_core import compute_repeats, summarize_samples


def make_zip(scale=1.0):
    names = {'i1-v23':14, 'i2-v34':15, 'i3-v41':14.1, 'i4-v12':15.1,
             'i13-v24_Bpos':-.4, 'i13-v24_Bneg':-.7,
             'i24-v13_Bpos':-.7, 'i24-v13_Bneg':-.4,
             'i13-v24_offset':-.55, 'i24-v13_offset':-.55}
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w') as z:
        for kind, r in names.items():
            df = pd.DataFrame({'I1':[-1e-7,1e-7], 'VDIFF':[-r*scale*1e-7,r*scale*1e-7]})
            z.writestr('samplefolder/'+kind+'.csv',df.to_csv(index=False))
    return buf.getvalue()

raws=[]
for idx in (1,2,3):
    raw, warnings = batch_one_zip(make_zip(1 + 0.05*idx),f'test-{idx}.zip','Sample_01',idx,1e-7,True)
    assert not warnings, warnings
    assert len(raw)==10
    raws.append(raw)
raw=pd.concat(raws,ignore_index=True)
reps,issues=compute_repeats(raw,1.08,163)
reps['Order']=[1,2,3]
reps=batch_derived(reps)
summary,_=summarize_samples(reps,163,1.08)
stats=batch_stats(reps)
assert len(reps)==3
assert len(stats)==5
assert int(summary.iloc[0]['N Rs'])==3
assert int(summary.iloc[0]['N Hall'])==3
assert np.isfinite(summary.iloc[0]['Hall mobility (cm²/V·s)'])
assert np.isfinite(reps['n_each_cm3']).all()
print('PASS: three independent ZIP files parsed as three repeats; five metrics and arithmetic statistics')
