# ==========================================================
# [strategy_v14.py] - 🌟 100% 통합 무결점 완성본 (Full Version) 🌟
# ⚠️ 오리지널 V14(무매4) & 클래식 리버스 모드 독립 플러그인
# MODIFIED: [V28.17 V14 오리지널 스냅샷 앵커 및 디커플링 이식]
# 1) V14 모드에도 save_daily_snapshot / load_daily_snapshot 함수 신설 이식.
# 2) get_plan() 진입 시 is_snapshot_mode 파라미터를 추가하여, 
#    텔레그램 지시서 조회 시 박제된 스냅샷을 우선 반환하도록 디커플링 배선 완비.
#    (이로써 장중 매수/매도 체결 시 지시서 타점이 실시간으로 뒤틀려
#    공수가 교대되는 하극상 엣지 케이스를 원천 차단함)
# MODIFIED: [V28.26 타임 패러독스 완벽 방어 수술]
# 서버 시간(KST/UTC) 의존성 100% 소각. 모든 스냅샷 및 쿼터 익절 캐싱 날짜를 
# 미국 동부시간(US/Eastern)으로 락온하여 자정 경계 환각 및 더블샷 버그 원천 차단.
# MODIFIED: [V30.09 핫픽스] pytz 영구 적출 및 ZoneInfo('America/New_York') 이식으로 LMT 버그 차단
# NEW: [자정 경계 스냅샷/캐시 증발(Cinderella) 타임 패러독스 완벽 방어] 런타임 붕괴(AttributeError) 차단 정수 기반 락온
# MODIFIED: [V44.57 인덴테이션 붕괴 수술] PEP8 규격 강제 및 IndentationError 영구 소각
# MODIFIED: [V44.58 스냅샷 멱등성 파괴 엣지 케이스 수술] 파일명에 논리적 날짜(today_str) 결속 락온 완료
# 🚨 NEW: [V72.00 줍줍 전면 소각 및 1회 예산 0.5회분 필수 분할 락온]
# - 줍줍 기능 불필요 지시에 따라 `bonus_orders`에 삽입되던 모든 줍줍 매수 로직을 100% 영구 소각 완료.
# - 새출발, 후반전, 리버스 매수 시 예산을 한 번에 쏘지 않고 정확히 0.5회분씩 분할(Buy1, Buy2)하여 덫을 장전하도록 안전 마진 락온.
# ==========================================================
import math
import os
import json
import tempfile
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

