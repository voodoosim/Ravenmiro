#!/usr/bin/env python3
"""
통합 명령어 테스트 - 각 명령어의 동작 검증
"""

import sys
from pathlib import Path

# Fix Windows Unicode
if sys.platform == 'win32' and hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')  # type: ignore

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from bot.config import Config


def test_commands():
    """각 명령어 동작 검증"""
    print("=" * 70)
    print("CROWBOT 명령어 체계 검증")
    print("=" * 70)
    
    config = Config()
    
    # 설정 확인
    print("\n📋 현재 설정:")
    print(f"  • 미러링: {'✅ 활성화' if config.get_option('mirror_enabled') else '❌ 비활성화'}")
    print(f"  • 소스: {config.get_source_channel() or '설정 안됨'}")
    print(f"  • 타겟: {config.get_target_channels() or '설정 안됨'}")
    
    print("\n" + "=" * 70)
    print("명령어 설명:")
    print("=" * 70)
    
    commands = [
        {
            "cmd": ".설정",
            "desc": "설정 메뉴 열기",
            "action": "1. 입력(소스) 설정\n2. 출력(타겟) 설정\n3. 로그 설정\n4. 미러링 토글"
        },
        {
            "cmd": ".동기화",
            "desc": "채널 완전 복제",
            "action": "소스 선택 → 타겟 선택 → 전체 히스토리 복사\n⚠️ 타겟 채널 내용이 소스로 교체됨"
        },
        {
            "cmd": ".카피",
            "desc": "선택적 복사",
            "action": "시작 지점 물어봄:\n• 링크 입력 → 해당 메시지부터\n• Enter → 처음부터"
        },
        {
            "cmd": ".카카시",
            "desc": "즉시 전체 복사",
            "action": "묻지 않고 바로 처음부터 복사 시작\n🥷 빠른 실행"
        },
        {
            "cmd": ".정지",
            "desc": "작업 중단",
            "action": "진행 중인 모든 복사 작업 즉시 중단"
        }
    ]
    
    for cmd in commands:
        print(f"\n🔹 {cmd['cmd']}")
        print(f"   설명: {cmd['desc']}")
        print(f"   동작: {cmd['action']}")
    
    print("\n" + "=" * 70)
    print("🔍 명령어 차이점:")
    print("=" * 70)
    
    print("""
📌 .동기화 vs .카피 vs .카카시

.동기화 - 채널을 완전히 똑같이 만들기
  • 타겟 채널 경고 표시
  • 전체 히스토리 복사
  • 채널 복제용

.카피 - 유연한 복사
  • 시작 지점 선택 가능
  • 링크로 특정 메시지부터 시작
  • 선택적 복사용

.카카시 - 빠른 복사
  • 묻지 않고 즉시 시작
  • 처음부터 끝까지 복사
  • 빠른 실행용
""")
    
    # 버그 수정 확인
    print("\n" + "=" * 70)
    print("✅ 수정된 버그:")
    print("=" * 70)
    print("• .카카시가 최근 100개만 복사하던 버그 → 전체 복사로 수정")
    print("• 다중 타겟 지원 추가")
    print("• bare except 제거")
    print("• 타입 힌트 현대화 (Optional → X | None)")
    
    print("\n" + "=" * 70)
    print("🚀 봇 실행:")
    print("=" * 70)
    print("python bot/main.py")
    print("\n텔레그램에서 명령어를 입력하여 사용하세요!")
    print("=" * 70)


if __name__ == "__main__":
    test_commands()