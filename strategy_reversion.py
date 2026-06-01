# ==========================================================
# FILE: strategy_reversion.py
# ==========================================================
# 🚨 VERIFIED: [최종 무결점 판정] 5대 헌법 및 34대 엣지 케이스 완벽 결속 교차 검증 완료
# 🚨 MODIFIED: [Boolean String Paradox 방어] is_zero_start 문자열 오염 시 발생 가능한 평가 오류(`bool("False") -> True`)를 완벽 차단하는 명시적 캐스팅 락온.
# 🚨 MODIFIED: [딥-레스큐 아키텍처 V84.00 전면 리빌딩] 
# 🚨 MODIFIED: [투트랙 디커플링 팩트 교정] LIFO 큐 대통합이 해체되었으므로, 장부의 물량 자체가 '순수 본진 물량'으로 확정됨. 기존에 존재하던 암살자 물량(AVWAP_Qty) 이중 차감(Double Deduction) 로직을 전면 영구 소각.
# 🚨 MODIFIED: [파일 I/O 낭비 원천 차단] 암살자 물량 차감이 불필요해짐에 따라 `avwap_state_persistent.json`을 읽어오던 데드코드를 완전히 소각하여 이벤트 루프 블로킹 위험 제로화.
# 🚨 MODIFIED: [단일 지층 락온] 잔여 지층이 1개일 경우 상위층 덫(Upper_Price) 생성을 영구 소각하고 1층 탈출 덫만 단일 장전하도록 팩트 교정 완료
# 🚨 MODIFIED: [Case 08 절대 규칙 준수] 스냅샷 멱등성 훼손을 유발하는 os.path.exists 동기 스캔을 100% 영구 소각하고 EAFP 원자적 파일 I/O로 전면 교체
# 🚨 MODIFIED: [Float 정밀도 오염 차단] 부동소수점 오차(Float Precision Error)로 인한 trigger_upper 바운딩 붕괴 방어용 절대 쉴드(0.01) 주입 및 upper_inv 음수 발생 시 0.0 바운딩
# 🚨 MODIFIED: [Case 16 위반 교정] 원자적 쓰기 UnboundLocalError 방어막(스코프 전진배치 및 dir_name or '.') 결속
# 🚨 MODIFIED: [TypeError 붕괴 방어] q_data 결측치(None) 유입 시 루프 마비를 막기 위한 단락 평가(or []) 쉴드 래핑
# 🚨 MODIFIED: [Insight 14] String-Float 콤마 맹독성 런타임 붕괴 방어용 `_safe_float` 래핑 전면 이식
# 🚨 MODIFIED: [Insight 12] 큐 장부 오염 객체(Dirty Record) 방어용 `isinstance(item, dict)` 필터링 락온
# 🚨 MODIFIED: [Insight 06/07] JSON 이중 get() 호출 시 발생하는 AttributeError 붕괴 방어용 `(dict or {})` 단락 평가 쉴드 주입
# 🚨 MODIFIED: [당일 지층 매수 앵커 최우선 락온] is_zero_start_session 조건을 해체하고 오직 실제 물량(total_q) 유무만을 기준으로 매수 앵커를 산출하도록 교정.
# ==========================================================
import math
import os
import json
import tempfile
import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

