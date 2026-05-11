"""
Created on 2025-07-01
AVWAP 암살자 실시간 타임-스플릿 레이더 관제탑 (V71.00 무결점 방탄 아키텍처)
"""

import logging
from datetime import datetime
# NEW: [제3헌법, 제10경고] pytz 영구 적출 및 ZoneInfo 100% 락온
from zoneinfo import ZoneInfo

from telegram import Update
from telegram.ext import ContextTypes

import config

# 로깅 설정
logger = logging.getLogger(__name__)

# NEW: [제3헌법] 논리적 시계열 EST, UI 렌더링 전용 KST 격리
EST_TZ = ZoneInfo('America/New_York')
KST_TZ = ZoneInfo('Asia/Seoul')

async def render_radar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /avwap 명령어 호출 시 응답하는 실시간 모멘텀 레이더 관제탑 렌더링 엔진
    """
    # NEW: [제16경고] 스코프 리프트 (UnboundLocalError 원천 봉쇄)
    now_est = None
    now_kst_str = ""
    symbol = ""
    state = {}
    is_shutdown = False
    is_bought = False
    qty = 0
    hour = 0
    minute = 0
    msg = ""

    try:
        now_est = datetime.now(EST_TZ)
        # NEW: [제3헌법] KST는 오직 UI 표출 용도로만 철저히 격리
        now_kst_str = datetime.now(KST_TZ).strftime("%Y-%m-%d %H:%M:%S")
        symbol = config.get_target_symbol()
        
        # 암살자 L1 캐시 상태 스캔
        state = config.get_avwap_state(symbol)
        is_shutdown = state.get('shutdown', False)
        is_bought = state.get('bought', False)
        qty = int(state.get('qty', 0))
        
        hour = now_est.hour
        minute = now_est.minute

        msg = f"🔫 <b>AVWAP 암살자 실시간 레이더 관제탑</b>\n\n"
        msg += f"🕒 렌더링 시각 (KST): {now_kst_str}\n"
        # NEW: [치명적 경고 11] 숏(SOXS) 운용 텍스트 영구 소각
        msg += f"🎯 타겟 종목: {symbol} (단일 롱 모멘텀 전용)\n\n"

        # NEW: [치명적 경고 17] 하드스탑 또는 수동 청산 셧다운 플래그 오버라이드
        if is_shutdown:
            msg += "🚨 <b>ATR5 동적 하드스탑 피격(또는 수동 0주 락온)에 의한 당일 영구 동결</b>\n"
            msg += "금일 암살자 작전은 완전히 셧다운되었습니다. 추가 진입은 철저히 차단됩니다."
            await update.message.reply_text(msg, parse_mode="HTML")
            return

        # 암살자 딥매수 진입 완료 상태
        if is_bought:
            msg += f"🔥 <b>현재 암살자 실전 타격 진행 중!</b>\n"
            msg += f"🔹 보유 물량: {qty}주\n"
            msg += "🔹 장 마감 35분 전(15:22~15:25 EST) 전량 덤핑 대기 중\n"
            await update.message.reply_text(msg, parse_mode="HTML")
            return

        # NEW: [치명적 경고 11] 09:30~09:34 EST 캔들 미완성 대기 렌더링 방어막
        if hour == 9 and 30 <= minute < 35:
            msg += "⏳ <b>캔들 형성 대기 중</b>\n"
            msg += "정규장 개장 직후 프리장 노이즈를 완벽히 소각하고 5분봉 하이킨아시 캔들 완성을 대기 중입니다."
            await update.message.reply_text(msg, parse_mode="HTML")
            return
            
        # 프리장 모니터링 (실제 타격은 보류)
        if hour < 9 or (hour == 9 and minute < 30):
            msg += "📡 <b>프리장 관측 모드 가동 중</b>\n"
            msg += "정규장 개장 전까지 기초지수 갭과 모멘텀을 추적합니다. (실제 타격은 정규장 개장 이후 09:35부터 가동)\n"
            msg += "※ 숏(SOXS) 타격 로직은 절대 헌법에 따라 영구 소각되었습니다."
            await update.message.reply_text(msg, parse_mode="HTML")
            return
            
        # 정규장 모니터링 상태 (타격 대기)
        msg += "📡 <b>정규장 실시간 모멘텀 스캔 중</b>\n"
        msg += "🔹 원웨이 갭 필터 및 시계열 체력 측정 중...\n"
        msg += "🔹 수급 모멘텀 및 하이킨아시 2연속 양봉 격발 대기 중...\n"
        msg += "※ 조건 부합 시 즉각 순수 가능 예산 95% 할당 및 딥매수 타격 예정"

        await update.message.reply_text(msg, parse_mode="HTML")

    except Exception as e:
        logger.error(f"🚨 암살자 레이더 관제탑 렌더링 중 런타임 오류 발생: {e}")
        await update.message.reply_text("🚨 관제탑 시스템 오류가 발생했습니다. 로그 진단망을 확인하십시오.", parse_mode="HTML")
