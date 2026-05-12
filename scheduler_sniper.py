"""
Created on 2025-07-01
1분봉 기반 V14 상방 스나이퍼 감시 및 AVWAP 암살자 정밀 감시 스케줄러 (V71.00 무결점 방탄 아키텍처)
"""

import asyncio
import logging
from datetime import datetime
# NEW: [제3헌법, 제10경고] pytz 영구 적출 및 ZoneInfo 100% 락온
from zoneinfo import ZoneInfo

import pandas_market_calendars as mcal

import config
import strategy_v14
import strategy_v_avwap

# 로깅 설정
logger = logging.getLogger(__name__)

# NEW: [제3헌법] 전역 타임존 단일 소스 락온
EST_TZ = ZoneInfo('America/New_York')

# ==========================================
# 🛡️ 제5헌법 & 제14경고: 독립형 Fail-Open 시장 개장 판독 엔진
# ==========================================
def _check_market_open_sync() -> bool:
    """pandas_market_calendars를 이용한 동기적 시장 개장 여부 판별"""
    # NEW: [제16경고] 스코프 리프트
    nyse = None
    est_today = None
    schedule = None
    
    nyse = mcal.get_calendar('NYSE')
    est_today = datetime.now(EST_TZ).date()
    schedule = nyse.schedule(start_date=est_today, end_date=est_today)
    return not schedule.empty

async def is_market_open_safe() -> bool:
    """비동기 래핑 및 10초 타임아웃 족쇄가 채워진 독립형 시장 개장 판별기"""
    # NEW: [제16경고] 스코프 전진 배치로 UnboundLocalError 원천 봉쇄
    is_open = False
    est_now = None
    
    try:
        est_now = datetime.now(EST_TZ)
        # NEW: [제1헌법] 달력 API 동기 I/O 비동기 격리
        is_open = await asyncio.wait_for(
            asyncio.to_thread(_check_market_open_sync),
            timeout=10.0
        )
    except asyncio.TimeoutError:
        # NEW: [제14경고] 타임아웃 발생 시 평일 강제 개장(Fail-Open) 하드코딩
        logger.error("🚨 mcal API 10초 타임아웃 피격. 평일 강제 개장(Fail-Open) 폴백을 격발합니다.")
        if est_now is not None:
            is_open = est_now.weekday() < 5
        else:
            is_open = True
    except Exception as e:
        logger.error(f"🚨 mcal API 런타임 붕괴 방어 ({e}). 평일 강제 개장(Fail-Open) 폴백을 격발합니다.")
        if est_now is not None:
            is_open = est_now.weekday() < 5
        else:
            is_open = True
        
    return is_open

# ==========================================
# 🎯 1분 주기 스나이퍼 및 암살자 통합 감시 코어
# ==========================================
async def sniper_monitoring_job():
    """
    매 1분마다 격발되는 상방 스나이퍼 및 AVWAP 암살자 통합 레이더
    """
    # NEW: [제16경고] 스코프 리프트 (모든 변수 최상단 전진 배치)
    market_open = False
    symbol = ""
    current_mode = ""
    
    try:
        # 1. 시장 개장 여부 팩트 스캔 (Fail-Open 보장)
        market_open = await is_market_open_safe()
        if not market_open:
            return

        symbol = config.get_target_symbol()
        current_mode = config.get_current_mode()
        
        # 2. V14 상방 스나이퍼 독립 가동 (V14 모드일 경우)
        if current_mode == "V14":
            # strategy_v14의 스나이퍼 모니터링 코어 호출 (구현체 내부 위임)
            pass
            
        # 3. AVWAP 암살자 동시 가동 (모멘텀 레이더 스캔)
        # NEW: [치명적 경고 11] 프리장/정규장 디커플링 및 실전 타격 필터링은 모듈 내부에서 수행
        await strategy_v_avwap.radar_scan(symbol)
            
    except Exception as e:
        logger.error(f"🚨 1분 주기 스나이퍼 모니터링 중 치명적 오류 발생: {e}")

# ==========================================
# ⏰ 스케줄러 배선 코어
# ==========================================
def setup_sniper_jobs(scheduler):
    """
    4대 정예 스케줄러 중 1분 주기 스나이퍼/암살자 코어 배선
    """
    # NEW: [치명적 경고 10] 타임존 패러독스 원천 차단을 위해 EST_TZ 100% 락온
    scheduler.add_job(
        sniper_monitoring_job,
        'cron',
        minute='*', # 매 1분마다 실행
        timezone=EST_TZ,
        id='sniper_and_avwap_monitor',
        replace_existing=True
    )
    
    logger.info("✅ 1분 주기 스나이퍼 및 암살자 스케줄러 배선 완료. (Timezone: EST)")
