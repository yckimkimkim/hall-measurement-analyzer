# Hall Data Analyzer v1.5 — 개별 폴더 여러 개 업로드

## Batch 폴더 업로드

**상위(부모) 폴더는 필요 없습니다.** 예를 들어 파일 탐색기에 `1`, `2`, `2t`, `3`, ... `10` 폴더가 있다면 Streamlit의 Batch Analyzer에서 **개별 폴더** 모드를 선택하고 다음처럼 합니다.

1. `측정 폴더 1` 입력칸에서 `1` 폴더를 선택합니다.
2. `측정 폴더 2` 입력칸에서 `2` 폴더를 선택합니다.
3. `+ 폴더 추가` 버튼으로 필요한 만큼 칸을 늘리고 `2t`, `3`, ..., `10`을 순서대로 선택합니다.
4. 폴더들이 측정 목록에 뜨는지 확인한 뒤 `Batch 분석 실행`을 **한 번** 누릅니다.

각 폴더에는 이전과 같은 `i1-v23.xls`, `i2-v34.xls`, ..., `i24-v13_Bneg.xls` 등 10개 파일이 들어 있어도 됩니다. 파일명이 모든 폴더에서 같아도, 입력칸별로 분리되어 덮어쓰지 않습니다. 각 폴더가 독립적인 측정 1회이고, 그래프 가로축은 선택칸의 순서입니다. 폴더 하나를 선택할 때는 폴더 안 Excel 파일만 선택하는 것이 아니라 **폴더 자체**를 선택합니다.

**브라우저 제약:** 일반 파일 탐색기의 폴더 선택창에서 서로 다른 폴더 10개를 한 번의 선택 조작으로 동시에 선택하는 것은 보장되지 않습니다. 이 버전에서는 여러 선택칸으로 폴더를 추가한 후, **10개 결과를 한 번에 분석**합니다. 폴더들을 통째로 드래그해 한 번에 선택하는 전용 웹 드롭존은 포함되어 있지 않습니다.

Single Analyzer는 폴더 1개 또는 ZIP 1개를 지원하고, Batch Analyzer는 여러 개별 폴더 또는 여러 ZIP 파일을 지원합니다.

## 설치/배포

```bash
pip install -r requirements.txt
streamlit run app.py
```

GitHub 저장소에 `app.py`, `folder_upload.py`, 기타 Python 모듈, `requirements.txt`를 모두 올려야 합니다. Streamlit 1.55 이상을 사용합니다.

## 계산 참고

- 각 반복 폴더에 대해 Hall coefficient, Van der Pauw 면저항, 비저항, 캐리어 농도, Hall mobility를 계산합니다.
- Batch에서는 측정별 값과 평균 및 5개 그래프를 제공합니다.
- Test Current는 A 단위이며 `1e-7` / `1E-7` 입력을 지원합니다. 현재 계산 엔진은 목표 전류의 ±20% 허용 규칙을 유지합니다.
- Thickness는 비어 있는 상태에서 시작하며 분석 전에 직접 입력해야 합니다.


## v1.6
Batch `Per-measurement results CSV` now includes `Thickness_nm` (the film thickness entered for the batch). The repeat-level results table also displays the same column. No electrical calculations were changed.
