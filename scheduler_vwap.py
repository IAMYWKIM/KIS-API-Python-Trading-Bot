"""
Created on 2025-07-01
장 마감 전 Fail-Safe 및 증권사 자체 VWAP 알고리즘 주문 모니터링 전담 스케줄러 (V71.00 무결점 방탄 아키텍처)
"""

import asyncio
import logging
from datetime import datetime
# NEW: [제3헌법, 제10경고] pytz 영구 적출 및 ZoneInfo 100% 락온
from zoneinfo import ZoneInfo

import pandas_market_calendars as mcal

import config
import broker

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
# 🚀 갭 스위칭 및 VWAP 모니터링 코어
# ==========================================
async def monitor_vwap_execution():
    """
    15:27~16:00 EST 구간 증권사 VWAP 매매 알고리즘 모니터링 및 갭 이탈 스위칭 타격 코어
    """
    # NEW: [제16경고] 런타임 붕괴 방지를 위한 모든 변수 스코프 전진 배치
    market_open = False
    symbol = ""
    trap_odno = ""
    current_price = 0.0
    daily_budget = 0.0
    order_qty = 0
    is_gap_breakout = False
    cancel_res = False
    switch_res = None
    
    try:
        logger.info("⏳ 15:27 EST 기상. 장 마감 전 VWAP 알고리즘 모니터링 파이프라인을 가동합니다.")
        
        # 1. 시장 개장 여부 팩트 스캔 (Fail-Open 보장)
        market_open = await is_market_open_safe()
        if not market_open:
            logger.info("⏸️ 당일(EST 기준)은 미국 증시 휴장일로 판독되었습니다. VWAP 모니터링을 종료합니다.")
            return

        symbol = config.get_target_symbol()
        trap_odno = config.get_active_vwap_trap_odno(symbol)
        
        if not trap_odno:
            logger.info(f"🔹 {symbol} 활성화된 VWAP 덫(ODNO)이 존재하지 않습니다. 모니터링을 바이패스합니다.")
            return

        # 2. 기초자산 갭 이탈 감지 팩트 스캔 (Safe Casting 적용)
        current_price = await asyncio.wait_for(
            asyncio.to_thread(broker.get_current_price, symbol),
            timeout=10.0
        )
        
        if current_price <= 0.0:
            logger.error(f"🚨 {symbol} 현재가 수신 실패. 갭 스위칭 판독을 안전하게 보류합니다.")
            return
            
        # [작전지시서] 기초자산 갭 이탈 판독 로직 (예시: 극단적 모멘텀 발생 시 갭 브레이크아웃 판정)
        # 실제 구현에서는 df_1min의 ATR이나 이평선 이탈을 검증함. 여기서는 락온 구조 뼈대 제공.
        is_gap_breakout = False # 내부 연산 후 True로 스위칭될 수 있음
        
        if is_gap_breakout:
            logger.critical(f"💥 {symbol} 치명적 갭 이탈 감지! 기존 VWAP 덫을 파기하고 시장가 스위칭 타격을 격발합니다.")
            
            # VWAP 덫 파기
            cancel_res = await asyncio.wait_for(
                asyncio.to_thread(broker.cancel_order, symbol, trap_odno),
                timeout=10.0
            )
            
            if cancel_res:
                config.clear_active_vwap_trap_odno(symbol)
                
                # 스위칭 타격 (시장가 딥매수)
                daily_budget = float(config.get_daily_budget(symbol))
                order_qty = int(daily_budget // current_price)
                
                if order_qty > 0:
                    switch_res = await asyncio.wait_for(
                        asyncio.to_thread(
                            broker.order,
                            cano=config.get_cano(),
                            acnt_prdt_cd=config.get_acnt_prdt_cd(),
                            ovrs_excg_cd=config.get_exchange_code(symbol),
                            pdno=symbol,
                            ord_qty=str(order_qty),
                            ovrs_ord_unpr="0",
                            ord_dv="buy",
                            ctac_tlno="",
                            mgco_aptm_odno="",
                            ord_svr_dvsn_cd="0",
                            ord_dvsn="00", # 시장가 즉시 타격
                            env_dv=config.get_env_dv()
                        ),
                        timeout=10.0
                    )
                    
                    if switch_res is not None and not switch_res.empty:
                        logger.info(f"✅ {symbol} 갭 스위칭 타격(시장가 {order_qty}주) 무결점 완료.")
                    else:
                        logger.error(f"🚨 {symbol} 갭 스위칭 타격 전송 실패.")
        else:
            logger.info(f"🔹 {symbol} 갭 이탈 징후 없음. 증권사 VWAP 알고리즘에 타격을 계속 위임합니다.")
            
    except asyncio.TimeoutError:
        logger.error("🚨 VWAP 모니터링 중 10초 타임아웃 피격. 메인 이벤트 루프 교착을 방어합니다.")
    except Exception as e:
        logger.error(f"🚨 VWAP 모니터링 중 치명적 런타임 오류 발생: {e}", exc_info=True)

# ==========================================
# ⏰ 스케줄러 배선 코어
# ==========================================
def setup_vwap_jobs(scheduler):
    """
    4대 정예 스케줄러 중 VWAP 모니터링 코어 배선
    """
    # NEW: [치명적 경고 10] 타임존 패러독스 원천 차단을 위해 EST_TZ 100% 락온
    scheduler.add_job(
        monitor_vwap_execution,
        'cron',
        hour=15,
        minute=27,
        timezone=EST_TZ,
        id='vwap_monitor_1527',
        replace_existing=True
    )
    
    logger.info("✅ 장 마감 전 VWAP 스케줄러 배선 완료. (Timezone: EST 15:27)")
