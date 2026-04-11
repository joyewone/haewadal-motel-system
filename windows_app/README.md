# Windows 프로그램 실행 가이드 (Python 버전)

> Python 설치 없이 실행되는 버전이 필요하면 `windows_native_app` 폴더를 사용하세요.

`windows_app/motel_manager.py`는 Tkinter + SQLite 기반의 Python 데스크톱 객실관리 프로그램입니다.

## 실행 방법

```bash
python windows_app/motel_manager.py
```

실행 시 `windows_app/motel_manager.db`가 자동 생성되며 기본 객실(101~110, 201~210, 301~310)이 준비됩니다.

## 주요 기능

- 객실 30개 기본 생성
- 체크인 / 체크아웃
- 청소중 / 이용가능 상태 전환
- 오늘 매출 집계
