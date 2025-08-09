# Telegram Mirror Bot 🤖

완벽한 텔레그램 미러링 봇 - 복사/전달 제한 우회 기능 포함

## 주요 기능 ✨

- ✅ **완전한 미러링**: 텍스트, 미디어, 편집, 삭제 모두 동기화
- 🔓 **복사 제한 우회**: 제한된 채널의 콘텐츠도 미러링 가능
- 🎯 **CLI 스타일 명령어**: 직관적인 명령어 체계
- 🔄 **실시간 동기화**: 모든 변경사항 즉시 반영
- 📊 **통계 및 모니터링**: 미러링 상태 실시간 확인
- 🚀 **VPS 배포 지원**: 24/7 운영 가능

## 설치 방법 📦

### 1. 요구사항
- Python 3.10 이상
- Telegram API 키 (https://my.telegram.org 에서 발급)

### 2. 설치
```bash
# 저장소 클론
git clone https://github.com/yourusername/crowbot.git
cd crowbot

# 가상환경 생성
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 의존성 설치
pip install -r requirements.txt
```

### 3. 설정
```bash
# 설정 파일 복사
cp data/settings.json.example data/settings.json

# settings.json 편집하여 API 정보 입력
{
  "api_id": YOUR_API_ID,
  "api_hash": "YOUR_API_HASH",
  ...
}
```

### 4. 실행
```bash
python bot/main.py
```

## 명령어 가이드 📝

### 기본 명령어
```bash
.설정                    # 도움말 표시
.설정 help              # 전체 도움말
.설정 help [command]    # 특정 명령어 도움말
```

### 채널 매핑 관리
```bash
.설정 map list                      # 매핑 목록 보기
.설정 map add [소스ID] [타겟ID]      # 매핑 추가
.설정 map del [인덱스/소스ID]        # 매핑 삭제
.설정 map clear                     # 모든 매핑 삭제

# 단축 명령어
.설정 ls                            # = map list
.설정 add [소스] [타겟]              # = map add
.설정 rm [인덱스]                   # = map del
```

### 세션 관리
```bash
.설정 session set          # 세션 문자열 설정
.설정 session info         # 세션 정보 확인
.설정 session test         # 세션 유효성 검사
.설정 session clear        # 세션 삭제
```

### 봇 제어
```bash
.설정 bot start            # 미러링 시작
.설정 bot stop             # 미러링 중지
.설정 bot restart          # 봇 재시작
.설정 bot status           # 상태 확인

# 단축 명령어
.설정 st                   # = bot status
```

### 통계 및 설정
```bash
.설정 stats                # 통계 보기
.설정 stats reset          # 통계 초기화
.설정 config show          # 설정 보기
.설정 config option [name] [on/off]  # 옵션 설정
```

## 세션 문자열 생성 방법 🔑

### 방법 1: Python 스크립트
```python
from telethon.sync import TelegramClient
from telethon.sessions import StringSession

api_id = YOUR_API_ID
api_hash = 'YOUR_API_HASH'

with TelegramClient(StringSession(), api_id, api_hash) as client:
    print("Session String:", client.session.save())
```

### 방법 2: 온라인 생성기
- https://replit.com/@bipinkrish/Telethon-String-Session

## VPS 배포 🚀

### 자동 배포 스크립트
```bash
# VPS에 업로드 후
chmod +x deploy.sh
./deploy.sh
```

### Systemd 서비스
```bash
# 시작
sudo systemctl start crowbot

# 자동 시작 설정
sudo systemctl enable crowbot

# 상태 확인
sudo systemctl status crowbot

# 로그 확인
sudo journalctl -u crowbot -f
```

### Screen 세션
```bash
# Screen으로 실행
./start_screen.sh

# 세션 연결
screen -r crowbot

# 세션 분리
Ctrl+A, D
```

## 설정 옵션 ⚙️

| 옵션 | 설명 | 기본값 |
|------|------|--------|
| `mirror_enabled` | 미러링 활성화 | `true` |
| `mirror_text` | 텍스트 미러링 | `true` |
| `mirror_media` | 미디어 미러링 | `true` |
| `mirror_edits` | 편집 미러링 | `true` |
| `mirror_deletes` | 삭제 미러링 | `true` |
| `bypass_restriction` | 복사 제한 우회 | `true` |

## 주의사항 ⚠️

- 세션 문자열은 계정 전체 권한을 가지므로 안전하게 보관
- API 제한(flood wait)을 피하기 위해 적절한 딜레이 설정
- 대용량 미디어 파일은 VPS 저장공간 고려
- 개인정보 및 저작권 관련 법규 준수

## 문제 해결 🔧

### 세션 만료
```bash
.설정 session clear
.설정 session set
# 새 세션 문자열 입력
```

### Flood Wait 에러
- 요청 간격 조정
- 동시 미러링 채널 수 제한

### 메모리 부족
- 미디어 캐시 비활성화
- 로그 파일 정기 정리

## 라이선스 📄

MIT License

## 기여 🤝

PR과 이슈 제보를 환영합니다!

---

Made with ❤️ using Telethon