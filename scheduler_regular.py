# ==========================================================
# FILE: scheduler_regular.py
# ==========================================================
# MODIFIED: [V53.06 전투 사령부 외부 통신 10초 타임아웃 및 폴백 방어막 이식]
# 🚨 [AI 에이전트(Copilot/Claude) 절대 주의 - 환각(Hallucination) 방어막]
# 제1헌법: queue_ledger.get_queue 등 모든 파일 I/O 및 락 점유 메서드는 무조건 asyncio.to_thread로 래핑하여 이벤트 루프 교착(Deadlock)을 원천 차단함.
# MODIFIED: [V44.47 이벤트 루프 데드락 영구 소각] 동기식 블로킹 호출 전면 비동기 래핑.
# 🚨 MODIFIED: [V54.02 깡통 스냅샷 붕괴 방어] V-REV 예방 덫 소각 시 생성되는 더미 스냅샷에 prev_c 및 is_zero_start 팩트 다이렉트 주입 락온
# 🚨 MODIFIED: [V-REV 데이터 기아 방어] 통신 장애로 0.0 폴백 시 루프 조기 탈출(continue) 무시 및 깡통 스냅샷 팩트 박제 락온.
# 🚨 NEW: [KIS VWAP 알고리즘 권한 위임 수술] V-REV 수동 덫 장전 경고문 및 바이패스 분기를 전면 소각. 17:05 KST 기상 시 산출된 단일 지시서를 KIS VWAP 예약 주문 및 LOC 예약 주문으로 즉각 전송하고 예약 주문 번호(ODNO)를 로컬 캐시에 영속화하는 라우팅 배선 100% 개통 완료.
# 🚨 MODIFIED: [V71.05 정규장 스케줄러 라이브 주문 런타임 붕괴 수술 및 시간 인젝션]
# - 17:05 KST에 실시간 주문(send_order)을 발송하여 전량 거절(Reject) 당하던 런타임 맹점 원천 차단.
# - 예약 주문(send_reservation_order)으로 100% 역배선(Rewiring) 완료.
# - 지시서의 start_time, end_time 파라미터를 다이렉트 인젝션하여 30분 압축 타임라인 락온.
# 🚨 MODIFIED: [V71.12 로컬 캐시 의존성 영구 소각 및 코어 압축]
# - KIS 실시간 팩트 스캔 엔진 도입에 따라, 파일 파편화를 유발하는 로컬 예약 캐시 영속화 보조 함수(_save_resv_odno_sync) 전면 적출.
# - 호출 루프 내 해당 비동기 배선 완벽 철거 및 코드 진공 압축 완료.
# 🚨 NEW: [V71.14 사일런트 스킵(Silent Skip) 맹점 원천 수술 및 관망 팩트 보고망 이식]
# - 예산 고갈 및 매도 타점 미도달로 전송할 덫(주문)이 0건일 때 봇이 조용히 침묵하던 UX 결함 해결.
# - 주문이 없을 경우 즉시 "💤 관망 모드 유지 (주문 0건)" 상태를 텔레그램으로 명시적 타전하도록 방어막 구축.
# ==========================================================
import logging
import datetime
from zoneinfo import ZoneInfo
import asyncio
import random

from scheduler_core import is_market_open, get_budget_allocation

