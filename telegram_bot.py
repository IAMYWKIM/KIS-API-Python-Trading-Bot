"""
Created on 2025-07-01
텔레그램 C4I 관제탑 라우팅 코어 (V71.00 무결점 방탄 아키텍처)
"""

import asyncio
import logging
from datetime import datetime
# NEW: [제3헌법, 제10경고] pytz 영구 적출 및 ZoneInfo 100% 락온
from zoneinfo import ZoneInfo

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

import config
# 하위 모듈 라우팅 배선
import telegram_view
import telegram_avwap_console
import telegram_states
import plugin_updater

# 로깅 설정
logger = logging.getLogger(__name__)

# NEW: [제3헌법] 전역 타임존 단일 소스 락온
EST_TZ = ZoneInfo('America/New_York')

async def check_redzone_lockon() -> bool:
    """
    [치명적 경고 9] 장중 업데이트 레드존(14:55~16:10 EST) 락온 판별기
    """
    # NEW: [제16경고] 스코프 리프트 (UnboundLocalError 원천 봉쇄)
    now_est = None
    hour = 0
    minute = 0
    is_redzone = False
    
    try:
        now_est = datetime.now(EST_TZ)
        hour = now_est.hour
        minute = now_est.minute
        
        # 14:55 ~ 16:10 EST 구간 필터링
        if (hour == 14 and minute >= 55) or (hour == 15) or (hour == 16 and minute <= 10):
            is_redzone = True
            
    except Exception as e:
        logger.error(f"🚨 레드존 연산 중 오류 발생: {e}. 안전을 위해 락온을 가동합니다.")
        is_redzone = True
        
    return is_redzone

# ==========================================
# 📡 10대 주요 명령어 라우팅 핸들러
# ==========================================

async def cmd_update(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """🚀 시스템 자가 업데이트 (레드존 락온 연동)"""
    # NEW: [제16경고] 스코프 리프트
    is_locked = False
    
    try:
        is_locked = await check_redzone_lockon()
        if is_locked:
            logger.warning("🚨 레드존(14:55~16:10 EST) 업데이트 차단 방어막 가동.")
            await update.message.reply_text("🚫 <b>[레드존 락온]</b> 장마감 VWAP 정산이 치열한 구간(14:55~16:10 EST)입니다. 런타임 붕괴를 막기 위해 시스템 업데이트가 원천 차단됩니다.", parse_mode="HTML")
            return
            
        await update.message.reply_text("🚀 시스템 자가 업데이트를 시작합니다. 깃허브 강제 동기화 후 데몬이 자폭(하드 킬) 및 재가동됩니다.")
        
        # NEW: [치명적 경고 15] 플러그인 업데이터로 위임 (내부적으로 os._exit(0) 격발 보장)
        await plugin_updater.trigger_update()
        
    except Exception as e:
        logger.error(f"🚨 업데이트 라우팅 중 오류 발생: {e}")

async def cmd_sync(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """📜 통합 지시서 조회"""
    await telegram_view.render_sync_instruction(update, context)

async def cmd_record(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """📊 장부 동기화 및 조회"""
    await telegram_view.render_ledger_record(update, context)

async def cmd_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """🏆 졸업 명예의 전당"""
    await telegram_view.render_graduation_history(update, context)

async def cmd_settlement(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """⚙️ 코어스위칭/전술설정"""
    await telegram_states.start_settlement_config(update, context)

async def cmd_seed(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """💵 개별 시드머니 관리"""
    await telegram_states.start_seed_management(update, context)

async def cmd_ticker(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """🔄 운용 종목 선택"""
    await telegram_states.start_ticker_selection(update, context)

async def cmd_mode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """🎯 상방 스나이퍼 ON/OFF"""
    await telegram_states.toggle_sniper_mode(update, context)

async def cmd_version(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """🛠️ 버전 및 업데이트 내역"""
    await telegram_view.render_version_history(update, context)

async def cmd_avwap(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """🔫 실시간 모멘텀 레이더 관제탑"""
    # NEW: [치명적 경고 11] AVWAP 레이더 전용 모듈로 위임 (숏 기능 완전 소각 완비)
    await telegram_avwap_console.render_radar(update, context)

async def cmd_log(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """🔍 실시간 에러 원격 추출 진단망"""
    await telegram_view.render_system_logs(update, context)

async def cmd_reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """🔓 비상 해제 메뉴 (락/리버스)"""
    await telegram_states.show_reset_menu(update, context)

# ==========================================
# ⚙️ 텔레그램 데몬 구동 코어
# ==========================================

async def start_polling():
    """텔레그램 봇 비동기 폴링 시작점 (main.py 단일 이벤트 루프 배선용)"""
    # NEW: [제16경고] 스코프 리프트
    bot_token = ""
    app = None
    
    try:
        # 데이터베이스 I/O 병목을 피하기 위해 캐시에서 다이렉트 토큰 추출
        bot_token = config._cache['config'].get('telegram_token', '')
        if not bot_token:
            logger.critical("🚨 텔레그램 봇 토큰이 환경설정에 존재하지 않습니다. C4I 관제탑 구동을 셧다운합니다.")
            return

        app = Application.builder().token(bot_token).build()

        logger.info("🔹 10대 주요 명령어 라우팅 배선을 시작합니다.")
        app.add_handler(CommandHandler("sync", cmd_sync))
        app.add_handler(CommandHandler("record", cmd_record))
        app.add_handler(CommandHandler("history", cmd_history))
        app.add_handler(CommandHandler("settlement", cmd_settlement))
        app.add_handler(CommandHandler("seed", cmd_seed))
        app.add_handler(CommandHandler("ticker", cmd_ticker))
        app.add_handler(CommandHandler("mode", cmd_mode))
        app.add_handler(CommandHandler("version", cmd_version))
        app.add_handler(CommandHandler("avwap", cmd_avwap))
        app.add_handler(CommandHandler("log", cmd_log))
        app.add_handler(CommandHandler("reset", cmd_reset))
        app.add_handler(CommandHandler("update", cmd_update))

        logger.info("🚀 텔레그램 C4I 관제탑 비동기 폴링 파이프라인 가동 완료.")
        
        # NEW: [제1헌법] 파이썬-텔레그램-봇 v20 비동기 래핑 (메인 루프 공유)
        await app.initialize()
        await app.start()
        # drop_pending_updates=True 로 과거에 쌓인 유령 콜백/명령어 소각
        await app.updater.start_polling(drop_pending_updates=True)
        
    except Exception as e:
        logger.error(f"🚨 텔레그램 데몬 구동 중 치명적 오류 발생: {e}", exc_info=True)
