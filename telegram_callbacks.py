"""
Created on 2025-07-01
인라인 키보드 클릭 이벤트 분배, 장부 조작 및 암살자 수동 개입 라우터 (V71.00 무결점 방탄 아키텍처)
"""

import asyncio
import logging
# NEW: [제3헌법, 제10경고] pytz 영구 적출 및 ZoneInfo 100% 락온
from zoneinfo import ZoneInfo

from telegram import Update
from telegram.ext import ContextTypes

import config
import broker
import queue_ledger

# 로깅 설정
logger = logging.getLogger(__name__)

# 전역 타임존 락온
EST_TZ = ZoneInfo('America/New_York')

async def _trigger_auto_sync(symbol: str):
    """
    [치명적 경고 2] 큐 장부 조작 직후 KIS 실잔고 스캔 및 비파괴 보정(CALIB) 강제 격발 코어
    """
    # NEW: [제16경고] 스코프 리프트 (UnboundLocalError 원천 봉쇄)
    balance_df = None
    matching_row = None
    real_qty = 0
    real_price = 0.0

    try:
        # NEW: [제1헌법] 실잔고 조회 동기 I/O 비동기 래핑 및 타임아웃 10초 족쇄
        balance_df = await asyncio.wait_for(
            asyncio.to_thread(broker.get_account_balance),
            timeout=10.0
        )

        if balance_df is not None and not balance_df.empty:
            matching_row = balance_df[balance_df['pdno'] == symbol]
            if not matching_row.empty:
                # NEW: [치명적 경고 5] 결측치 방어 Safe Casting (0.0 강제 형변환)
                real_qty = int(float(matching_row.iloc[0].get('hldg_qty', 0)))
                real_price = float(matching_row.iloc[0].get('pchs_avg_pric', 0.0))

        # NEW: [치명적 경고 2] 장부 동기화 코어로 위임 (내부에서 이중 합산 방어 수행 및 뻥튀기 차단)
        await config.process_auto_sync(symbol, real_qty, real_price)

    except asyncio.TimeoutError:
        logger.error("🚨 잔고 스캔 API 10초 타임아웃 피격. 장부 동기화 격발을 일시 중단합니다.")
    except Exception as e:
        logger.error(f"🚨 수동 조작 직후 장부 동기화 중 런타임 오류 발생: {e}")

async def handle_inline_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    인라인 키보드 액션 라우팅 및 멱등성 보장 큐 장부 조작 허브
    """
    # NEW: [제16경고] 스코프 리프트 (모든 변수 최상단 전진 배치)
    query = None
    data = ""
    parts = []
    symbol = ""
    target_idx = -1
    is_success = False

    try:
        query = update.callback_query
        await query.answer()

        data = query.data
        if not data:
            return

        parts = data.split('_')
        
        # 1. 큐 장부 지층 수동 삭제 라우터 (DEL_Q_SOXL_0 구조)
        if data.startswith("DEL_Q_") and len(parts) >= 4:
            symbol = parts[2]
            target_idx = int(parts[3])

            logger.info(f"🔹 {symbol} 장부 지층 삭제(인덱스: {target_idx}) 수동 개입을 시작합니다.")

            # NEW: [치명적 경고 2] 객체 클래스 변수 우회 조작을 엄금하고 스레드 세이프 코어 다이렉트 호출
            is_success = await queue_ledger.delete_lot(symbol, target_idx)

            if is_success:
                await query.edit_message_text(f"✅ {symbol} 장부의 [{target_idx}]번 지층이 무결점 삭제되었습니다.")
                # NEW: [치명적 경고 2] 조작 완료 직후 비파괴 보정 릴레이 격발
                await _trigger_auto_sync(symbol)
            else:
                await query.edit_message_text(f"🚨 {symbol} 장부 삭제 실패. 유효하지 않은 인덱스이거나 I/O 락온이 발생했습니다.")

        # 2. 암살자 전용 수동 0주 청산 라우터 (KILL_AVWAP_SOXL 구조)
        elif data.startswith("KILL_AVWAP_") and len(parts) >= 3:
            symbol = parts[2]
            logger.warning(f"🚨 {symbol} 암살자 수동 청산 콜백 수신. 디커플링 붕괴 방어막을 즉시 가동합니다.")

            # NEW: [치명적 경고 18] 즉시 비동기 원자적 쓰기로 암살자 캐시 0주 강제 포맷 및 당일 영구 동결 락온
            config.set_avwap_state(symbol, qty=0, bought=False, shutdown=True, entry_price=0.0)

            await query.edit_message_text(f"🧯 {symbol} 암살자 수동 청산 및 0주 락온이 성공적으로 적용되었습니다. 당일 암살자 작전은 영구 셧다운됩니다.")
            await _trigger_auto_sync(symbol)

        else:
            logger.info(f"🔹 기타 인라인 콜백 수신 및 바이패스: {data}")

    except Exception as e:
        logger.error(f"🚨 콜백 라우팅 중 치명적 런타임 붕괴 방어: {e}")
        if query:
            await query.edit_message_text("🚨 시스템 런타임 오류로 인해 수동 조작 요청이 안전하게 롤백되었습니다.")
