"""
Created on 2025-07-01
정규장 예방적 덫 스케줄러 (V71.00 무결점 방탄 아키텍처)
"""

import asyncio
import random
import logging
from datetime import datetime
# NEW: [제3헌법, 제10경고] pytz 영구 적출 및 ZoneInfo 100% 락온
from zoneinfo import ZoneInfo

import pandas_market_calendars as mcal

# 하위 통제실 및 코어 모듈 배선
import config
import strategy
import telegram_view

# 로깅 설정
logger = logging.getLogger(__name__)

# NEW: [제3헌법] 전역 타임존 단일 소스 락온
EST_TZ = ZoneInfo('America/New_York')

# NEW: [제5헌법, 제14경고] 달력 API 동기 함수 분리 및 런타임 붕괴 방어용
def _check_market_open_sync() -> bool:
    """
    pandas_market_calendars를 이용한 동기적 시장 개장 여부 판별
    """
    nyse = mcal.get_calendar('NYSE')
    est_today = datetime.now(EST_TZ).date()
    schedule = nyse.schedule(start_date=est_today, end_date=est_today)
    return not schedule.empty

async def is_market_open_safe() -> bool:
    """
    비동기 래핑 및 10초 타임아웃 족쇄가 채워진 시장 개장 판별 엔진
    """
    # NEW: [제16경고] 변수 스코프 전진 배치로 UnboundLocalError 원천 봉쇄
    is_open = False
    est_now = datetime.now(EST_TZ)
    
    try:
        # NEW: [제1헌법] 달력 API 동기 I/O 비동기 격리 및 메인 루프 교착 방어
        is_open = await asyncio.wait_for(
            asyncio.to_thread(_check_market_open_sync),
            timeout=10.0
        )
    except asyncio.TimeoutError:
        # NEW: [제14경고] 타임아웃 발생 시 평일 강제 개장(Fail-Open) 하드코딩
        logger.error("🚨 mcal API 10초 타임아웃 피격. 평일 강제 개장(Fail-Open) 폴백을 격발합니다.")
        is_open = est_now.weekday() < 5
    except Exception as e:
        logger.error(f"🚨 mcal API 런타임 붕괴 방어 ({e}). 평일 강제 개장(Fail-Open) 폴백을 격발합니다.")
        is_open = est_now.weekday() < 5
        
    return is_open

async def execute_proactive_traps():
    """
    17:05 KST 타겟 V14 LOC 및 V-REV VWAP 예방적 덫 장전 파이프라인
    """
    # NEW: [제16경고] 런타임 붕괴 방지를 위한 변수 선언 전진 배치
    jitter_sec = 0
    market_open = False
    
    try:
        # NEW: [작전지시서 1-2] 180초 지터(Jitter) 난수 발생 및 대기 (자전거래 방어용 시차)
        jitter_sec = random.randint(0, 180)
        logger.info(f"⏳ 예방적 덫 스케줄러 기상. {jitter_sec}초 지터(Jitter) 대기 후 타격을 개시합니다.")
        await asyncio.sleep(jitter_sec)

        # 시장 휴장 여부 팩트 스캔
        market_open = await is_market_open_safe()
        if not market_open:
            logger.info("⏸️ 옴니 매트릭스 판독 결과 당일(EST 기준)은 미국 증시 휴장일입니다. 덫 장전을 전면 취소합니다.")
            return

        logger.info("🚀 옴니 매트릭스 작전 개시. 중앙 라우팅 허브로 예방적 덫 장전을 위임합니다.")
        # NEW: [작전지시서 2] strategy로 위임하여 0주 락온 기반 모드별 덫(LOC/VWAP) 장전 통제
        await strategy.deploy_proactive_traps()

        logger.info("📝 타격 완료. 텔레그램 C4I 관제탑으로 통합 작전지시서를 송출합니다.")
        # NEW: [작전지시서 1-1] 통합 지시서 포맷팅 및 전송 전담 (UI 격리)
        await telegram_view.broadcast_daily_instructions()

    except Exception as e:
        logger.error(f"🚨 예방적 덫 장전 중 치명적 오류 발생: {e}", exc_info=True)

def setup_regular_jobs(scheduler):
    """
    4대 정예 스케줄러 배선 (정규장 예방적 덫 전담)
    """
    # NEW: [치명적 경고 1] 17:05 KST를 EST로 동적 래핑하여 타임존 패러독스 원천 차단
    # KST 시간을 EST로 치환하여 APScheduler에 EST 락온(Lock-on) 상태로 주입
    now_kst = datetime.now(ZoneInfo('Asia/Seoul'))
    target_kst = now_kst.replace(hour=17, minute=5, second=0, microsecond=0)
    target_est = target_kst.astimezone(EST_TZ)

    scheduler.add_job(
        execute_proactive_traps,
        trigger='cron',
        hour=target_est.hour,
        minute=target_est.minute,
        timezone=EST_TZ,  # 제3헌법에 의거 오직 EST만 사용
        id='regular_1705_traps',
        replace_existing=True
    )
    
    logger.info(f"✅ 정규장 예방적 덫 스케줄러 배선 완료. (타임존 락온: EST {target_est.hour:02d}:{target_est.minute:02d})")