class V14Strategy:
    def __init__(self, config):
        self.cfg = config

    def _ceil(self, val): return math.ceil(val * 100) / 100.0
    def _floor(self, val): return math.floor(val * 100) / 100.0

    def _get_logical_date_str(self):
        now_est = datetime.now(ZoneInfo('America/New_York'))
        if now_est.hour < 4 or (now_est.hour == 4 and now_est.minute < 4):
            target_date = now_est - timedelta(days=1)
        else:
            target_date = now_est
        return target_date.strftime("%Y-%m-%d")

    def save_daily_snapshot(self, ticker, plan_data):
        today_str = self._get_logical_date_str()
        snap_file = f"data/daily_snapshot_V14_{today_str}_{ticker}.json"
        
        if os.path.exists(snap_file):
            return
        
        data = {
            "date": today_str,
            "total_q": int(plan_data.get('total_q', 0)),
            "avg_price": float(plan_data.get('avg_price', 0.0)),
            "one_portion": float(plan_data.get('one_portion', 0.0)),
            "star_price": float(plan_data.get('star_price', 0.0)),
            "star_ratio": float(plan_data.get('star_ratio', 0.0)),
            "t_val": float(plan_data.get('t_val', 0.0)),
            "is_reverse": bool(plan_data.get('is_reverse', False)),
            "orders": plan_data.get('orders', []),
            "core_orders": plan_data.get('core_orders', []),
            "bonus_orders": plan_data.get('bonus_orders', []),
            "process_status": plan_data.get('process_status', '')
        }
        
        os.makedirs(os.path.dirname(snap_file), exist_ok=True)
        try:
            fd, temp_path = tempfile.mkstemp(dir=os.path.dirname(snap_file))
            with os.fdopen(fd, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
                f.flush()
                os.fsync(f.fileno())
            os.replace(temp_path, snap_file)
        except Exception:
            pass

    def load_daily_snapshot(self, ticker):
        today_str = self._get_logical_date_str()
        snap_file = f"data/daily_snapshot_V14_{today_str}_{ticker}.json"
        
        if os.path.exists(snap_file):
            try:
                with open(snap_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if data.get("date") == today_str:
                        return data
            except Exception:
                pass
        return None

    def _mark_quarter_sell_completed(self, ticker):
        flag_file = f"cache_sniper_sell_{ticker}.json"
        today_str = self._get_logical_date_str()
        
        if os.path.exists(flag_file):
            try:
                with open(flag_file, 'r') as f:
                    data = json.load(f)
                    if data.get("date") == today_str and data.get("QUARTER_SELL_COMPLETED"):
                        return
            except Exception:
                pass

        data = {"date": today_str, "QUARTER_SELL_COMPLETED": True}
        try:
            fd, temp_path = tempfile.mkstemp(dir=".")
            with os.fdopen(fd, 'w') as f:
                json.dump(data, f)
                f.flush()
                os.fsync(f.fileno())
            os.replace(temp_path, flag_file)
        except Exception:
            pass

    def _apply_wash_trade_shield(self, c_orders, b_orders):
        all_o = c_orders + b_orders
        
        has_sell_moc = any(o['type'] in ['MOC', 'MOO'] and o['side'] == 'SELL' for o in all_o)
        
        s_prices = [o['price'] for o in all_o if o['side'] == 'SELL' and o['price'] > 0]
        min_s = min(s_prices) if s_prices else 0.0

        def _clean(lst):
            res = []
            for o in lst:
                new_o = o.copy()
                if new_o['side'] == 'BUY':
                    if has_sell_moc and new_o['type'] in ['LOC', 'MOC']: 
                        continue 
                    
                    if min_s > 0 and new_o['price'] >= min_s:
                        new_o['price'] = round(min_s - 0.01, 2)
                        if "🛡️" not in new_o['desc']: 
                            new_o['desc'] = f"🛡️교정_{new_o['desc'].replace('🧹', '')}"
                    
                    new_o['price'] = max(0.01, new_o['price'])
                        
                res.append(new_o)
            return res

        return _clean(c_orders), _clean(b_orders)

    def get_plan(self, ticker, current_price, avg_price, qty, prev_close, ma_5day=0.0, market_type="REG", available_cash=0, is_simulation=False, is_snapshot_mode=False, **kwargs):
        
        if not is_snapshot_mode:
            snap = self.load_daily_snapshot(ticker)
            if snap:
                return snap
                
        core_orders = []
        bonus_orders = []
        process_status = "" 
        tr_info = {}
        
        lock_s_sell = self.cfg.check_lock(ticker, "SNIPER_SELL")

        if lock_s_sell and not is_simulation:
            self._mark_quarter_sell_completed(ticker)

        other_locked_cash = self.cfg.get_total_locked_cash(exclude_ticker=ticker)
        real_available_cash = max(0, available_cash - other_locked_cash)
        
        split = self.cfg.get_split_count(ticker)      
        target_pct_val = self.cfg.get_target_profit(ticker) 
        target_ratio = target_pct_val / 100.0
        
        rev_state = self.cfg.get_reverse_state(ticker)
        is_reverse = rev_state.get("is_active", False)
        rev_day = rev_state.get("day_count", 0)
        exit_target = rev_state.get("exit_target", 0.0)

        t_val, base_portion = self.cfg.get_absolute_t_val(ticker, qty, avg_price)
        target_price = self._ceil(avg_price * (1 + target_ratio)) if avg_price > 0 else 0
        is_jackpot_reached = target_price > 0 and current_price >= target_price

        _, dynamic_budget, _ = self.cfg.calculate_v14_state(ticker)
        one_portion_amt = dynamic_budget
        
        is_money_short_check = False if (is_simulation or market_type == "PRE_CHECK") else (real_available_cash < one_portion_amt)
        
        if not is_reverse and (t_val > (split - 1) or (qty > 0 and is_money_short_check)):
            if not is_jackpot_reached:
                is_reverse = True 
                rev_day = 1 
                
                current_return = (current_price - avg_price) / avg_price * 100.0 if avg_price > 0 else 0.0
                default_exit = -15.0 if ticker == "TQQQ" else -20.0
                
                if current_return >= default_exit:
                    exit_target = 0.0
                else:
                    exit_target = default_exit

        depreciation_factor = 2.0 / split if split > 0 else 0.1
        star_ratio = target_ratio - (target_ratio * depreciation_factor * t_val)
        
        if is_reverse:
            if ma_5day > 0: 
                star_price = round(ma_5day, 2)
            else: 
                star_price = self._ceil(avg_price)

            ledger = self.cfg.get_ledger()
            total_sell_amount = 0.0
            
            for r in reversed(ledger):
                if r.get('ticker') == ticker:
                    if r.get('is_reverse', False):
                        if r['side'] == 'SELL':
                            total_sell_amount += (r['qty'] * r['price'])
                    else:
                        break
            
            if total_sell_amount > 0:
                one_portion_amt = total_sell_amount / 4.0
            else:
                one_portion_amt = base_portion
                
            if one_portion_amt <= 0:
                return {"orders": [], "core_orders": [], "bonus_orders": [], "total_q": qty, "avg_price": avg_price, "t_val": t_val, "one_portion": 0.0, "process_status": "⛔리버스예산오류(0원)", "is_reverse": True, "star_price": star_price, "star_ratio": star_ratio, "real_cash_used": real_available_cash, "tracking_info": tr_info}
        else:
            star_price = self._ceil(avg_price * (1 + star_ratio)) if avg_price > 0 else 0
            
        is_last_lap = (split - 1) < t_val < split
        
        if is_simulation: is_money_short = False
        else: is_money_short = real_available_cash < one_portion_amt

        base_price = current_price if current_price > 0 else prev_close
        if base_price <= 0: 
            return {"orders": [], "core_orders": [], "bonus_orders": [], "total_q": qty, "avg_price": avg_price, "t_val": t_val, "one_portion": one_portion_amt, "process_status": "⛔가격오류", "is_reverse": is_reverse, "star_price": star_price, "star_ratio": star_ratio, "real_cash_used": real_available_cash, "tracking_info": tr_info}
            
        if market_type == "PRE_CHECK":
            process_status = "🌅프리마켓"
            if qty > 0 and target_price > 0 and current_price >= target_price and not is_reverse:
                core_orders.append({"side": "SELL", "price": current_price, "qty": int(qty), "type": "LIMIT", "desc": "🌅프리:목표돌파익절"})
            orders = core_orders + bonus_orders
            return {"orders": orders, "core_orders": core_orders, "bonus_orders": bonus_orders, "total_q": qty, "avg_price": avg_price, "t_val": t_val, "one_portion": one_portion_amt, "process_status": process_status, "is_reverse": is_reverse, "star_price": star_price, "star_ratio": star_ratio, "real_cash_used": real_available_cash, "tracking_info": tr_info}

        if market_type == "REG":
            if qty == 0:
                process_status = "✨새출발"
                buy_price = max(0.01, round(self._ceil(base_price * 1.15) - 0.01, 2))
                
                half_budget = one_portion_amt * 0.5
                buy_qty1 = int(math.floor(half_budget / buy_price)) if buy_price > 0 else 0
                buy_qty2 = int(math.floor((one_portion_amt - half_budget) / buy_price)) if buy_price > 0 else 0
                
                if buy_qty1 > 0:
                    core_orders.append({"side": "BUY", "price": buy_price, "qty": buy_qty1, "type": "LOC", "desc": "🆕새출발1"})
                if buy_qty2 > 0:
                    core_orders.append({"side": "BUY", "price": buy_price, "qty": buy_qty2, "type": "LOC", "desc": "🆕새출발2"})
                    
                orders = core_orders + bonus_orders
                return {"orders": orders, "core_orders": core_orders, "bonus_orders": bonus_orders, "total_q": qty, "avg_price": avg_price, "t_val": t_val, "one_portion": one_portion_amt, "process_status": process_status, "is_reverse": False, "star_price": star_price, "star_ratio": star_ratio, "real_cash_used": real_available_cash, "tracking_info": tr_info}

            if is_reverse:
                sell_divisor = 10 if split <= 20 else 20
                
                if qty < 4:
                    sell_qty = int(qty)
                else:
                    sell_qty = int(max(4, math.floor(qty / sell_divisor)))

                is_emergency_cash_needed = (real_available_cash < base_price) and (rev_day > 1)

                if rev_day == 1 or is_emergency_cash_needed:
                    process_status = "🩸리버스(긴급수혈)" if is_emergency_cash_needed else "🚨리버스(1일차)"
                    
                    if sell_qty > 0:
                        desc_str = "🩸수혈매도" if is_emergency_cash_needed else "🛡️의무매도"
                        if qty < 4: desc_str = "💥잔량청산(수량부족)"
                        core_orders.append({"side": "SELL", "price": 0, "qty": sell_qty, "type": "MOC", "desc": desc_str})
                else:
                    process_status = f"🔄리버스({rev_day}일차)"
                    buy_price = 0
                    if one_portion_amt > 0 and star_price > 0:
                        buy_price = max(0.01, round(star_price - 0.01, 2))
                        if buy_price > 0: 
                            b1_budget = one_portion_amt * 0.5
                            b2_budget = one_portion_amt - b1_budget
                            buy_qty1 = int(math.floor(b1_budget / buy_price))
                            buy_qty2 = int(math.floor(b2_budget / buy_price))
                            if buy_qty1 > 0:
                                core_orders.append({"side": "BUY", "price": buy_price, "qty": buy_qty1, "type": "LOC", "desc": "⚓잔금매수1"})
                            if buy_qty2 > 0:
                                core_orders.append({"side": "BUY", "price": buy_price, "qty": buy_qty2, "type": "LOC", "desc": "⚓잔금매수2"})
                     
                    if not lock_s_sell and sell_qty > 0 and star_price > 0:
                        core_orders.append({"side": "SELL", "price": star_price, "qty": sell_qty, "type": "LOC", "desc": "🌟별값매도"})

                if lock_s_sell: process_status = "🔫리버스(명중)"

                core_orders, bonus_orders = self._apply_wash_trade_shield(core_orders, bonus_orders)        
                orders = core_orders + bonus_orders
                return {"orders": orders, "core_orders": core_orders, "bonus_orders": bonus_orders, "total_q": qty, "avg_price": avg_price, "t_val": t_val, "one_portion": one_portion_amt, "process_status": process_status, "is_reverse": is_reverse, "star_price": star_price, "star_ratio": star_ratio, "real_cash_used": real_available_cash, "tracking_info": tr_info}

            if is_jackpot_reached and (t_val > (split - 1) or is_money_short):
                process_status = "🎉대박익절(리버스생략)"
                if qty > 0:
                    core_orders.append({"side": "SELL", "price": target_price, "qty": int(qty), "type": "LIMIT", "desc": "🎯전량대박익절"})
                core_orders, bonus_orders = self._apply_wash_trade_shield(core_orders, bonus_orders)        
                orders = core_orders + bonus_orders
                return {
                    "orders": orders, "core_orders": core_orders, "bonus_orders": bonus_orders, "total_q": qty, "avg_price": avg_price,
                    "t_val": t_val, "one_portion": one_portion_amt, "process_status": process_status,
                    "is_reverse": False, "star_price": star_price, "star_ratio": star_ratio,
                    "real_cash_used": real_available_cash,
                    "tracking_info": tr_info 
                }
            elif is_last_lap: process_status = "🏁마지막회차"
            elif is_money_short: process_status = "🛡️방어모드(부족)"
            elif t_val < (split / 2): process_status = "🌓전반전"
            else: process_status = "🌕후반전"

            if t_val > (split * 1.1):
                process_status = "🚨T값폭주(역산경고)"

            can_buy = not is_money_short and not is_last_lap
            
            safe_ceiling = min(avg_price, star_price) if star_price > 0 else avg_price

            p_avg = max(0.01, round(min(self._ceil(avg_price) - 0.01, safe_ceiling - 0.01), 2))
            
            if can_buy:
                p_star = max(0.01, round(star_price - 0.01, 2))

                if t_val < (split / 2):
                    half_amt = one_portion_amt * 0.5
                    q_avg = math.floor(half_amt / p_avg) if p_avg > 0 else 0
                    q_star = math.floor((one_portion_amt - half_amt) / p_star) if p_star > 0 else 0
                    
                    if q_avg > 0:
                        core_orders.append({"side": "BUY", "price": p_avg, "qty": q_avg, "type": "LOC", "desc": "⚓평단매수"})
                    if q_star > 0:
                        core_orders.append({"side": "BUY", "price": p_star, "qty": int(q_star), "type": "LOC", "desc": "💫별값매수"})
                else: 
                    if p_star > 0:
                        half_amt = one_portion_amt * 0.5
                        q_star1 = int(math.floor(half_amt / p_star))
                        q_star2 = int(math.floor((one_portion_amt - half_amt) / p_star))
                        if q_star1 > 0:
                            core_orders.append({"side": "BUY", "price": p_star, "qty": q_star1, "type": "LOC", "desc": "💫별값매수1"})
                        if q_star2 > 0:
                            core_orders.append({"side": "BUY", "price": p_star, "qty": q_star2, "type": "LOC", "desc": "💫별값매수2"})

            if qty > 0:
                if lock_s_sell:
                    pass
                else:
                    q_qty = int(math.ceil(qty / 4))
                    rem_qty = int(qty - q_qty)
                
                    if star_price > 0 and q_qty > 0:
                        core_orders.append({"side": "SELL", "price": star_price, "qty": q_qty, "type": "LOC", "desc": "🌟별값매도"})
                    if target_price > 0 and rem_qty > 0:
                        core_orders.append({"side": "SELL", "price": target_price, "qty": rem_qty, "type": "LIMIT", "desc": "🎯목표매도"})

            if lock_s_sell:
                process_status = "🔫스나이퍼(명중)"

            core_orders, bonus_orders = self._apply_wash_trade_shield(core_orders, bonus_orders)        
            orders = core_orders + bonus_orders
            
            return {
                "orders": orders, "core_orders": core_orders, "bonus_orders": bonus_orders, "total_q": qty, "avg_price": avg_price,
                "t_val": t_val, "one_portion": one_portion_amt, "process_status": process_status,
                "is_reverse": is_reverse, "star_price": star_price, "star_ratio": star_ratio,
                "real_cash_used": real_available_cash,
                "tracking_info": tr_info 
            }