async def scheduled_regular_trade(context):
    try:
        is_open = await asyncio.wait_for(asyncio.to_thread(is_market_open), timeout=10.0)
    except asyncio.TimeoutError:
        logging.error("⚠️ is_market_open 달력 API 타임아웃. 평일이므로 강제 개장 처리합니다.")
        est = ZoneInfo('America/New_York')
        is_open = datetime.datetime.now(est).weekday() < 5

    if not is_open:
        return
    
    app_data = context.job.data
    cfg, broker, strategy, tx_lock = app_data['cfg'], app_data['broker'], app_data['strategy'], app_data['tx_lock']
    
    if tx_lock is None:
        logging.warning("⚠️ [regular_trade] tx_lock 미초기화. 이번 사이클 스킵.")
        await context.bot.send_message(chat_id=context.job.chat_id, text="⚠️ <b>[시스템 경고]</b> tx_lock 미초기화로 정규장 주문을 1회 스킵합니다.", parse_mode='HTML')
        return
    
    jitter_seconds = random.randint(0, 180)

    await context.bot.send_message(
        chat_id=context.job.chat_id, 
        text=f"🌃 <b>[04:05 EST] 통합 주문 장전 및 스냅샷 박제!</b>\n"
             f"🛡️ 서버 접속 부하 방지를 위해 <b>{jitter_seconds}초</b> 대기 후 안전하게 주문 전송을 시도합니다.", 
        parse_mode='HTML'
    )

    await asyncio.sleep(jitter_seconds)

    MAX_RETRIES = 15
    RETRY_DELAY = 60

    async def _do_regular_trade():
        est = ZoneInfo('America/New_York')
        _now_est = datetime.datetime.now(est)
        today_str_est = _now_est.strftime("%Y-%m-%d")
        
        async with tx_lock:
            try:
                cash, holdings = await asyncio.wait_for(asyncio.to_thread(broker.get_account_balance), timeout=10.0)
            except asyncio.TimeoutError:
                logging.warning("⚠️ [regular_trade] 잔고 조회 타임아웃 (10초).")
                return False, "잔고 조회 타임아웃"
            except Exception as e:
                return False, f"잔고 조회 오류: {e}"
            
            if holdings is None:
                return False, "❌ 계좌 정보를 불러오지 못했습니다."
            
            safe_holdings = holdings if isinstance(holdings, dict) else {}

            active_tickers_list = await asyncio.to_thread(cfg.get_active_tickers)
            sorted_tickers, allocated_cash = await asyncio.to_thread(get_budget_allocation, cash, active_tickers_list, cfg)
            
            plans = {}
            msgs = {t: "" for t in sorted_tickers}
            all_success_map = {t: True for t in sorted_tickers}

            for t in sorted_tickers:
                is_locked = await asyncio.to_thread(cfg.check_lock, t, "REG")
                if is_locked:
                    skip_msg = (
                        f"⚠️ <b>[{t}] REG 잠금 미해제 — 주문 스킵</b>\n"
                        f"▫️ 전날 REG 잠금이 자정 초기화 시 해제되지 않아 오늘 04:05 EST 주문 루프에서 제외되었습니다.\n"
                        f"▫️ 수동으로 잠금 해제 후 상태를 확인하십시오."
                    )
                    await context.bot.send_message(context.job.chat_id, skip_msg, parse_mode='HTML')
                    continue
                
                h = safe_holdings.get(t) or {}
                safe_avg = float(h.get('avg') or 0.0)
                safe_qty = int(float(h.get('qty') or 0))

                curr_p = 0.0
                prev_c = 0.0
                for _api_retry in range(3):
                    try:
                        curr_p_val = await asyncio.wait_for(asyncio.to_thread(broker.get_current_price, t), timeout=10.0)
                        curr_p = float(curr_p_val or 0.0)
                    except Exception:
                        curr_p = 0.0
                        
                    try:
                        prev_c_val = await asyncio.wait_for(asyncio.to_thread(broker.get_previous_close, t), timeout=10.0)
                        prev_c = float(prev_c_val or 0.0)
                    except Exception:
                        prev_c = 0.0
                        
                    if curr_p > 0 and prev_c > 0:
                        break
                    await asyncio.sleep(2.0)

                if curr_p <= 0 or prev_c <= 0:
                    msgs[t] += (
                        f"🚨 <b>[{t}] 전일 종가/현재가 API 3회 결측 감지!</b>\n"
                        f"▫️ 0.0 폴백 상태이나 깡통 스냅샷(0.0) 박제를 위해 런타임을 강제 진행합니다.\n"
                    )

                try:
                    ma_5day_val = await asyncio.wait_for(asyncio.to_thread(broker.get_5day_ma, t), timeout=10.0)
                    ma_5day = float(ma_5day_val or 0.0)
                except Exception:
                    ma_5day = 0.0
                
                # 🚨 MODIFIED: [KIS VWAP 알고리즘 대통합] V-REV 및 VWAP 수동/우회 처리 전면 소각 및 단일 통짜 플랜 로드 락온
                plan = await asyncio.to_thread(
                    strategy.get_plan,
                    t, curr_p, safe_avg, safe_qty, prev_c, ma_5day=ma_5day, market_type="REG", available_cash=allocated_cash.get(t, 0.0), is_snapshot_mode=True
                )
                
                plans[t] = plan

            for t in sorted_tickers:
                if t not in plans: continue
                target_orders = plans[t].get('core_orders', plans[t].get('orders', []))
                target_bonus = plans[t].get('bonus_orders', [])
                
                # 🚨 NEW: [V71.14 사일런트 스킵 맹점 원천 수술] 주문 0건 시 관망 팩트 텔레그램 타전망 이식
                if not target_orders and not target_bonus:
                    msg_skip = f"💤 <b>[{t}] 관망 모드 유지 (주문 0건)</b>\n▫️ 가용 예산이 모두 소진되었고 장전할 매도 덫이 없어 금일 정규장은 시스템 관망합니다."
                    await context.bot.send_message(chat_id=context.job.chat_id, text=msg_skip, parse_mode='HTML')
                    continue
                
                is_rev = plans[t].get('is_reverse', False)
                msgs[t] += f"🔄 <b>[{t}] 리버스(VWAP) 예약 덫 장전 완료</b>\n" if is_rev else f"💎 <b>[{t}] 정규장(LOC/VWAP) 예약 덫 장전 완료</b>\n"

                for o in target_orders:
                    # 🚨 [라우팅 수술] send_order -> send_reservation_order 역배선 및 시간 주입
                    res = await asyncio.to_thread(
                        broker.send_reservation_order, 
                        t, o['side'], o['qty'], o['price'], o['type'],
                        start_time=o.get('start_time'), end_time=o.get('end_time')
                    )
                    is_success = res.get('rt_cd') == '0'
                    if not is_success: all_success_map[t] = False

                    # 🚨 [V71.12 로컬 캐시 의존성 영구 소각] _save_resv_odno_sync 호출부 전면 적출 완료.
                    err_msg = res.get('msg1', '오류')
                    status_icon = '✅' if is_success else f'❌({err_msg})'
                    msgs[t] += f"└ 1차 필수: {o['desc']} {o['qty']}주 (${o['price']}): {status_icon}\n"
                    await asyncio.sleep(0.2)
                    
            for t in sorted_tickers:
                if t not in plans: continue
                target_bonus = plans[t].get('bonus_orders', [])
                if not target_bonus: continue
                
                for o in target_bonus:
                    # 🚨 [라우팅 수술] send_order -> send_reservation_order 역배선 및 시간 주입
                    res = await asyncio.to_thread(
                        broker.send_reservation_order, 
                        t, o['side'], o['qty'], o['price'], o['type'],
                        start_time=o.get('start_time'), end_time=o.get('end_time')
                    )
                    is_success = res.get('rt_cd') == '0'

                    # 🚨 [V71.12 로컬 캐시 의존성 영구 소각] _save_resv_odno_sync 호출부 전면 적출 완료.
                    err_msg = res.get('msg1', '잔금패스')
                    status_icon = '✅' if is_success else f'❌({err_msg})'
                    msgs[t] += f"└ 2차 보너스: {o['desc']} {o['qty']}주 (${o['price']}): {status_icon}\n"
                    await asyncio.sleep(0.2) 

            for t in sorted_tickers:
                if t not in plans: continue
                target_orders = plans[t].get('core_orders', plans[t].get('orders', []))
                target_bonus = plans[t].get('bonus_orders', [])
                if not target_orders and not target_bonus: continue
                
                if all_success_map[t] and len(target_orders) > 0:
                    await asyncio.to_thread(cfg.set_lock, t, "REG")
                    msgs[t] += "\n🔒 <b>필수 예약 덫 정상 전송 완료 (잠금 설정됨)</b>"
                elif not all_success_map[t] and len(target_orders) > 0:
                    msgs[t] += "\n⚠️ <b>일부 예약 덫 장전 실패 (매매 잠금 보류)</b>"
                elif len(target_bonus) > 0:
                    await asyncio.to_thread(cfg.set_lock, t, "REG")
                    msgs[t] += "\n🔒 <b>보너스 예약 덫만 전송 완료 (잠금 설정됨)</b>"
                    
                await context.bot.send_message(chat_id=context.job.chat_id, text=msgs[t], parse_mode='HTML')

            return True, "SUCCESS"

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            success, fail_reason = await asyncio.wait_for(_do_regular_trade(), timeout=300.0)
            if success:
                if attempt > 1:
                    await context.bot.send_message(chat_id=context.job.chat_id, text=f"✅ <b>[통신 복구] {attempt}번째 재시도 끝에 예약 덫 장전을 완수했습니다!</b>", parse_mode='HTML')
                return 
        except Exception as e:
            logging.error(f"정규장 예약 덫 전송 에러 ({attempt}/{MAX_RETRIES}): {e}", exc_info=True)
            if attempt == 1:
                await context.bot.send_message(
                    chat_id=context.job.chat_id, 
                    text=f"⚠️ <b>[API 통신 지연 감지]</b>\n한투 서버 불안정. 1분 뒤 재시도합니다! 🛡️\n<code>사유: {type(e).__name__}: {e}</code>", 
                    parse_mode='HTML'
                )
        else:
            logging.warning(f"정규장 예약 덫 조건 미충족 ({attempt}/{MAX_RETRIES}): {fail_reason}")
            if attempt == 1:
                 await context.bot.send_message(
                    chat_id=context.job.chat_id, 
                    text=f"⚠️ <b>[API 통신 지연 감지]</b>\n한투 서버 불안정. 1분 뒤 재시도합니다! 🛡️\n<code>사유: {fail_reason}</code>", 
                    parse_mode='HTML'
                )

        if attempt < MAX_RETRIES:
            if attempt != 1 and attempt % 5 == 0:
                await context.bot.send_message(chat_id=context.job.chat_id, text=f"⚠️ <b>[API 통신 지연 감지]</b>\n한투 서버 불안정. 1분 뒤 재시도합니다! 🛡️", parse_mode='HTML')
            await asyncio.sleep(RETRY_DELAY)

    await context.bot.send_message(chat_id=context.job.chat_id, text="🚨 <b>[긴급 에러] 통신 복구 최종 실패. 수동 점검 요망!</b>", parse_mode='HTML')
