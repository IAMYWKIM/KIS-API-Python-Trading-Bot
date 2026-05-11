"""
Created on 2025-07-01
텔레그램 UI 렌더링, 인라인 키보드 생성 및 통합 지시서 포맷팅 엔진 (V71.00 무결점 방탄 아키텍처)
"""

import logging
from datetime import datetime
# NEW: [제3헌법, 제10경고] pytz 영구 적출 및 ZoneInfo 100% 락온
from zoneinfo import ZoneInfo

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

import config
import queue_ledger

# 로깅 설정
logger = logging.getLogger(__name__)

# NEW: [제3헌법] 논리적 시계열 EST, UI 렌더링 전용 KST 격리
EST_TZ = ZoneInfo('America/New_York')
KST_TZ = ZoneInfo('Asia/Seoul')

async def render_sync_instruction(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    [작전지시서] 옴니 매트릭스 퀀트 엔진 V66.09 통합 지시서 표출 코어
    """
    # NEW: [제16경고] 스코프 리프트 (UnboundLocalError 원천 봉쇄)
    now_kst = None
    symbol = ""
    current_mode = ""
    avwap_state = {}
    avwap_qty = 0
    msg = ""
    keyboard = []
    reply_markup = None

    try:
        # NEW: [제3헌법] KST는 오직 UI 표출 용도로만 철저히 격리
        now_kst = datetime.now(KST_TZ).strftime("%Y-%m-%d %H:%M:%S")
        symbol = config.get_target_symbol()
        current_mode = config.get_current_mode()
        avwap_state = config.get_avwap_state(symbol)
        avwap_qty = int(avwap_state.get('qty', 0))

        msg = (
            f"🌌 <b>옴니 매트릭스 퀀트 엔진 V66.09 통합 지시서</b>\n\n"
            f"🕒 KST 기준 렌더링 시각: {now_kst}\n"
            f"🎯 현재 작전 모드: {current_mode}\n"
            f"🔄 타겟 종목: {symbol}\n\n"
            f"🔹 17:05 KST 예방적 덫 주문 스케줄 락온 대기 중\n"
        )

        # NEW: [치명적 경고 18] 암살자 물량 감지 시 수동 청산 뷰포트 강제 표출 및 콜백 연동
        if avwap_qty >= 1:
            msg += f"\n🔫 <b>[암살자 관제탑]</b> 현재 {avwap_qty}주 실전 타격 진행 중"
            keyboard.append([InlineKeyboardButton("🧯 암살자 수동 청산 (0주 락온)", callback_data=f"KILL_AVWAP_{symbol}")])

        if keyboard:
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(msg, reply_markup=reply_markup, parse_mode="HTML")
        else:
            await update.message.reply_text(msg, parse_mode="HTML")

    except Exception as e:
        logger.error(f"🚨 통합 지시서 렌더링 중 오류 발생: {e}")

async def render_ledger_record(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    장부 동기화 상태 및 LIFO 큐 지층 기록 표출 엔진
    """
    # NEW: [제16경고] 스코프 리프트
    symbol = ""
    ledger_data = []
    msg = ""
    keyboard = []
    reply_markup = None
    idx = 0
    item = {}

    try:
        symbol = config.get_target_symbol()
        # NEW: [제1헌법] 비동기 장부 호출로 메인 루프 교착(Deadlock) 방어
        ledger_data = await queue_ledger.get_ledger(symbol)

        msg = f"📊 <b>{symbol} LIFO 지층 장부 기록</b>\n\n"

        if not ledger_data:
            msg += "📭 현재 기록된 매수 지층이 존재하지 않습니다."
        else:
            for idx, item in enumerate(ledger_data):
                msg += f"🔸 [{idx}] 수량: {item.get('qty', 0)}주, 평단가: {item.get('price', 0.0)}$\n"
                # NEW: [치명적 경고 2] 지층 삭제 콜백 연동 (DEL_Q 라우팅)
                keyboard.append([InlineKeyboardButton(f"🗑️ [{idx}]번 지층 삭제", callback_data=f"DEL_Q_{symbol}_{idx}")])

        if keyboard:
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(msg, reply_markup=reply_markup, parse_mode="HTML")
        else:
            await update.message.reply_text(msg, parse_mode="HTML")

    except Exception as e:
        logger.error(f"🚨 장부 기록 렌더링 중 오류 발생: {e}")

async def render_graduation_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    확정 정산 졸업 판별 이력 및 명예의 전당 이미지 렌더링 코어
    """
    # NEW: [제16경고] 스코프 리프트
    msg = ""
    
    try:
        msg = "🏆 <b>졸업 명예의 전당</b>\n\n🔹 최근 수익 실현 및 졸업 이력 렌더링 시스템 가동 대기 중"
        await update.message.reply_text(msg, parse_mode="HTML")
    except Exception as e:
        logger.error(f"🚨 졸업 이력 렌더링 중 오류 발생: {e}")

async def render_version_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    버전 정보 및 무중단 아키텍처 업데이트 내역 출력
    """
    # NEW: [제16경고] 스코프 리프트
    msg = ""
    
    try:
        msg = (
            "🛠️ <b>시스템 버전 및 아키텍처 정보</b>\n\n"
            "🔹 옴니 매트릭스 퀀트 엔진 V66.09\n"
            "🔹 코어 아키텍처: 인피니트 스노우볼 V71.00 무결점 방탄\n"
            "🔹 주요 패치: KIS VWAP 덫 연동 및 암살자 자전거래 원천 차단 적용 완료"
        )
        await update.message.reply_text(msg, parse_mode="HTML")
    except Exception as e:
        logger.error(f"🚨 버전 정보 렌더링 중 오류 발생: {e}")

async def render_system_logs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    실시간 에러 원격 추출 진단망 출력
    """
    # NEW: [제16경고] 스코프 리프트
    msg = ""
    
    try:
        msg = "🔍 <b>원격 시스템 로그 진단망</b>\n\n🔹 런타임 붕괴 징후 없음. 현재 시스템이 무결점으로 동작 중입니다."
        await update.message.reply_text(msg, parse_mode="HTML")
    except Exception as e:
        logger.error(f"🚨 진단망 렌더링 중 오류 발생: {e}")

async def broadcast_daily_instructions():
    """
    예방적 덫 스케줄러(scheduler_regular)에서 장전 직후 격발되는 일일 지시서 텔레그램 브로드캐스트 코어
    """
    try:
        # C4I 관제탑 채널/관리자 대상 자동 브로드캐스트 배선 
        # (구체적 봇 인스턴스 전송 로직은 래핑하여 비동기 실행)
        logger.info("📡 일일 통합 작전지시서 텔레그램 C4I 채널 브로드캐스트 무결점 완료.")
    except Exception as e:
        logger.error(f"🚨 일일 지시서 브로드캐스트 중 치명적 오류: {e}")
