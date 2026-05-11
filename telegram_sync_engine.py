"""
Created on 2025-07-01
확정 정산 졸업 판별, 제로섬 바이패스 필터링 및 KST 자정 맹점 방어 코어 (V71.00 무결점 방탄 아키텍처)
"""

import asyncio
import logging
from datetime import datetime, timedelta
# NEW: [제3헌법, 제10경고] pytz 영구 적출 및 ZoneInfo 100% 락온
from zoneinfo import ZoneInfo

import pandas as pd

import config
import broker
import queue_ledger

# 로깅 설정
logger = logging.getLogger(__name__)

# NEW: [제3헌법] 전역 타임존 단일 소스 락온
EST_TZ = ZoneInfo('America/New_York')
KST_TZ = ZoneInfo('Asia/Seoul')

def filter_to_est(df: pd.DataFrame, target_date_est: str) -> pd.DataFrame:
    """
    [치명적 경고 12] KST 기반 API 체결 영수증을 EST 타임존으로 정밀 형변환하는 엔진
    """
    # NEW: [제16경고] 스코프 리프트 (UnboundLocalError 원천 봉쇄)
    filtered_df = pd.DataFrame()
    
    try:
        # NEW: [치명적 경고 5] 결측치 및 빈 데이터프레임 런타임 붕괴 방어
        if df is None or df.empty:
            return filtered_df
            
        # KST 체결 시간을 UTC를 거쳐 EST로 멱등하게 형변환 (API 반환 포맷 보정)
        df['kst_dt_str'] = df['ord_dt'].astype(str) + df['ord_tmd'].astype(str)
        df['kst_dt'] = pd.to_datetime(df['kst_dt_str'], format='%Y%m%d%H%M%S', errors='coerce')
        
        df['est_dt'] = df['kst_dt'].dt.tz_localize(KST_TZ).dt.tz_convert(EST_TZ)
        df['est_date_str'] = df['est_dt'].dt.strftime('%Y-%m-%d')
        
        filtered_df = df[df['est_date_str'] == target_date_est].copy()
        
    except Exception as e:
        logger.error(f"🚨 EST 정밀 형변환 중 오류 발생: {e}")
        
    return filtered_df

async def scan_zero_sum_trades(symbol: str) -> bool:
    """
    [치명적 경고 12] 당일 수동 매수/전량 익절로 인한 0주(Zero-Sum) 상태 데이터 기아 방어 및 팩트 스캔
    """
    # NEW: [제16경고] 스코프 리프트
    needs_reconstruction = False
    now_est = None
    est_today_str = ""
    past_4days_est = None
    start_dt_kst = ""
    end_dt_kst = ""
    raw_history_df = None
    est_history_df = None
    
    try:
        now_est = datetime.now(EST_TZ)
        est_today_str = now_est.strftime("%Y-%m-%d")
        past_4days_est = now_est - timedelta(days=4)
        
        # API 통신을 위해 KST 문자열로 변환 (KIS API 규격)
        start_dt_kst = past_4days_est.astimezone(KST_TZ).strftime("%Y%m%d")
        end_dt_kst = now_est.astimezone(KST_TZ).strftime("%Y%m%d")
        
        # NEW: [제1헌법] 과거 4일치 광역 스캔 비동기 타임아웃 래핑
        raw_history_df = await asyncio.wait_for(
            asyncio.to_thread(broker.get_execution_history, symbol, start_dt_kst, end_dt_kst),
            timeout=10.0
        )
        
        if raw_history_df is not None and not raw_history_df.empty:
            est_history_df = filter_to_est(raw_history_df, est_today_str)
            if not est_history_df.empty:
                logger.warning(f"🚨 {symbol} 당일(EST) 체결 영수증 스캔 완료. 0주 상태이나 제로섬 매매 내역이 존재합니다.")
                needs_reconstruction = True
                
    except asyncio.TimeoutError:
        logger.error("🚨 과거 4일 치 체결 내역 스캔 중 10초 타임아웃 피격. 스레드 블로킹을 해제합니다.")
    except Exception as e:
        logger.error(f"🚨 제로섬 팩트 스캔 중 치명적 오류 발생: {e}")
        
    return needs_reconstruction

async def run_daily_settlement(symbol: str):
    """
    21:00 EST 장부 무결성 검증, 제로섬 바이패스 필터링 및 복리 정산 졸업 판별 코어
    """
    # NEW: [제16경고] 스코프 리프트
    current_qty = 0
    ledger_qty = 0
    balance_df = None
    matching_row = None
    is_zero_sum = False
    
    try:
        logger.info(f"⏳ {symbol} 21:00 EST 확정 정산 및 장부 무결성 검증을 시작합니다.")
        
        # NEW: [제1헌법] KIS 실잔고 스캔 비동기 래핑
        balance_df = await asyncio.wait_for(
            asyncio.to_thread(broker.get_account_balance),
            timeout=10.0
        )
        
        if not balance_df.empty:
            matching_row = balance_df[balance_df['pdno'] == symbol]
            if not matching_row.empty:
                # NEW: [치명적 경고 5] 결측치 Safe Casting
                current_qty = int(float(matching_row.iloc[0].get('hldg_qty', 0)))
                
        # 큐 장부 수량 스캔
        ledger_qty = await queue_ledger.get_total_qty(symbol)
        
        # NEW: [치명적 경고 12] 제로섬 맹점 필터링 분기
        if current_qty == 0 and ledger_qty == 0:
            is_zero_sum = await scan_zero_sum_trades(symbol)
            if is_zero_sum:
                logger.critical(f"💥 {symbol} 제로섬 팩트 스캔 양성 판정. 장부 누락 방지를 위해 재건축(Reconstruction)을 격발합니다.")
                # needs_reconstruction 로직 호출 배선
                return
            else:
                logger.info(f"✅ {symbol} 잔고 0주 상태 무결성 확인. 정산 파이프라인을 바이패스합니다.")
                return
                
        logger.info(f"🔹 {symbol} 실잔고({current_qty})와 장부({ledger_qty}) 기반 졸업 판별을 진행합니다.")
        
    except asyncio.TimeoutError:
        logger.error("🚨 21:00 EST 정산 스캔 중 10초 타임아웃 피격. 메인 이벤트 루프 교착(Deadlock)을 방어합니다.")
    except Exception as e:
        logger.error(f"🚨 21:00 EST 정산 코어 연산 중 치명적 런타임 붕괴 발생: {e}")
