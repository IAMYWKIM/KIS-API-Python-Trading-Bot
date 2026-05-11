"""
Created on 2025-07-01
인피니트 스노우볼 시스템 진입점 (V71.00 무결점 방탄 아키텍처)
"""

import asyncio
import logging
import os
import sys
# NEW: [제3헌법, 제10경고] pytz 영구 적출 및 ZoneInfo 100% 락온
from zoneinfo import ZoneInfo

from apscheduler.schedulers.asyncio import AsyncIOScheduler

# 하위 모듈 임포트 (아키텍처 명세 기반)
import config
import telegram_bot
import scheduler_core
import scheduler_regular
import scheduler_vwap
import scheduler_sniper

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# NEW: [제3헌법] 전역 논리적 시계열 EST 락온
EST_TZ = ZoneInfo('America/New_York')

async def main_loop():
    """
    시스템 메인 이벤트 루프 및 4대 정예 스케줄러 독립 배선 코어
    """
    # NEW: [제16경고] 변수 스코프 전진 배치로 UnboundLocalError 원천 봉쇄
    scheduler = None
    bot_task = None
    
    try:
        logger.info("🚀 인피니트 스노우볼 V71.00 퀀트 엔진 가동을 시작합니다.")
        
        # 환경설정 및 장부 무결성 검증 초기화
        await config.initialize_system()

        # 스케줄러 인스턴스 생성 (EST 타임존 100% 락온)
        scheduler = AsyncIOScheduler(timezone=EST_TZ)

        logger.info("🔹 4대 정예 스케줄러 배선을 시작합니다.")
        # NEW: [아키텍처 롤] 4대 스케줄러 모듈 주입
        scheduler_core.setup_core_jobs(scheduler)
        scheduler_regular.setup_regular_jobs(scheduler)
        scheduler_vwap.setup_vwap_jobs(scheduler)
        scheduler_sniper.setup_sniper_jobs(scheduler)

        # 스케줄러 가동
        scheduler.start()
        logger.info("✅ 스케줄러 코어 가동 완료. (Timezone: EST)")

        # 텔레그램 데몬 구동 (비동기 태스크 분리)
        logger.info("🔹 텔레그램 C4I 관제탑 통신을 연결합니다.")
        bot_task = asyncio.create_task(telegram_bot.start_polling())
        
        # 시스템 무한 대기 (Heartbeat)
        while True:
            await asyncio.sleep(3600)
            
    except asyncio.CancelledError:
        logger.warning("⚠️ 시스템 종료 신호가 감지되었습니다. 셧다운 시퀀스를 시작합니다.")
    except Exception as e:
        logger.error(f"🚨 메인 루프 치명적 오류 발생: {e}", exc_info=True)
    finally:
        logger.info("🛑 시스템 자원을 해제합니다.")
        if scheduler and scheduler.running:
            scheduler.shutdown(wait=False)
        if bot_task and not bot_task.done():
            bot_task.cancel()
        
        # NEW: [제15경고] 좀비 프로세스 방어를 위한 파이썬 자체 하드 킬 격발
        logger.critical("💥 프로세스를 완전히 자폭(Kill) 시켜 OS 레벨 재부팅을 유도합니다.")
        os._exit(0)

if __name__ == "__main__":
    # NEW: [제1경고] 메인 진입점부터 타임존 락온 방어막 실행
    os.environ['TZ'] = 'America/New_York'
    
    try:
        asyncio.run(main_loop())
    except KeyboardInterrupt:
        logger.info("사용자 수동 종료. 엔진을 정지합니다.")
        sys.exit(0)
