# ==========================================================
# FILE: strategy_reversion.py
# ==========================================================
# 🚨 MODIFIED: [V-REV 추세장 LOC 스위칭 침묵 버그 및 상태 증발 완벽 수술]
# get_dynamic_plan 엔진이 60% 거래량 지배력을 감지하고 LOC 방어선으로 전환(trigger_loc)할 때, 
# 상태 파일 저장을 누락한 채 루프 탈출하여 봇이 영구 기절하던 치명적 맹점 원천 차단. 
# return 직전에 self._save_state(ticker)를 강제 주입하여 팩트 박제 및 락온 완료.
# MODIFIED: [V44.27 0주 스냅샷 환각 락온] 서버 재시작으로 인메모리 스냅샷이 소실되었을 때, VWAP이 장중 매수한 로트를 기보유 물량으로 오판하여 매도를 재개(하극상)하던 맹점 원천 차단. 큐 장부에서 당일 날짜(EST)의 로트를 100% 도려내고 오직 어제까지 이월된 순수 과거 물량만을 스캔하여 '0주 새출발' 상태를 완벽히 팩트 복구하는 타임머신 역산 엔진 이식 완료.
# MODIFIED: [V44.25 예산 탈취(Stealing) 런타임 붕괴 방어막 이식] Buy1이 Buy2의 미사용 예산을 훔쳐와 무한 타격(34주 체결 등)하는 차원 붕괴를 영구 소각.
# MODIFIED: [V44.25 AVWAP 디커플링] VWAP 기상 전 스냅샷 2중 교차 검증(Fail-Safe) 및 암살자 물량(AVWAP) 100% 격리(Decoupling) 파이프라인 이식 완료.
# MODIFIED: [V44.36 큐 장부 vs 브로커 실잔고 불일치 팩트 스캔] 페일세이프 스냅샷 복원 시 KIS 순수 본대 수량과 큐 장부 이월 수량 간의 팩트 불일치가 발생할 경우 명시적으로 경고를 타전하여 CALIB 보정을 유도하도록 감시망(EC-3) 이식 완료.
# MODIFIED: [V44.48 런타임 붕괴 방어] 들여쓰기 붕괴(IndentationError) 완벽 교정.
# NEW: [VWAP 잔차 증발 방어 롤백 엔진] 주문 거절/미체결 시 삭감된 예산을 버킷 식별자 기반으로 원상 복구(Refund)하는 환불 파이프라인 개통 완료.
# NEW: [V46.01 팩트 교정] 소형 시드 1주 타격 영구 동결(Data Starvation) 및 분할 교착 맹점 원천 차단
# 🚨 MODIFIED: [V46.02 엣지 케이스 핫픽스: 잔차 파탄 완벽 해체] 소형 시드 분할 교착 방어 시 기저 버킷(bucket) 동기화 및 초기화 로직 100% 추가.
# 🚨 MODIFIED: [V48.00 단일 바구니(Single Bucket) 롤백] Buy1과 Buy2 예산 스틸링(Stealing)을 허용하여 체결 우위 극대화 및 데이터 기아 원천 차단.
# 🚨 MODIFIED: [V50.02 30분 압축 락온] 타임 윈도우 스캔 범위를 range(27, 60)에서 range(27, 57)로 정밀 교정하여 15:56 타격 종료 완벽 동기화.
# 🚨 MODIFIED: [V50.03 분할 교착 및 예산 강제 축소 버그 완벽 수술] 기존 elif 구조로 인해 버려지던 가불 로직을 독립된 if문으로 분리하고, 이미 예산이 넉넉한 경우를 1주 가격(curr_p)으로 강제 축소해버리는 치명적 맹점 원천 차단.
# 🚨 MODIFIED: [V51.00 몰빵 로직 전면 철거] 0주 진입 시에도 50:50 분할 예산 원칙을 100% 강제 락온하여 예산 효율성 복구 완료.
# 🚨 MODIFIED: [V51.01 소형 시드 1주 영끌 타격 락온] 예산이 1주 가격보다 작더라도 장막판 가불을 통해 무조건 1주 베이스캠프 확보 보장.
# 🚨 MODIFIED: [V53.00 무한 재진입 락온] 0주 매수 금지(Daily Buy-Lock) 족쇄 전면 폐기 및 was_holding 데드코드 100% 소각. 전량 익절 후에도 당일 타점 도달 시 100% 재매수 강제 가동.
# 🚨 NEW: [KIS VWAP 알고리즘 대통합 수술] 1분 단위 타임 슬라이싱 연산 및 잔차 버킷 파편화 궤적을 100% 영구 소각하고, 할당된 1회분 총 예산을 단일 KIS VWAP 덫 예약 주문 플랜으로 통짜 스냅샷 산출하여 반환하도록 아키텍처 대수술 완료.
# 🚨 MODIFIED: [V71.05 KIS VWAP 30분 압축 타격 타임라인 락온]
# - 종일 타격 패러독스를 방어하기 위해 지시서 생성 시 start_time(153000), end_time(155500) 파라미터를 팩트 인젝션하여 30분 압축 타임라인 확립 완료.
# 🚨 MODIFIED: [V71.13 런타임 붕괴 방어 및 타임라인 전진 배치 수술]
# - 들여쓰기 붕괴(IndentationError) 팩트 무결점 교정.
# - start_time 파라미터 153000 하드코딩을 152500으로 전진 배치하여 V-REV 덤핑 복원 타임라인(15:25 EST)과 100% 동기화 완료.
# 🚨 NEW: [V71.14 예약 덫 무조건 장전 헌법 복구 및 족쇄 철거]
# - 1분 타임 슬라이싱 시절의 잔재인 `curr_p >= trigger_l1` 가격 족쇄를 전면 적출.
# - 예약 덫(Limit VWAP)이므로 현재가와 무관하게 100% 무조건 KIS 서버에 Pop1, Pop2 매도 덫을 깔아두도록 퀀트 제1헌법 복구 완료.
# 🚨 MODIFIED: [V71.25 KST 타임라인 동적 래핑 수술]
# - KIS 서버의 알고리즘 시간 요구사항(KST)에 맞춰 EST를 강제하던 맹점(152500)을 100% 영구 소각.
# - 서머타임(DST) 적용 여부를 스캔하여 042500/045500 또는 052500/055500을 동적으로 주입하는 무결점 아키텍처 이식.
# 🚨 MODIFIED: [V71.27 런타임 붕괴 수술]
# - `for n in range(1, max_n + 1):` 라인에 침투한 IndentationError(들여쓰기) 불일치 팩트 교정 완료.
# 🚨 MODIFIED: [V72.00 줍줍 전면 소각 및 VWAP 10주 제약 LOC 우회 락온]
# - 줍줍 데드코드 100% 소각 및 매수 0.5회분 강제 분할 보장 로직.
# - KIS 지정가 VWAP 10주 미만 리젝 방어를 위해 qty < 10인 VWAP 주문을 LOC로 동적 오버라이드.
# 🚨 MODIFIED: [V72.01 V-REV 1회 예산(15%) 하드 마진 캡(Cap) 락온]
# - 외부 라우터에서 비정상적으로 거대한 예산(alloc_cash)이 유입되더라도, 
#   절대 당일 1일 할당량(시드의 15%) 잔여분을 초과할 수 없도록 
#   수학적 하드 마진 클램핑 이식 완료.
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
        if os.path.exists(state_file):
            try:
                with open(state_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for k in self.executed.keys():
                        raw_val = data.get("executed", {}).get(k, 0)
                        self.executed[k][ticker] = int(raw_val) if k == "SELL_QTY" else float(raw_val)
                    self.state_loaded[ticker] = today_str
                    return
            except Exception:
                pass
                
        self.executed["BUY_BUDGET"][ticker] = 0.0
        self.executed["SELL_QTY"][ticker] = 0
        self.state_loaded[ticker] = today_str

    def _save_state(self, ticker):
        today_str = self._get_logical_date_str()
        state_file = self._get_state_file(ticker)
        data = {
            "date": today_str,
            "residual": {},
            "executed": {
                "BUY_BUDGET": float(self.executed.get("BUY_BUDGET", {}).get(ticker, 0.0)),
                "SELL_QTY": int(self.executed.get("SELL_QTY", {}).get(ticker, 0))
            }
        }
        temp_path = None
        try:
            dir_name = os.path.dirname(state_file)
            if dir_name and not os.path.exists(dir_name):
                os.makedirs(dir_name, exist_ok=True)
            fd, temp_path = tempfile.mkstemp(dir=dir_name, text=True)
            with os.fdopen(fd, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
                f.flush()
                os.fsync(f.fileno())
            os.replace(temp_path, state_file)
            temp_path = None
        except Exception:
            if temp_path and os.path.exists(temp_path):
                try:
                    os.unlink(temp_path)
                except OSError:
                    pass

    def refund_residual(self, ticker, bucket, refund_value):
        pass

    def save_daily_snapshot(self, ticker, plan_data):
        snap_file = self._get_snapshot_file(ticker)
        if os.path.exists(snap_file):
            return
            
        today_str = self._get_logical_date_str()
        data = {
            "date": today_str,
            "plan": plan_data
        }
        temp_path = None
        try:
            dir_name = os.path.dirname(snap_file)
            if not os.path.exists(dir_name):
                os.makedirs(dir_name, exist_ok=True)
            fd, temp_path = tempfile.mkstemp(dir=dir_name, text=True)
            with os.fdopen(fd, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
                f.flush()
                os.fsync(f.fileno())
            os.replace(temp_path, snap_file)
            temp_path = None
        except Exception:
            if temp_path and os.path.exists(temp_path):
                try: os.unlink(temp_path)
                except OSError: pass

    def load_daily_snapshot(self, ticker):
        snap_file = self._get_snapshot_file(ticker)
        if os.path.exists(snap_file):
            try:
                with open(snap_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return data.get("plan")
            except Exception:
                pass
        return None

    def ensure_failsafe_snapshot(self, ticker, curr_p, prev_c, alloc_cash, q_data, total_kis_qty, avwap_qty):
        snap = self.load_daily_snapshot(ticker)
        if snap is not None:
            return snap
            
        pure_qty = max(0, total_kis_qty - avwap_qty)
        
        today_str_est = self._get_logical_date_str()
        legacy_lots = [item for item in q_data if not str(item.get("date", "")).startswith(today_str_est)]
        legacy_q = sum(int(item.get("qty", 0)) for item in legacy_lots if float(item.get('price', 0.0)) > 0)
        
        if pure_qty != legacy_q:
            logging.warning(f"⚠️ [{ticker}] V-REV 페일세이프 경고: KIS 순수 본대 수량({pure_qty}주)과 이월 큐 장부 수량({legacy_q}주) 불일치 감지. CALIB 비파괴 보정 또는 수동 동기화 요망.")
            
        logging.warning(f"🚨 [{ticker}] V_REV 스냅샷 증발 감지! 페일세이프 긴급 복원 가동 (KIS총잔고:{total_kis_qty} - 암살자:{avwap_qty} = 본대:{pure_qty}주 | 이월 큐 장부:{legacy_q}주)")
        
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

    def reset_residual(self, ticker):
        pass

    def record_execution(self, ticker, side, qty, exec_price):
        self._load_state_if_needed(ticker)
        safe_qty = int(float(qty or 0))
        safe_price = float(exec_price or 0.0)
        
        if side == "BUY":
            spent = safe_qty * safe_price
            self.executed["BUY_BUDGET"][ticker] = float(self.executed.get("BUY_BUDGET", {}).get(ticker, 0.0)) + spent
        else:
            self.executed["SELL_QTY"][ticker] = int(self.executed.get("SELL_QTY", {}).get(ticker, 0)) + safe_qty
        self._save_state(ticker)

    def get_dynamic_plan(self, ticker, curr_p, prev_c, current_weight, vwap_status, min_idx, alloc_cash, q_data, is_snapshot_mode=False, market_type="REG"):
        self._load_state_if_needed(ticker)

        valid_q_data = [item for item in q_data if float(item.get('price', 0.0)) > 0]
        total_q = sum(int(item.get("qty", 0)) for item in valid_q_data)
        total_inv = sum(float(item.get('qty', 0)) * float(item.get('price', 0.0)) for item in valid_q_data)
        avg_price = (total_inv / total_q) if total_q > 0 else 0.0
        
        dates_in_queue = sorted(list(set(item.get('date') for item in valid_q_data if item.get('date'))), reverse=True)
        l1_qty, l1_price = 0, 0.0
        
        if dates_in_queue:
            lots_1 = [item for item in valid_q_data if item.get('date') == dates_in_queue[0]]
            l1_qty = sum(int(item.get('qty', 0)) for item in lots_1)
            l1_price = sum(float(item.get('qty', 0)) * float(item.get('price', 0.0)) for item in lots_1) / l1_qty if l1_qty > 0 else 0.0
         
        upper_qty = total_q - l1_qty
        upper_inv = total_inv - (l1_qty * l1_price)
        upper_avg = upper_inv / upper_qty if upper_qty > 0 else 0.0

        trigger_jackpot = round(avg_price * 1.010, 2)
        trigger_l1 = round(l1_price * 1.006, 2)
        trigger_upper = round(upper_avg * 1.005, 2) if upper_qty > 0 else 0.0

        cached_plan = self.load_daily_snapshot(ticker)
        
        if is_snapshot_mode:
            is_zero_start_session = (total_q == 0)
        else:
            if cached_plan:
                is_zero_start_session = cached_plan.get("is_zero_start", cached_plan.get("snapshot_total_q", cached_plan.get("total_q", -1)) == 0)
            else:
                today_str_est = self._get_logical_date_str()
                legacy_lots = [item for item in valid_q_data if not str(item.get("date", "")).startswith(today_str_est)]
                legacy_q = sum(int(item.get("qty", 0)) for item in legacy_lots)
                is_zero_start_session = (legacy_q == 0)

        if is_zero_start_session or total_q == 0:
            side = "BUY"
            p1_trigger = round(prev_c * 1.15, 2)
            p2_trigger = round(prev_c * 0.999, 2)
        else:
            side = "SELL" if curr_p > prev_c else "BUY"
            p1_trigger = round(prev_c * 0.995, 2)
            p2_trigger = round(prev_c * 0.9725, 2)

        if total_q > 0:
             active_sell_targets = [t for t in [trigger_jackpot, trigger_l1, trigger_upper] if t > 0]
             if active_sell_targets:
                min_sell = min(active_sell_targets)
                if p1_trigger >= min_sell:
                    p1_trigger = max(0.01, round(min_sell - 0.01, 2))
                if p2_trigger >= min_sell:
                    p2_trigger = max(0.01, round(min_sell - 0.01, 2))

        orders = []

        total_spent = float(self.executed["BUY_BUDGET"].get(ticker, 0.0))
        
        # 🚨 MODIFIED: [V72.01 V-REV 1회 예산(15%) 하드 마진 캡(Cap) 락온]
        # 외부에서 거대 예산(alloc_cash)이 유입되더라도 절대 당일 1회 할당량(시드의 15%)
        # 잔여분을 초과할 수 없도록 수학적 하드 마진 클램핑 이식 완료.
        seed_val = float(self.cfg.get_seed(ticker) or 0.0)
        daily_limit = seed_val * 0.15
        
        safe_alloc_cash = min(float(alloc_cash), daily_limit) if daily_limit > 0 else float(alloc_cash)
        rem_budget = max(0.0, safe_alloc_cash - total_spent)
        
        if rem_budget > 0:
            # 🚨 MODIFIED: [V72.00] 1회 예산을 무조건 0.5회분씩 하드 분할 (예산 초과 금지)
            b1_budget = rem_budget * 0.5
            b2_budget = rem_budget * 0.5
            
            q1 = math.floor(b1_budget / p1_trigger) if p1_trigger > 0 else 0
            q2 = math.floor(b2_budget / p2_trigger) if p2_trigger > 0 else 0
            
            est_tz_check = ZoneInfo('America/New_York')
            is_dst_active = bool(datetime.now(est_tz_check).dst())
            start_t = "042500" if is_dst_active else "052500"
            end_t = "045500" if is_dst_active else "055500"
            
            # 🚨 MODIFIED: [V72.00] 10주 미만 시 LOC 스위칭 락온 적용
            if q1 > 0:
                ord_type = "VWAP" if q1 >= 10 else "LOC"
                desc_str = "VWAP매수(Buy1)" if ord_type == "VWAP" else "LOC매수(Buy1)"
                orders.append({"side": "BUY", "qty": q1, "price": p1_trigger, "type": ord_type, "start_time": start_t if ord_type == "VWAP" else None, "end_time": end_t if ord_type == "VWAP" else None, "desc": desc_str})
            if q2 > 0:
                ord_type = "VWAP" if q2 >= 10 else "LOC"
                desc_str = "VWAP매수(Buy2)" if ord_type == "VWAP" else "LOC매수(Buy2)"
                orders.append({"side": "BUY", "qty": q2, "price": p2_trigger, "type": ord_type, "start_time": start_t if ord_type == "VWAP" else None, "end_time": end_t if ord_type == "VWAP" else None, "desc": desc_str})
            
        rem_qty_total = max(0, int(total_q) - int(self.executed["SELL_QTY"].get(ticker, 0)))
        
        if rem_qty_total > 0:
            est_tz_check = ZoneInfo('America/New_York')
            is_dst_active = bool(datetime.now(est_tz_check).dst())
            start_t = "042500" if is_dst_active else "052500"
            end_t = "045500" if is_dst_active else "055500"
            
            available_l1 = min(l1_qty, rem_qty_total)
            l1_queued = 0
            if available_l1 > 0 and trigger_l1 > 0:
                ord_type = "VWAP" if available_l1 >= 10 else "LOC"
                desc_str = "Pop1(VWAP)" if ord_type == "VWAP" else "Pop1(LOC)"
                orders.append({"side": "SELL", "qty": available_l1, "price": trigger_l1, "type": ord_type, "start_time": start_t if ord_type == "VWAP" else None, "end_time": end_t if ord_type == "VWAP" else None, "desc": desc_str})
                l1_queued = available_l1
                
            available_upper = min(upper_qty, rem_qty_total - l1_queued)
            if available_upper > 0 and trigger_upper > 0:
                ord_type = "VWAP" if available_upper >= 10 else "LOC"
                desc_str = "Pop2(VWAP)" if ord_type == "VWAP" else "Pop2(LOC)"
                orders.append({"side": "SELL", "qty": available_upper, "price": trigger_upper, "type": ord_type, "start_time": start_t if ord_type == "VWAP" else None, "end_time": end_t if ord_type == "VWAP" else None, "desc": desc_str})
        
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
