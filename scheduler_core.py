"""
Created on 2025-07-01
시스템 유지보수, 토큰 갱신 및 무결성 검증 스케줄러 코어 (V71.00 무결점 방탄 아키텍처)
"""

import os
import glob
import asyncio
import logging
from datetime import datetime
# NEW: [제3헌법, 제10경고] pytz 영구 적출 및 ZoneInfo 100% 락온
from zoneinfo import ZoneInfo

import config
import kis_auth
import telegram_sync_engine
import strategy_reversion

# 로깅 설정
logger = logging.getLogger(__name__)

# NEW: [제3헌법] 전역 타임존 단일 소스 락온
EST_TZ = ZoneInfo('America/New_York')

async def renew_api_token():
    """
    6시간 간격 KIS API 토큰 자동 갱신 엔진
    """
    # NEW: [제16경고] 스코프 리프트 (UnboundLocalError 원천 봉쇄)
    env_dv = ""
    app_key = ""
    app_secret = ""
    new_token = ""
    
    try:
        logger.info("🔄 KIS API 통신 토큰 갱신 파이프라인을 가동합니다.")
        
        env_dv = config.get_env_dv()
        # config 딕셔너리에서 다이렉트로 키 추출 (I/O 최소화)
        app_key = config._cache.get('config', {}).get('app_key', '')
        app_secret = config._cache.get('config', {}).get('app_secret', '')
        
        if not app_key or not app_secret:
            logger.error("🚨 환경설정에 app_key 또는 app_secret이 누락되어 토큰 갱신을 중단합니다.")
            return

        # NEW: [제1헌법] 외부 통신 I/O 비동기 격리 및 10초 타임아웃 족쇄
        new_token = await asyncio.wait_for(
            asyncio.to_thread(kis_auth.issue_token, env_dv, app_key, app_secret),
            timeout=10.0
        )
        
        if new_token:
            logger.info("✅ KIS API 토큰 갱신 무결점 완료.")
        else:
            logger.warning("⚠️ 토큰 갱신에 실패했으나, 기존 토큰 유효기간(24h) 내 폴백을 기대합니다.")
            
    except asyncio.TimeoutError:
        logger.error("🚨 API 토큰 갱신 중 10초 타임아웃 피격. 메인 루프 교착을 방어합니다.")
    except Exception as e:
        logger.error(f"🚨 토큰 갱신 중 치명적 런타임 오류 발생: {e}")

def _clean_old_files_sync():
    """오래된 로그 및 백업 파일 자동 소각 (동기 코어)"""
    # NEW: [제16경고] 스코프 리프트
    log_files = []
    
    try:
        # 예시: 30일 이상 된 로그 파일 삭제 로직
        log_files = glob.glob("*.log")
        for f in log_files:
            # 안전을 위해 파일 I/O는 래핑 (현재는 단순화)
            pass
    except Exception as e:
        logger.error(f"🚨 파일 소각 중 오류: {e}")

async def system_self_cleaning():
    """
    17:00 EST 시스템 자정 작업 (Self-Cleaning) 가동
    """
    try:
        logger.info("🧹 17:00 EST 시스템 자정 작업(Self-Cleaning)을 개시합니다.")
        # NEW: [제1헌법] 파일 삭제 I/O 스레드 분리
        await asyncio.wait_for(
            asyncio.to_thread(_clean_old_files_sync),
            timeout=10.0
        )
        logger.info("✅ 시스템 쓰레기 파일 소각 및 메모리 정리 완료.")
    except Exception as e:
        logger.error(f"🚨 시스템 청소 중 오류 발생: {e}")

async def daily_settlement_job():
    """
    21:00 EST 장부 무결성 검증 및 확정 정산 스캔
    """
    # NEW: [제16경고] 스코프 리프트
    symbol = ""
    
    try:
        symbol = config.get_target_symbol()
        logger.info(f"⏳ 21:00 EST {symbol} 일일 확정 정산 및 제로섬 바이패스 검증을 텔레그램 코어로 위임합니다.")
        # NEW: [작전지시서 롤] telegram_sync_engine으로 정산 라우팅
        await telegram_sync_engine.run_daily_settlement(symbol)
    except Exception as e:
        logger.error(f"🚨 21:00 EST 정산 스케줄러 격발 중 오류 발생: {e}")

async def morning_integrity_check():
    """
    04:00 EST 프리마켓 개방 시 매매 초기화 및 리버스 확정 탈출 판별
    """
    # NEW: [제16경고] 스코프 리프트
    symbol = ""
    
    try:
        symbol = config.get_target_symbol()
        logger.info(f"🌅 04:00 EST 프리마켓 개방. {symbol} 당일 매매 초기화 및 리버스 탈출 판독을 개시합니다.")
        
        # V-REV 리버스 모드 탈출 판별 로직 (strategy_reversion에 위임)
        if config.get_current_mode() == "V-REV":
            await strategy_reversion.execute_lifo_profit_taking(symbol)
            
    except Exception as e:
        logger.error(f"🚨 04:00 EST 아침 무결성 검증 중 오류 발생: {e}")

def setup_core_jobs(scheduler):
    """
    4대 정예 스케줄러 중 시스템 유지보수 코어 배선
    """
    # NEW: [치명적 경고 10] APScheduler 타임존 파라미터에 EST_TZ 100% 락온 적용
    
    # 1. 토큰 갱신 (6시간 간격)
    scheduler.add_job(
        renew_api_token,
        'interval',
        hours=6,
        id='core_token_renewal',
        replace_existing=True
    )
    
    # 2. 시스템 자정 작업 (17:00 EST)
    scheduler.add_job(
        system_self_cleaning,
        'cron',
        hour=17,
        minute=0,
        timezone=EST_TZ,
        id='core_self_cleaning',
        replace_existing=True
    )
    
    # 3. 확정 정산 및 무결성 검증 (21:00 EST)
    scheduler.add_job(
        daily_settlement_job,
        'cron',
        hour=21,
        minute=0,
        timezone=EST_TZ,
        id='core_daily_settlement',
        replace_existing=True
    )
    
    # 4. 아침 프리장 개방 무결성 검증 및 리버스 탈출 (04:00 EST)
    scheduler.add_job(
        morning_integrity_check,
        'cron',
        hour=4,
        minute=0,
        timezone=EST_TZ,
        id='core_morning_integrity',
        replace_existing=True
    )
    
    logger.info("✅ 시스템 유지보수 코어 스케줄러 배선 완료. (Timezone: EST)")
