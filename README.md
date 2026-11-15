# Hall Data Analyzer v1.4

## 업로드

**폴더 업로드 (기본값):** Single에서는 측정 폴더 하나를, Batch에서는 그 상위 폴더를 선택합니다.

```text
Hall Measurements/
├── 1/
│   ├── i1-v23.xls
│   ├── i2-v34.xls
│   └── ... (10 files)
├── 2/
│   └── ... (10 files)
├── 2t/
│   └── ... (10 files)
└── 10/
    └── ... (10 files)
```

각 하위 폴더는 측정 1회입니다. 같은 파일명이 반복되어도 폴더별로 분리됩니다. `2t`도 별도의 측정으로 인식합니다. 폴더를 하나씩 추가로 선택하는 것도 가능합니다.

**ZIP 업로드:** 선택 메뉴에서 ZIP을 선택하면 기존 방식도 계속 사용할 수 있습니다.

폴더 업로드는 Streamlit `accept_multiple_files="directory"`를 사용하며 Streamlit 1.55 이상이 필요합니다. `UploadedFile.name`에 보존된 폴더 경로를 기준으로 묶습니다. 별도 폴더 없이 Excel 파일만 선택하는 방식은 지원하지 않습니다.

## 실행

```bash
pip install -r requirements.txt
streamlit run app.py
```

## 주의

- 폴더/ZIP의 전류값은 기존 분석 엔진과 동일하게 Test Current의 ±20% 이내 값만 반영합니다.
- 같은 시편이면 Sample 열을 같게 두고, 서로 다른 시편이면 구분하세요.
- 두께는 반드시 입력합니다. Test Current는 A 단위로 `1e-7` 또는 `1E-7` 입력 가능합니다.
- 분석 데이터 파일을 GitHub에 올릴 필요는 없습니다. 브라우저에서 로컬 폴더를 선택하세요.
