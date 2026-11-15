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


def individual_folder_sources(slots):
    """Collect one measurement directory per independent uploader slot.

    slots: iterable of (slot_number, list[UploadedFile]); repeated Excel basenames
    across slots are intentionally permitted, and a parent folder is not needed.
    """
    sources=[]
    for slot_number, uploaded in slots:
        if not uploaded:
            continue
        grouped=split_folders(uploaded)
        if len(grouped)!=1:
            raise ValueError(
                f"폴더 선택칸 {slot_number}: 한 번에 측정 폴더 하나만 선택해 주세요. "
                f"현재 {len(grouped)}개의 하위 폴더가 감지됐습니다."
            )
        folder, files=next(iter(grouped.items()))
        folder_name=PurePosixPath(folder).name
        sources.append((f"{slot_number:02d} · {folder_name}", zip_folder(files)))
    if len(sources)>100:
        raise ValueError("한 번에 최대 100개의 측정 폴더를 처리할 수 있습니다.")
    return sources
