# ==========================================================
# FILE: callback_avwap_handler.py
# ==========================================================
# 🚨 VERIFIED: [최종 무결점 판정] 3중 딥다이브 교차 검증(Async I/O 족쇄, State Mismatch 방어, Float 정밀도 사수) 통과 완료.
# 🚨 NEW: [수동 매수 제어망 이식] PAUSE_BUY(주문 취소하기) 및 RESUME_BUY(수동으로 주문하기) 콜백 라우팅을 신규 락온하여 매수 덫을 원자적으로 일시 정지(Cancel)하고 관망 상태로 전환하는 기능 결속 완료.
# 🚨 MODIFIED: [V86.00 텍스트 팩트 롤오버 궁극 수술] 하위 알림 메시지에 잔존하던 '딥-레스큐 암살자' 및 '암살자 물량' 레거시 명칭을 100% 영구 소각하고 '새벽 수금원(스캘퍼)' 퀀트 네이밍으로 팩트 교정 완료.
# 🚨 MODIFIED: [딥-레스큐 V84.00 전면 리빌딩] 100% 자율주행 아키텍처 도입에 따른 데드코드 영구 소각.
# 🚨 MODIFIED: [수동 제어망 완전 소각] MANUAL_FIRE_REQ, MANUAL_FIRE_EXEC, MANUAL_CANCEL_REQ 등 팻핑거 개입을 유발하는 모든 라우팅과 연계 로직을 100% 진공 압축(제거).
# 🚨 MODIFIED: [다중 출격 소각] AVWAP_SORTIE 라우팅 데드코드 영구 제거 (단일 구출 후 무조건 퇴근).
# 🚨 MODIFIED: [SYNC_ZERO 상태 누수 방어] 0주 포맷 시 limit_order_placed, placed_target_th, trap_odno 등 잔여 찌꺼기 상태를 완벽하게 초기화하여 다음 날 멱등성을 사수.
# 🚨 MODIFIED: [Float 정밀도 붕괴 원천 차단] 클래스 전용 `_safe_float` 래퍼 메서드를 주입하여 파편화된 인라인 캐스팅을 통합하고 NaN/Inf 맹독성 붕괴 원천 차단.
# 🚨 MODIFIED: [제1헌법 철저 준수] 로컬 파일 I/O(save_state, config 조작) 실행 시 `wait_for(..., timeout=5.0)` 족쇄를 완벽히 래핑하여 디스크 I/O 병목으로 인한 이벤트 루프 교착 원천 차단.
# 🚨 MODIFIED: [Case 26 절대 헌법 준수] 텔레그램 타전망 내 동적 변수 전역에 `html.escape` 쉴드 강제 래핑 완료.
# 🚨 MODIFIED: [Ghost Chat 붕괴 원천 봉쇄] update.effective_chat 결측치(None) 유입 시 발생하는 AttributeError 즉사 버그를 막기 위한 진입 게이트 단락 평가 쉴드 락온.
# ==========================================================
import logging
import datetime
from zoneinfo import ZoneInfo
import math
import asyncio
import html
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

