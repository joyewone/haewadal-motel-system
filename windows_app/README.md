# Windows 프로그램 실행 가이드

`windows_app/motel_manager.py`는 Tkinter + SQLite 기반의 Windows 데스크톱 객실관리 프로그램입니다.

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

## Windows 배포(단일 exe)

PyInstaller가 있다면 다음 명령으로 exe 생성 가능합니다.

```bash
pyinstaller --onefile --windowed --name HaewadalMotel windows_app/motel_manager.py
```

생성 파일: `dist/HaewadalMotel.exe`
