"""Run: python test_batch.py. Synthetic two-ZIP repeat test with scientific-current input."""
import io
import zipfile
import numpy as np
import pandas as pd
from batch_processing import batch_one_zip, batch_derived, batch_stats, summarize_batch_repeat_means
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
summary,_=summarize_batch_repeat_means(reps,163,1.08)
stats=batch_stats(reps)
assert len(reps)==3
assert len(stats)==5
assert int(summary.iloc[0]['N Rs'])==3
assert int(summary.iloc[0]['N Hall'])==3
assert np.isfinite(summary.iloc[0]['Hall mobility (cm²/V·s)'])
assert np.isfinite(reps['n_each_cm3']).all()
print('PASS: three independent ZIP files parsed as three repeats; five metrics and arithmetic statistics')


# Regression: signed RH changes sign once. The batch cards MUST show the
# arithmetic means of individual n and mobility, even though those differ
# from the values derived from mean signed RH.
import numpy as np
reps2 = reps.copy()
reps2.loc[reps2.index[-1], "RH_cm3_C"] *= -1
reps2 = batch_derived(reps2)
new_summary, _ = summarize_batch_repeat_means(reps2, 163, 1.08)
old_summary, _ = summarize_samples(reps2, 163, 1.08)
new_stats = batch_stats(reps2)
for prop, metric in [("Carrier concentration (cm⁻³)", "Carrier concentration"),
                     ("Hall mobility (cm²/V·s)", "Hall mobility")]:
    displayed = new_summary.iloc[0][prop]
    tabulated = new_stats.loc[new_stats["Metric"].eq(metric), "Mean (arithmetic repeat values)"].iloc[0]
    assert np.isclose(displayed, tabulated), (prop, displayed, tabulated)
    assert not np.isclose(displayed, old_summary.iloc[0][prop]), prop
assert np.isclose(new_summary.iloc[0]["RH mean (cm³/C)"], reps2["RH_cm3_C"].mean())
print("PASS: Batch cards match repeat-statistics arithmetic means, including sign-flip cases")
