# Telegram Mirror Bot

Complete channel mirroring bot with copy restriction bypass capabilities.

## Features

- ✅ **Complete Mirroring**: Text, media, edits, deletes, albums
- 🔓 **Copy Restriction Bypass**: Download and re-upload protected content
- ⚡ **High Performance**: Task queue, batch processing, flood wait handling
- 🎯 **Smart Strategies**: Auto-selects optimal mirroring method
- 📊 **Statistics**: Track messages, media, errors

## Installation

### 1. Get Telegram API Credentials
1. Visit https://my.telegram.org
2. Log in with your phone number
3. Go to "API development tools"
4. Create an application
5. Copy your `API_ID` and `API_HASH`

### 2. Setup Environment
```bash
# Clone repository
git clone https://github.com/yourusername/crowbot.git
cd crowbot

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env and add your API_ID and API_HASH
```

### 3. Run the Bot
```bash
# Test installation
python test_bot.py

# Start bot
python run_bot.py
```

## Usage

### Bot Commands
- `.설정` - Open configuration menu
- `.동기화` - Sync channel history

### Configuration Menu
1. **Session Management**: Set/update session string
2. **Channel Mappings**: Add source → target channels
3. **Mirror Options**: Toggle text/media/edits/deletes
4. **Statistics**: View mirroring stats
5. **Channel Sync**: Sync historical messages

## Project Structure

```
crowbot/
├── bot/
│   ├── main.py          # Main bot entry point
│   ├── config.py        # Configuration management
│   ├── mirror.py        # Core mirroring engine
│   ├── simple_menu.py   # Menu interface
│   └── session_handler.py # Session management
├── data/
│   ├── bot.log          # Application logs
│   └── settings.json    # Persistent settings
├── .env                 # API credentials
├── run_bot.py          # Bot launcher
└── test_bot.py         # System check tool
```

## Requirements

- Python 3.8+
- Telegram API credentials
- Session string (generated through bot menu)

## License

MIT License

<!-- 
Project: Telegram Mirror Bot
Version: 1.0.0
License: MIT
Author: CrowBot Team
Last Updated: 2025-08-10
-->

# Telegram Mirror Bot 🤖 (User Bot)

완벽한 텔레그램 미러링 봇 - 복사/전달 제한 우회 기능 포함

✅ **사용 방법**: 이제 모든 사용자가 명령어를 사용할 수 있습니다!
- **누구나** 봇에게 명령어를 입력할 수 있습니다
- 1:1 대화, 그룹, 채널 모두에서 작동합니다
- `.설정` 또는 `.동기화` 명령어를 입력하면 봇이 응답합니다

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

### 3. 환경 설정
```bash
# .env 파일 생성
cp .env.example .env

# .env 파일 편집하여 API 정보 입력
API_ID=your_api_id_here
API_HASH=your_api_hash_here
SESSION_STRING=  # 선택사항 - 메뉴에서도 설정 가능
LOG_CHANNEL_ID=  # 선택사항 - 로그 채널 ID
```

### 4. 실행
```bash
python bot/main.py
```

## 명령어 가이드 📝

### 🟢 사용 방법

**모든 사용자가 사용 가능:**
1. **아무 채팅방**에서 봇과 대화
2. **누구나** `.설정` 또는 `.동기화` 명령어 입력 가능
3. 봇이 메뉴를 응답하면 숫자로 선택

### 새로운 간단한 메뉴 시스템

#### 기본 명령어
```bash
.설정      # 설정 메뉴 열기
.동기화    # 채널 전체 동기화
```

#### 메뉴 구조
```
1. 📊 상태 - 전체 설정 및 상태 보기
2. 📥 입력설정 - 소스 채널 설정
3. 📤 출력설정 - 타겟 채널 설정
4. 📝 로그설정 - 로그 채널 설정

0. 종료
```

#### 사용 예시
1. `.설정` 입력
2. 번호로 메뉴 선택
3. `0`으로 뒤로가기/종료

### 채널 동기화
```bash
.동기화
# 채널 ID 또는 @username 입력
# 모든 메시지를 타겟 채널로 복사
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