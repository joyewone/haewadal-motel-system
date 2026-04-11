# Windows 네이티브(.exe) 실행 버전

이 폴더는 **Python 설치 없이 실행 가능한 Windows 프로그램**(WinForms + SQLite) 소스입니다.

## 1) 빌드 환경

- Windows 10/11
- [.NET SDK 8.0 이상](https://dotnet.microsoft.com/download)

## 2) 실행 파일(.exe) 만들기 (Self-contained)

PowerShell 또는 CMD에서:

```bash
cd windows_native_app
dotnet restore
dotnet publish -c Release -r win-x64 --self-contained true /p:PublishSingleFile=true
```

완성된 exe 경로:

```text
windows_native_app/bin/Release/net8.0-windows/win-x64/publish/HaewadalMotel.exe
```

위 exe는 대상 PC에 Python이 없어도 실행됩니다.

## 3) 개발 실행

```bash
cd windows_native_app
dotnet run
```

## 4) 기능

- 객실 30개 자동 생성
- 체크인/체크아웃
- 청소중/이용가능 상태 변경
- 일 매출 집계
- SQLite 로컬 DB(`motel_native.db`) 자동 생성