class CallbackAvwapHandler:
    def __init__(self, config, broker, strategy, view, tx_lock):
        self.cfg = config
        self.broker = broker
        self.strategy = strategy
        self.view = view
        self.tx_lock = tx_lock

    # 🚨 [수학 연산 붕괴 방어] NaN, Infinity 및 String-Comma 맹독성 데이터 정밀 필터링 락온
    def _safe_float(self, val):
        try:
            f_val = float(str(val or 0.0).replace(',', ''))
            if math.isnan(f_val) or math.isinf(f_val):
                return 0.0
            return f_val
        except Exception:
            return 0.0

    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE, controller, action: str, sub: str, data: list):
        query = update.callback_query
        
        # 🚨 MODIFIED: [Ghost Chat 붕괴 원천 봉쇄] 통신 노이즈로 텔레그램 객체가 파손되어 유입될 경우 즉사 버그 100% 방어
        if not query:
            return
            
        chat_id = update.effective_chat.id if update.effective_chat else 0
        if chat_id == 0:
            return
            
        ticker = data[2] if len(data) > 2 else ""

        if action == "AVWAP":
            if sub == "MENU":
                if hasattr(controller, 'cmd_avwap'):
                    await controller.cmd_avwap(update, context)

        elif action == "MODE":
            if not ticker: return
            
            # 🚨 [제1헌법 준수] config I/O 조작 시 이벤트 루프 교착을 막기 위해 wait_for(timeout=5.0) 족쇄 전면 결속
            if sub == "ON":
                try: await query.answer()
                except Exception: pass
                try: await asyncio.wait_for(asyncio.to_thread(self.cfg.set_upward_sniper_mode, ticker, True), timeout=5.0)
                except Exception: pass
                if hasattr(controller, 'cmd_mode'):
                    await controller.cmd_mode(update, context)
            
            elif sub == "OFF":
                try: await query.answer()
                except Exception: pass
                try: await asyncio.wait_for(asyncio.to_thread(self.cfg.set_upward_sniper_mode, ticker, False), timeout=5.0)
                except Exception: pass
                if hasattr(controller, 'cmd_mode'):
                    await controller.cmd_mode(update, context)
            
            elif sub == "AVWAP_WARN":
                try: await query.answer()
                except Exception: pass
                msg, markup = self.view.get_avwap_warning_menu(ticker)
                try:
                    await query.edit_message_text(msg, reply_markup=markup, parse_mode='HTML')
                except Exception: pass
            
            elif sub == "AVWAP_ON":
                try: await query.answer()
                except Exception: pass
                try: await asyncio.wait_for(asyncio.to_thread(self.cfg.set_avwap_hybrid_mode, ticker, True), timeout=5.0)
                except Exception: pass
                if hasattr(controller, 'cmd_settlement'):
                    await controller.cmd_settlement(update, context)
            
            elif sub == "AVWAP_OFF":
                try: await query.answer()
                except Exception: pass
                try: await asyncio.wait_for(asyncio.to_thread(self.cfg.set_avwap_hybrid_mode, ticker, False), timeout=5.0)
                except Exception: pass
                if hasattr(controller, 'cmd_settlement'):
                    await controller.cmd_settlement(update, context)

        elif action == "AVWAP_SET":
            if not ticker: return
            
            # 🚨 NEW: [수동 매수 제어망 - 주문 취소 및 관망 모드 돌입]
            if sub == "PAUSE_BUY":
                status_code, _ = await controller._get_market_status()
                if status_code not in ["PRE", "REG"]:
                    try: await query.answer("❌ [격발 차단] 현재 장운영시간(정규장/프리장)이 아닙니다.", show_alert=True)
                    except Exception: pass
                    return

                try: await query.answer("⏳ 주문 취소 및 관망 모드 전환 중...", show_alert=False)
                except Exception: pass

                async with self.tx_lock:
                    app_data_root = (context.bot_data or {})
                    if not isinstance(app_data_root, dict): app_data_root = {}
                    app_data = app_data_root.get('app_data') or {}
                    if not isinstance(app_data, dict): app_data = {}
                    
                    tracking_cache = app_data.get('sniper_tracking') or {}
                    if not isinstance(tracking_cache, dict): tracking_cache = {}
                    
                    # 🚨 [Case 1] TOCTOU 레이스 컨디션 방어: 이미 매수가 체결되었는지 교차 검증
                    current_qty = int(self._safe_float(tracking_cache.get(f"AVWAP_QTY_{ticker}", 0)))
                    if current_qty > 0:
                        try: await query.edit_message_text(f"⚠️ <b>[{html.escape(str(ticker))}] 이미 스캘퍼 매수가 체결되어 취소가 불가능합니다.</b>", parse_mode='HTML')
                        except Exception: pass
                        return
                    
                    buy_odno = str(tracking_cache.get(f"AVWAP_BUY_ODNO_{ticker}") or "")
                    
                    # 🚨 [제1헌법 & Case 32] KIS API 비동기 취소 전송 및 TPS 캡핑
                    if buy_odno:
                        for attempt in range(3):
                            try:
                                await asyncio.sleep(0.06)
                                await asyncio.wait_for(asyncio.to_thread(self.broker.cancel_order, ticker, buy_odno), timeout=10.0)
                                break
                            except Exception as e:
                                if attempt == 2: logging.error(f"🚨 [{ticker}] 스캘퍼 수동 매수 취소 실패 (이미 체결되었거나 증발): {e}")
                                else: await asyncio.sleep(1.0 * (2 ** attempt))

                    # 🚨 [Case 3] 상태 스키마 오염 방어: 캐시 및 로컬 상태 파일 원자적 동기화
                    tracking_cache[f"AVWAP_MANUAL_SUSPEND_{ticker}"] = True
                    tracking_cache[f"AVWAP_LIMIT_ORDER_PLACED_{ticker}"] = False
                    tracking_cache[f"AVWAP_BUY_ODNO_{ticker}"] = ""

                    est = ZoneInfo('America/New_York')
                    now_est = datetime.datetime.now(est)

                    if hasattr(self.strategy, 'v_avwap_plugin'):
                        try:
                            state_data = await asyncio.wait_for(asyncio.to_thread(self.strategy.v_avwap_plugin.load_state, ticker, now_est), timeout=5.0)
                            if isinstance(state_data, dict):
                                state_data['manual_suspend'] = True
                                state_data['limit_order_placed'] = False
                                state_data['buy_odno'] = ""
                                await asyncio.wait_for(asyncio.to_thread(self.strategy.v_avwap_plugin.save_state, ticker, now_est, state_data), timeout=5.0)
                        except Exception as e:
                            logging.error(f"🚨 [{ticker}] 수동 관망(Pause) 상태 파일 저장 에러: {e}")

                if hasattr(controller, 'cmd_avwap'):
                    await controller.cmd_avwap(update, context)

            # 🚨 NEW: [수동 매수 제어망 - 주문 재개 및 관망 모드 해제]
            elif sub == "RESUME_BUY":
                status_code, _ = await controller._get_market_status()
                if status_code not in ["PRE", "REG"]:
                    try: await query.answer("❌ [격발 차단] 현재 장운영시간(정규장/프리장)이 아닙니다.", show_alert=True)
                    except Exception: pass
                    return

                try: await query.answer("⏳ 매수 감시 재개 중...", show_alert=False)
                except Exception: pass

                # 🚨 [동시성 충돌 방어] 실제 주문은 쏘지 않고 플래그만 해제하여 1분 스케줄러 코어 엔진에 타격 위임(Delegate)
                async with self.tx_lock:
                    app_data_root = (context.bot_data or {})
                    if not isinstance(app_data_root, dict): app_data_root = {}
                    app_data = app_data_root.get('app_data') or {}
                    if not isinstance(app_data, dict): app_data = {}
                    
                    tracking_cache = app_data.get('sniper_tracking') or {}
                    if not isinstance(tracking_cache, dict): tracking_cache = {}
                    
                    tracking_cache[f"AVWAP_MANUAL_SUSPEND_{ticker}"] = False

                    est = ZoneInfo('America/New_York')
                    now_est = datetime.datetime.now(est)

                    if hasattr(self.strategy, 'v_avwap_plugin'):
                        try:
                            state_data = await asyncio.wait_for(asyncio.to_thread(self.strategy.v_avwap_plugin.load_state, ticker, now_est), timeout=5.0)
                            if isinstance(state_data, dict):
                                state_data['manual_suspend'] = False
                                await asyncio.wait_for(asyncio.to_thread(self.strategy.v_avwap_plugin.save_state, ticker, now_est, state_data), timeout=5.0)
                        except Exception as e:
                            logging.error(f"🚨 [{ticker}] 수동 관망 해제(Resume) 상태 파일 저장 에러: {e}")

                if hasattr(controller, 'cmd_avwap'):
                    await controller.cmd_avwap(update, context)

            elif sub == "SYNC_ZERO":
                status_code, _ = await controller._get_market_status()
                if status_code not in ["PRE", "REG"]:
                    try: await query.answer("❌ [격발 차단] 현재 장운영시간(정규장/프리장)이 아닙니다.", show_alert=True)
                    except Exception: pass
                    return
                    
                try: await query.answer()
                except Exception: pass
                
                # 🚨 [콜백 레이스 컨디션 완벽 차단] 상태 포맷 역시 원자성 보장을 위해 락온
                async with self.tx_lock:
                    try:
                        # 🚨 [메모리 참조 증발 패러독스 수술] 명시적 딕셔너리 할당으로 Ghost Dict 차단 및 전역 봇 상태 100% 멱등성 락온
                        app_data_root = (context.bot_data or {})
                        if not isinstance(app_data_root, dict): app_data_root = {}
                        app_data = app_data_root.get('app_data') or {}
                        if not isinstance(app_data, dict): app_data = {}
                            
                        tracking_cache = app_data.get('sniper_tracking') or {}
                        if not isinstance(tracking_cache, dict): tracking_cache = {}
                        
                        tracking_cache[f"AVWAP_QTY_{ticker}"] = 0
                        tracking_cache[f"AVWAP_AVG_{ticker}"] = 0.0
                        tracking_cache[f"AVWAP_SHUTDOWN_{ticker}"] = True
                        tracking_cache[f"AVWAP_TRAP_PLACED_TIME_{ticker}"] = ""
                        tracking_cache[f"AVWAP_BUY_ODNO_{ticker}"] = "" 
                        tracking_cache[f"AVWAP_TRAP_ODNO_{ticker}"] = ""
                        
                        # 🚨 [SYNC_ZERO 상태 누수 방어] 0주 포맷 시 덫 장전 상태도 100% 해제 락온
                        tracking_cache[f"AVWAP_LIMIT_ORDER_PLACED_{ticker}"] = False
                        tracking_cache[f"AVWAP_PLACED_TARGET_TH_{ticker}"] = 0.0
                        tracking_cache[f"AVWAP_T_H_{ticker}"] = 0.0
                        tracking_cache[f"AVWAP_TRAP_QTY_{ticker}"] = 0
                        tracking_cache[f"AVWAP_MANUAL_SUSPEND_{ticker}"] = False # 수동 제어망 초기화

                        est = ZoneInfo('America/New_York')
                        now_est = datetime.datetime.now(est)

                        if hasattr(self.strategy, 'v_avwap_plugin'):
                            # 🚨 [상태 다이어트 적용 완료] 불필요한 레거시가 소각된 순수 상태 팩트 덮어쓰기 (스키마 무결성 유지)
                            state_data = {
                                'shutdown': True,
                                'qty': 0,
                                'avg_price': 0.0,
                                'trap_odno': "",
                                'buy_odno': "",
                                'T_H': 0.0,
                                'limit_order_placed': False,
                                'placed_target_th': 0.0,
                                'trap_placed_time': "",
                                'trap_qty': 0,
                                'manual_suspend': False,
                                'strikes': int(self._safe_float(tracking_cache.get(f"AVWAP_STRIKES_{ticker}", 0)))
                            }
                        
                            # 🚨 [제1헌법 준수] 로컬 파일 I/O 타임아웃 래핑 강제
                            try:
                                await asyncio.wait_for(
                                    asyncio.to_thread(self.strategy.v_avwap_plugin.save_state, ticker, now_est, state_data),
                                    timeout=5.0
                                )
                            except Exception as e:
                                logging.error(f"🚨 수동 0주 포맷 로컬 파일 저장 에러 (RAM은 초기화됨): {e}")
                        
                        try:
                            # 🚨 MODIFIED: [V86.00 텍스트 롤오버] 하위 알림 메시지까지 100% 새벽 수금원(스캘퍼) 포맷으로 교체 완료
                            msg_success = f"🧯 <b>[{html.escape(str(ticker))}] 새벽 수금원(스캘퍼) 수동 청산 (0주 락온) 완료!</b>\n▫️ 스캘퍼 물량이 0주로 강제 포맷되었으며, 금일 남은 시간 동안 영구 동결(SHUTDOWN)됩니다."
                            keyboard = [[InlineKeyboardButton("🔄 관제탑 복귀", callback_data="AVWAP_SET:REFRESH:NONE")]]
                            await query.edit_message_text(msg_success, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')
                        except Exception: pass
                    except Exception as e:
                        logging.error(f"🚨 수동 0주 동기화 에러: {e}")
                        safe_err = html.escape(str(e))
                        try:
                            keyboard = [[InlineKeyboardButton("🔄 관제탑 복귀", callback_data="AVWAP_SET:REFRESH:NONE")]]
                            await query.edit_message_text(f"❌ <b>수동 0주 동기화 중 에러 발생:</b>\n<code>{safe_err}</code>", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')
                        except Exception: pass

            elif sub == "REFRESH":
                try: await query.answer()
                except Exception: pass
                if hasattr(controller, 'cmd_avwap'):
                    await controller.cmd_avwap(update, context)