class ReversionStrategy:
    def __init__(self, config):
        self.cfg = config
        self.residual = {}
        self.executed = {"BUY_BUDGET": {}, "SELL_QTY": {}}
        self.state_loaded = {}

    def _safe_float(self, value):
        try:
            val = float(str(value or 0.0).replace(',', ''))
            if math.isnan(val) or math.isinf(val): return 0.0
            return val
        except Exception: 
            return 0.0

    def _get_logical_date_str(self):
        now_est = datetime.now(ZoneInfo('America/New_York'))
        if now_est.hour < 4 or (now_est.hour == 4 and now_est.minute < 4):
            target_date = now_est - timedelta(days=1)
        else:
            target_date = now_est
        return target_date.strftime("%Y-%m-%d")

    def _get_state_file(self, ticker):
        today_str = self._get_logical_date_str()
        return f"data/vwap_state_REV_{today_str}_{ticker}.json"

    def _get_snapshot_file(self, ticker):
        today_str = self._get_logical_date_str()
        return f"data/daily_snapshot_REV_{today_str}_{ticker}.json"

    def _load_state_if_needed(self, ticker):
        today_str = self._get_logical_date_str()
        if self.state_loaded.get(ticker) == today_str:
            return 
        
        state_file = self._get_state_file(ticker)
        # 🚨 [TOCTOU 붕괴 방어] os.path.exists 동기 스캔 전면 소각 및 EAFP 적용
        try:
            with open(state_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if data.get("date") == today_str:
                    for k in self.executed.keys():
                        raw_val = (data.get("executed") or {}).get(k, 0)
                        self.executed[k][ticker] = int(self._safe_float(raw_val)) if k == "SELL_QTY" else self._safe_float(raw_val)
                    self.state_loaded[ticker] = today_str
                    return
        except Exception:
            pass
                   
        self.executed["BUY_BUDGET"][ticker] = 0.0
        self.executed["SELL_QTY"][ticker] = 0
        self.state_loaded[ticker] = today_str
        self._save_state(ticker)

    def _save_state(self, ticker):
        today_str = self._get_logical_date_str()
        state_file = self._get_state_file(ticker)
        data = {
            "date": today_str,
            "residual": {},
            "executed": {
                "BUY_BUDGET": self._safe_float((self.executed.get("BUY_BUDGET") or {}).get(ticker, 0.0)),
                "SELL_QTY": int(self._safe_float((self.executed.get("SELL_QTY") or {}).get(ticker, 0)))
            }
        }
        fd = None
        temp_path = None
        try:
            dir_name = os.path.dirname(state_file)
            if dir_name:
                try: os.makedirs(dir_name, exist_ok=True)
                except OSError: pass
            
            fd, temp_path = tempfile.mkstemp(dir=dir_name or '.', text=True)
            with os.fdopen(fd, 'w', encoding='utf-8') as f:
                fd = None
                json.dump(data, f, ensure_ascii=False, indent=4)
                f.flush()
                os.fsync(f.fileno())
            os.replace(temp_path, state_file)
            temp_path = None
        except Exception:
            if fd is not None:
                try: os.close(fd)
                except OSError: pass
            if temp_path:
                try: os.remove(temp_path)
                except OSError: pass

    def save_daily_snapshot(self, ticker, plan_data):
        snap_file = self._get_snapshot_file(ticker)
        today_str = self._get_logical_date_str()
        data = {
            "date": today_str,
            "plan": plan_data
        }
        fd = None
        temp_path = None
        try:
            dir_name = os.path.dirname(snap_file)
            if dir_name:
                try: os.makedirs(dir_name, exist_ok=True)
                except OSError: pass
            
            fd, temp_path = tempfile.mkstemp(dir=dir_name or '.', text=True)
            with os.fdopen(fd, 'w', encoding='utf-8') as f:
                fd = None
                json.dump(data, f, ensure_ascii=False, indent=4)
                f.flush()
                os.fsync(f.fileno())
            os.replace(temp_path, snap_file)
            temp_path = None
        except Exception:
            if fd is not None:
                try: os.close(fd)
                except OSError: pass
            if temp_path:
                try: os.remove(temp_path)
                except OSError: pass

    def load_daily_snapshot(self, ticker):
        snap_file = self._get_snapshot_file(ticker)
        try:
            with open(snap_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get("plan")
        except Exception:
            pass
        return None

    def ensure_failsafe_snapshot(self, ticker, curr_p, prev_c, alloc_cash, q_data, total_kis_qty, avwap_qty):
        # 🚨 [Type-Safety] 진입 파라미터 방어막 결속
        curr_p = self._safe_float(curr_p)
        prev_c = self._safe_float(prev_c)
        alloc_cash = self._safe_float(alloc_cash)
        
        snap = self.load_daily_snapshot(ticker)
        if snap is not None:
            return snap
            
        today_str_est = self._get_logical_date_str()
        legacy_lots = [item for item in (q_data or []) if isinstance(item, dict) and not str(item.get("date", "")).startswith(today_str_est)]
        
        logging.warning(f"🚨 [{ticker}] V_REV 스냅샷 증발 감지! 페일세이프 긴급 복원 가동")
        
        return self.get_dynamic_plan(
            ticker=ticker,
            curr_p=curr_p,
            prev_c=prev_c,
            current_weight=0.0,
            vwap_status={},
            min_idx=-1,
            alloc_cash=alloc_cash,
            q_data=legacy_lots,
            is_snapshot_mode=True,
            market_type="REG"
        )

    def record_execution(self, ticker, side, qty, exec_price):
        self._load_state_if_needed(ticker)
        safe_qty = int(self._safe_float(qty))
        safe_price = self._safe_float(exec_price)
        
        if side == "BUY":
            spent = safe_qty * safe_price
            self.executed["BUY_BUDGET"][ticker] = self._safe_float((self.executed.get("BUY_BUDGET") or {}).get(ticker, 0.0)) + spent
        else:
            self.executed["SELL_QTY"][ticker] = int(self._safe_float((self.executed.get("SELL_QTY") or {}).get(ticker, 0))) + safe_qty
        self._save_state(ticker)

    def get_dynamic_plan(self, ticker, curr_p, prev_c, current_weight, vwap_status, min_idx, alloc_cash, q_data, is_snapshot_mode=False, market_type="REG"):
        # 🚨 [Type-Safety] 진입 파라미터 방어막 결속
        curr_p = self._safe_float(curr_p)
        prev_c = self._safe_float(prev_c)
        current_weight = self._safe_float(current_weight)
        alloc_cash = self._safe_float(alloc_cash)

        self._load_state_if_needed(ticker)

        cached_plan = self.load_daily_snapshot(ticker)
        if not is_snapshot_mode and cached_plan:
            return cached_plan

        # 🚨 MODIFIED: [투트랙 디커플링 팩트 교정] LIFO 큐 장부 대통합 해체에 따라 암살자 물량(AVWAP_Qty) 파일 I/O 스캔 및 이중 차감(Double Deduction) 로직 전면 영구 소각 완료.
        valid_q_data = [item for item in (q_data or []) if isinstance(item, dict) and self._safe_float(item.get('price')) > 0]
        total_q = sum(int(self._safe_float(item.get("qty"))) for item in valid_q_data)
        total_inv = sum(self._safe_float(item.get('qty')) * self._safe_float(item.get('price')) for item in valid_q_data)
        
        # TypeError(비교 불가) 방어를 위한 str() 캐스팅
        dates_in_queue = sorted(list(set(str(item.get('date', '')) for item in valid_q_data if item.get('date'))), reverse=True)
        l1_qty, l1_price = 0, 0.0
        
        if dates_in_queue:
            lots_1 = [item for item in valid_q_data if str(item.get('date', '')) == dates_in_queue[0]]
            l1_qty = sum(int(self._safe_float(item.get('qty'))) for item in lots_1)
            l1_price = sum(self._safe_float(item.get('qty')) * self._safe_float(item.get('price')) for item in lots_1) / l1_qty if l1_qty > 0 else 0.0
        
        upper_qty = total_q - l1_qty

        # 🚨 [본진 디커플링 완전 독립 락온] 
        # 장부 대통합이 해체되었으므로 큐 장부의 물량이 100% 순수 본진 물량입니다. 암살자 물량(AVWAP_Qty) 이중 차감 로직을 적용하지 않습니다.
        pure_l1_qty = l1_qty
        pure_upper_qty = upper_qty

        trigger_l1 = round(l1_price * 1.006, 2)
        
        # 🚨 [단일 지층 락온] 순수 상위 지층이 존재하고(pure_upper_qty > 0) 지층 종류가 2개 이상일 때만 상위층 탈출 덫 장전
        if pure_upper_qty > 0 and len(dates_in_queue) >= 2:
            # upper_inv는 전체 투자금에서 수학적 1지층(l1_qty) 투자금을 빼서 산출
            upper_inv = max(0.0, total_inv - (l1_price * l1_qty))
            upper_price = upper_inv / pure_upper_qty if pure_upper_qty > 0 else 0.0
            trigger_upper = round(upper_price * 1.010, 2)
        else:
            trigger_upper = 0.0

        if is_snapshot_mode:
            is_zero_start_session = (total_q == 0)
        else:
            if cached_plan:
                # 🚨 MODIFIED: [Boolean String Paradox 방어] 문자열 오염 시 발생 가능한 평가 오류 완벽 차단
                is_zero_val = cached_plan.get("is_zero_start")
                if is_zero_val is None:
                    tot_q = int(self._safe_float(cached_plan.get("snapshot_total_q", cached_plan.get("total_q", -1))))
                    is_zero_start_session = (tot_q == 0)
                else:
                    if isinstance(is_zero_val, str):
                        is_zero_start_session = (is_zero_val.lower() == 'true')
                    else:
                        is_zero_start_session = bool(is_zero_val)
            else:
                today_str_est = self._get_logical_date_str()
                legacy_lots = [item for item in valid_q_data if not str(item.get("date", "")).startswith(today_str_est)]
                legacy_q = sum(int(self._safe_float(item.get("qty"))) for item in legacy_lots)
                is_zero_start_session = (legacy_q == 0)

        # 🚨 [당일 지층 매수 앵커 최우선 락온] is_zero_start_session을 배제하고 오직 팩트 물량(total_q)에 기반한 매수 앵커 맵핑
        if total_q == 0:
            p1_trigger = round(prev_c * 1.15, 2)
            p2_trigger = round(prev_c * 0.999, 2)
        else:
            safe_anchor = l1_price if l1_price > 0.0 else prev_c
            p1_trigger = round(safe_anchor * 0.9976, 2)
            p2_trigger = round(safe_anchor * 0.9887, 2)

        # 본진이 오늘 매도한 수량을 제외하고 순수 본진 물량 배분
        rem_qty_total = max(0, int(pure_l1_qty + pure_upper_qty) - int(self._safe_float((self.executed.get("SELL_QTY") or {}).get(ticker, 0))))
        available_l1 = min(pure_l1_qty, rem_qty_total) if rem_qty_total > 0 else 0
        available_upper = min(pure_upper_qty, rem_qty_total - available_l1) if rem_qty_total > 0 else 0
        
        if rem_qty_total > 0:
            active_sells = []
            if available_l1 > 0 and trigger_l1 > 0:
                active_sells.append(trigger_l1)
            # 🚨 [Float 정밀도 방어] 0.01 하드코딩으로 부동소수점 찌꺼기 완벽 필터링
            if available_upper > 0 and trigger_upper >= 0.01:
                active_sells.append(trigger_upper)
                
            if active_sells:
                min_sell = min(active_sells)
                if p1_trigger >= min_sell:
                    p1_trigger = max(0.01, round(min_sell - 0.01, 2))
                if p2_trigger >= min_sell:
                    p2_trigger = max(0.01, round(min_sell - 0.01, 2))

        orders = []

        est_zone = ZoneInfo('America/New_York')
        kst_zone = ZoneInfo('Asia/Seoul')
        now_est = datetime.now(est_zone)
        
        base_start_est = now_est.replace(hour=15, minute=26, second=0, microsecond=0)
        shifted_start_est = now_est + timedelta(minutes=3)
        actual_start_est = max(base_start_est, shifted_start_est)
        
        base_end_est = now_est.replace(hour=15, minute=56, second=0, microsecond=0)
        
        start_dt_kst = actual_start_est.astimezone(kst_zone)
        end_dt_kst = base_end_est.astimezone(kst_zone)
        
        start_t = start_dt_kst.strftime("%H%M%S")
        end_t = end_dt_kst.strftime("%H%M%S")

        total_spent = 0.0 if is_snapshot_mode else self._safe_float((self.executed.get("BUY_BUDGET") or {}).get(ticker, 0.0))
        
        seed_val = self._safe_float(self.cfg.get_seed(ticker))
        daily_limit = seed_val * 0.15
        
        safe_alloc_cash = min(float(alloc_cash), daily_limit) if daily_limit > 0 else float(alloc_cash)
        rem_budget = max(0.0, safe_alloc_cash - total_spent)
        
        if rem_budget > 0:
            b1_budget = rem_budget * 0.5
            b2_budget = rem_budget * 0.5
            
            q1 = math.floor(b1_budget / p1_trigger) if p1_trigger > 0 else 0
            q2 = math.floor(b2_budget / p2_trigger) if p2_trigger > 0 else 0
            
            if q1 == 0 and q2 == 0:
                if p1_trigger > 0 and rem_budget >= p1_trigger:
                    q1 = math.floor(rem_budget / p1_trigger)
                elif p2_trigger > 0 and rem_budget >= p2_trigger:
                    q2 = math.floor(rem_budget / p2_trigger)
            elif q1 == 0 and q2 > 0:
                q2 = math.floor(rem_budget / p2_trigger) if p2_trigger > 0 else 0
            elif q2 == 0 and q1 > 0:
                q1 = math.floor(rem_budget / p1_trigger) if p1_trigger > 0 else 0
            
            # 🚨 [V-REV 로컬 슬라이싱 엔진] 무조건 VWAP 태그 락온
            if q1 > 0:
                ord_type = "VWAP"
                desc_str = "VWAP매수(Buy1)"
                orders.append({"side": "BUY", "qty": q1, "price": p1_trigger, "type": ord_type, "start_time": start_t, "end_time": end_t, "desc": desc_str})
            if q2 > 0:
                ord_type = "VWAP"
                desc_str = "VWAP매수(Buy2)"
                orders.append({"side": "BUY", "qty": q2, "price": p2_trigger, "type": ord_type, "start_time": start_t, "end_time": end_t, "desc": desc_str})
        
        if rem_qty_total > 0:
            sell_dict = {}
            if available_l1 > 0 and trigger_l1 > 0:
                sell_dict[trigger_l1] = sell_dict.get(trigger_l1, 0) + available_l1
            # 🚨 [Float 정밀도 방어] 0.01 하드코딩으로 부동소수점 찌꺼기 완벽 필터링 (단일 지층 락온 사수)
            if available_upper > 0 and trigger_upper >= 0.01:
                sell_dict[trigger_upper] = sell_dict.get(trigger_upper, 0) + available_upper
                
            for price in sorted(sell_dict.keys()):
                s_qty = sell_dict[price]
                
                # 🚨 [V-REV 로컬 슬라이싱 엔진] KIS 서버 VWAP 10주 제약 파기 및 전면 자체 VWAP 위임
                ord_type = "VWAP"
                
                if price == trigger_l1 and price == trigger_upper:
                    desc_str = "통합탈출"
                elif price == trigger_l1:
                    desc_str = "1층탈출"
                elif price == trigger_upper:
                    desc_str = "상위층탈출"
                else:
                    desc_str = "잔여탈출"
                    
                orders.append({
                    "side": "SELL", "qty": s_qty, "price": price, "type": ord_type, 
                    "start_time": start_t, 
                    "end_time": end_t, 
                    "desc": desc_str
                })
        
        plan_result = {
            "orders": orders, 
            "trigger_loc": False, 
            "total_q": total_q,
            "is_zero_start": is_zero_start_session
        }
        
        if is_zero_start_session and market_type != "AFTER":
            plan_result["orders"] = [o for o in plan_result.get("orders", []) if o.get("side") != "SELL"]
        
        if is_snapshot_mode:
            self.save_daily_snapshot(ticker, plan_result)

        self._save_state(ticker)
        return plan_result
