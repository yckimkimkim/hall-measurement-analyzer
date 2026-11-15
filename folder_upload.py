"""Upload helpers: preserve measurement-folder identity with repeated Excel filenames."""
from __future__ import annotations
from collections import OrderedDict
from pathlib import PurePosixPath
from io import BytesIO
import zipfile

ALLOWED={".xls", ".xlsx", ".csv", ".txt"}
MAX_FILES=10000
MAX_BYTES=500*1024*1024


def split_folders(uploaded_files):
    """Return ordered folder -> file objects mapping from Streamlit directory uploads.

    Streamlit UploadedFile.name for directory mode contains a relative path,
    including the selected directory. The IMMEDIATE parent is the measurement
    folder (e.g. 'Hall/2t/i1-v23.xls' -> '2t'). All equal filenames remain distinct.
    """
    groups=OrderedDict()
    total=0
    if len(uploaded_files)>MAX_FILES:
        raise ValueError('최대 업로드 파일 수(10,000)를 초과했습니다.')
    for obj in uploaded_files:
        path=str(obj.name).replace('\\','/')
        parts=PurePosixPath(path).parts
        if '..' in parts or len(parts)<2:
            raise ValueError(f'폴더 경로가 포함되지 않은 파일: {path}. 폴더 업로드를 사용해 주세요.')
        if PurePosixPath(path).suffix.lower() not in ALLOWED:
            continue
        total += len(obj.getvalue())
        if total>MAX_BYTES:
            raise ValueError('업로드된 데이터가 500 MB 한도를 초과했습니다.')
        parent='/'.join(parts[:-1])
        groups.setdefault(parent,[]).append(obj)
    return groups


def zip_folder(files):
    """Create an in-memory ZIP per folder; no user-side compression necessary."""
    out=BytesIO()
    seen=set()
    with zipfile.ZipFile(out,'w',compression=zipfile.ZIP_DEFLATED) as z:
        for obj in files:
            name=PurePosixPath(str(obj.name).replace('\\','/')).name
            if name in seen:
                raise ValueError(f'같은 폴더에 중복 파일명이 있습니다: {name}')
            seen.add(name)
            z.writestr(name,obj.getvalue())
    return out.getvalue()


def batch_sources(zips, folders, mode):
    """Return [(name, bytes)] for either ZIP archives or measurement folders."""
    if mode=='ZIP':
        return [(f.name,f.getvalue()) for f in zips]
    grouped=split_folders(folders)
    return [(name,zip_folder(group)) for name,group in grouped.items()]
