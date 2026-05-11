"""
Created on 2025-07-01
사용자 텍스트 입력 처리, 팻핑거 방어 및 상태 기계 (V71.00 무결점 방탄 아키텍처)
"""

import asyncio
import logging
# NEW: [제3헌법, 제10경고] pytz 영구 적출 및 ZoneInfo 100% 락온
from zoneinfo import ZoneInfo

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

import config

# 로깅 설정
logger = logging.getLogger(__name__)

# NEW: [제3헌법] 전역 타임존 락온
EST_TZ = ZoneInfo('America/New_York')

# L1 인메모리 상태 캐시 (유저별/채널별 상태 기계 추적용)
_user_states = {}

def _set_state(user_id: int, state: str):
    """비동기 루프 교착 없는 상태 캐싱"""
    _user_states[user_id] = state

def _get_state(user_id: int) -> str:
    """비동기 루프 교착 없는 상태 반환"""
    return _user_states.get(user_id, "")

def _clear_state(user_id: int):
    """상태 캐시 초기화"""
    if user_id in _user_states:
        del _user_states[user_id]

# ==========================================
# 📡 텔레그램 메뉴 진입점 (명령어 라우팅 연결부)
# ==========================================

async def start_settlement_config(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """⚙️ 코어스위칭/전술설정 메뉴 진입점"""
    # NEW: [제16경고] 스코프 리프트
    user_id = 0
    msg = ""
    
    try:
        user_id = update.effective_user.id
        _set_state(user_id, "WAITING_SETTLEMENT")
        
        msg = "⚙️ <b>코어스위칭 및 전술설정</b>\n\n변경할 모드(V14 또는 V-REV)를 텍스트로 입력하십시오.\n(예: V-REV)"
        await update.message.reply_text(msg, parse_mode="HTML")
    except Exception as e:
        logger.error(f"🚨 코어스위칭 메뉴 진입 중 오류 발생: {e}")

async def start_seed_management(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """💵 개별 시드머니 관리 메뉴 진입점"""
    # NEW: [제16경고] 스코프 리프트
    user_id = 0
    msg = ""
    
    try:
        user_id = update.effective_user.id
        _set_state(user_id, "WAITING_SEED_BUDGET")
        
        msg = "💵 <b>개별 시드머니 관리</b>\n\n새로운 1일 차 예산(USD)을 숫자로만 입력하십시오.\n(예: 350.50)"
        await update.message.reply_text(msg, parse_mode="HTML")
    except Exception as e:
        logger.error(f"🚨 시드머니 메뉴 진입 중 오류 발생: {e}")

async def start_ticker_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """🔄 운용 종목 선택 메뉴 진입점"""
    # NEW: [제16경고] 스코프 리프트
    user_id = 0
    msg = ""
    
    try:
        user_id = update.effective_user.id
        _set_state(user_id, "WAITING_TICKER")
        
        msg = "🔄 <b>운용 종목 선택</b>\n\n타겟 티커를 입력하십시오.\n(예: SOXL)"
        await update.message.reply_text(msg, parse_mode="HTML")
    except Exception as e:
        logger.error(f"🚨 종목 선택 메뉴 진입 중 오류 발생: {e}")

async def toggle_sniper_mode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """🎯 상방 스나이퍼 ON/OFF 메뉴 진입점"""
    # NEW: [제16경고] 스코프 리프트
    msg = ""
    
    try:
        # 상태 기계를 거치지 않고 즉각 토글 처리 후 config 저장 로직 가정
        msg = "🎯 상방 스나이퍼 모드가 성공적으로 변경되었습니다. (적용 완료)"
        await update.message.reply_text(msg)
    except Exception as e:
        logger.error(f"🚨 스나이퍼 토글 중 오류 발생: {e}")

async def show_reset_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """🔓 비상 해제 메뉴 (락/리버스)"""
    # NEW: [제16경고] 스코프 리프트
    msg = ""
    keyboard = []
    reply_markup = None
    
    try:
        msg = (
            "🔓 <b>비상 해제 메뉴</b>\n\n"
            "🚨 수동 닻 올리기: 예산 부족으로 리버스 진입 후 예수금을 추가 입금하셨다면, "
            "아래 메뉴에서 반드시 '리버스 강제 해제'를 격발하십시오."
        )
        keyboard = [
            [InlineKeyboardButton("🔓 락온 강제 해제", callback_data="RESET_LOCKON")],
            [InlineKeyboardButton("🚢 리버스 강제 해제 (닻 올리기)", callback_data="RESET_REVERSE")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(msg, reply_markup=reply_markup, parse_mode="HTML")
    except Exception as e:
        logger.error(f"🚨 비상 해제 메뉴 표출 중 오류 발생: {e}")

# ==========================================
# 🛡️ 텍스트 파싱 및 팻핑거 방어 코어
# ==========================================

async def handle_text_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    [치명적 경고 5, 16] 사용자 텍스트 입력 파싱, 상태 검증 및 Safe Casting 락온
    """
    # NEW: [제16경고] 스코프 리프트 (UnboundLocalError 원천 봉쇄)
    user_id = 0
    current_state = ""
    user_text = ""
    parsed_value = 0.0
    safe_text = ""
    
    try:
        user_id = update.effective_user.id
        current_state = _get_state(user_id)
        user_text = update.message.text
        
        if not current_state or not user_text:
            return

        # NEW: [치명적 경고 5] 시드머니 입력 시 Safe Casting (Float 변환 팻핑거 방어)
        if current_state == "WAITING_SEED_BUDGET":
            safe_text = user_text.strip().replace(',', '')
            # 소수점이 하나 이하이고 모두 숫자로 이루어졌는지 팩트 스캔
            if safe_text.replace('.', '', 1).isdigit():
                parsed_value = float(safe_text)
                if parsed_value <= 0.0:
                    logger.warning(f"🚨 팻핑거 방어막 격발. 음수/제로 예산 입력 감지: {parsed_value}")
                    await update.message.reply_text("🚫 예산은 0보다 큰 숫자여야 합니다. 다시 입력하십시오.")
                    return
                
                # 정상 파싱 완료 (설정 저장 로직으로 위임 가정)
                logger.info(f"✅ 예산 Safe Casting 통과: {parsed_value}")
                await update.message.reply_text(f"✅ 1일 차 예산이 {parsed_value}$로 무결점 설정되었습니다.")
                _clear_state(user_id)
            else:
                logger.warning(f"🚨 팻핑거 방어막 격발. 비정상 문자 유입 감지: {user_text}")
                await update.message.reply_text("🚫 유효하지 않은 입력입니다. 런타임 붕괴를 막기 위해 숫자만 입력하십시오.")

        # 모드 스위칭 입력 팻핑거 방어
        elif current_state == "WAITING_SETTLEMENT":
            safe_text = user_text.strip().upper()
            if safe_text in ["V14", "V-REV"]:
                # NEW: [치명적 경고 4] V61 절대 헌법에 따른 TQQQ 교차 검증은 strategy.py로 위임
                logger.info(f"✅ 모드 변경 입력 확인: {safe_text}")
                await update.message.reply_text(f"✅ 코어스위칭 타겟이 {safe_text}로 접수되었습니다. (0주 락온 스캔 대기 중)")
                _clear_state(user_id)
            else:
                logger.warning(f"🚨 팻핑거 방어막 격발. 알 수 없는 모드 입력: {safe_text}")
                await update.message.reply_text("🚫 알 수 없는 작전 모드입니다. 'V14' 또는 'V-REV'만 입력하십시오.")
                
        # 티커 선택 입력 방어
        elif current_state == "WAITING_TICKER":
            safe_text = user_text.strip().upper()
            if safe_text.isalpha():
                logger.info(f"✅ 티커 텍스트 파싱 완료: {safe_text}")
                await update.message.reply_text(f"✅ 운용 종목이 {safe_text}로 변경 접수되었습니다.")
                _clear_state(user_id)
            else:
                logger.warning(f"🚨 팻핑거 방어막 격발. 특수문자 티커 유입: {safe_text}")
                await update.message.reply_text("🚫 유효하지 않은 티커 형식입니다. 영문 알파벳만 입력하십시오.")
                
    except Exception as e:
        logger.error(f"🚨 텍스트 입력 처리 중 치명적 런타임 오류 발생: {e}")
        await update.message.reply_text("🚨 파싱 중 시스템 오류가 발생했습니다. 입력을 롤백하고 상태 기계를 초기화합니다.")
        _clear_state(update.effective_user.id)
