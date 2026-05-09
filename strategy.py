# ==========================================================
# [strategy.py] - 🌟 2대 코어 + 하이브리드 라우터 완성본 🌟
# ⚠️ 이 주석 및 파일명 표기는 절대 지우지 마세요.
# 🚨 MODIFIED: [V32.00 그랜드 수술] 불필요한 AVWAP 동적 파라미터 수신 배선 완전 소각
# NEW: [V40.XX 옴니 매트릭스 절대 헌법] TQQQ(V14) / SOXS(V-REV) 런타임 강제 라우팅(Bypass) 쉴드 이식
# 🚨 MODIFIED: [V40.XX 옴니 매트릭스 전면 수술] 후행성 60MA/120MA 엔진 전면 소각 및
# 전일 VWAP vs 당일 실시간 VWAP 동행 지표(Coincident Indicator) 듀얼 모멘텀 엔진 수신 및 라우팅 락온
# [span_0](start_span)🚨 MODIFIED: [V43.00 작전 통제실 복구] AVWAP 사용자가 설정하는 커스텀 목표[span_0](end_span)
# 수익률(Target) 및 근무 모드(조기퇴근/다중출장) 파라미터를 하위 플러그인(strategy_v_avwap)으로 전달하는 라우터 배선 복구 완료.
# 🚨 MODIFIED: [V44.03 AVWAP 매수 방어] **kwargs 배선 개통으로 5일 ATR 등 신규 파라미터 주입 호환성 확보
# 🚨 MODIFIED: [V44.61 팩트 교정] VWAP 지배력(Dominance) 분석 시 프리마켓 거래량 노이즈 원천 차단 및 정규장 100% 락온
# 🚨 MODIFIED: [V54.06 SSOT 코어 통일 및 Split-Brain 영구 소각]
# 1) V_REV 모드 판별 시 억지스러운 is_active 플래그 의존도를 100% 소각하고, version="V_REV" 자체를 단일 진실 공급원(SSOT)으로 락온.
# 2) get_plan 내부 V_REV 더미 반환 시 is_reverse=True 로 강제 결속하여 UI 렌더링 엇박자(프랑켄슈타인 맹점) 완벽 해체.
# 🚨 MODIFIED: [V59.02 잔재 데드코드 영구 소각]
# [span_1](start_span)15:25 전량 덤핑 헌법에 따라 의미를 상실한 AVWAP 목표 수익률 및 다중 출장 모드[span_1](end_span)
# 파라미터 추출 배선 영구 적출 완료.
# 🚨 MODIFIED: [V60.00 옴니 매트릭스 락다운 엔진 전면 폐기]
# 기회비용을 훼손하던 apply_omni_matrix_filter 엔진 및 관련 매수 차단 로직 100% 영구 소각 완료.
# ==========================================================
import logging
import pandas as pd
from zoneinfo import ZoneInfo
from strategy_v14 import V14Strategy
from strategy_v_avwap import VAvwapHybridPlugin  
from strategy_reversion import ReversionStrategy
from strategy_v14_vwap import V14VwapStrategy

class InfiniteStrategy:
    
    def __init__(self, config):
        self.cfg = config
        self.v14_plugin = V14Strategy(config)
        self.v_avwap_plugin = VAvwapHybridPlugin()
        # [span_2](start_span)MODIFIED: [V42 U-Curve 락온 무결성 복구] ReversionStrategy 객체 생성 시 config 인자 주입 배선 100% 복구[span_2](end_span)
        # 🚨 [AI 에이전트 절대 주의 - 환각(Hallucination) 방어막] V42 U-Curve 락온 무결성 
        # [span_3](start_span)유지를 위해 config 주입을 훼손하지 말 것[span_3](end_span)
        self.v_rev_plugin = ReversionStrategy(config)
        self.v14_vwap_plugin = V14VwapStrategy(config)

    def analyze_vwap_dominance(self, df):
        if df is None or len(df) < 10:
            return {"vwap_price": 0.0, "is_strong_up": False, "is_strong_down": False}
            
        try:
            # [span_4](start_span)🚨 MODIFIED: [V44.61 팩트 수술] 프리마켓 거래량 노이즈가 지배력 연산을 오염시키는 맹점 원천 차단[span_4](end_span)
            # [AI 에이전트(Copilot/Claude) 절대 주의 - 환각(Hallucination) 방어막]
            # YF API가 프리마켓 데이터를 포함하여 반환하므로 순수 정규장 모멘텀만을 
            # [span_5](start_span)측정하기 위해 반드시 '093000' ~ '155900' 구간만 필터링해야 합니다.[span_5](end_span)
            if 'time_est' in df.columns:
                df = df[(df['time_est'] >= '093000') & (df['time_est'] <= '155900')]
            
            [span_6](start_span)if df.empty or len(df) < 10:[span_6](end_span)
                return {"vwap_price": 0.0, "is_strong_up": False, "is_strong_down": False}

            if 'high' in df.columns and 'low' in df.columns:
                typical_price = (df['high'].astype(float) + df['low'].astype(float) + df['close'].astype(float)) / 3.0
            else:
                typical_price = df['close'].astype(float)
              
            [span_7](start_span)vol_x_price = typical_price * df['volume'].astype(float)[span_7](end_span)
            total_vol = df['volume'].astype(float).sum()
            
            if total_vol == 0:
                return {"vwap_price": 0.0, "is_strong_up": False, "is_strong_down": False}
                
            vwap_price = vol_x_price.sum() / total_vol
      
            df_temp = pd.DataFrame()
            df_temp['volume'] = df['volume'].astype(float)
            df_temp['vol_x_price'] = vol_x_price
            df_temp['cum_vol'] = df_temp['volume'].cumsum()
            df_temp['cum_vol_price'] = df_temp['vol_x_price'].cumsum()
            [span_8](start_span)df_temp['running_vwap'] = df_temp['cum_vol_price'] / df_temp['cum_vol'][span_8](end_span)
            
            idx_10pct = int(len(df_temp) * 0.1)
            vwap_start = df_temp['running_vwap'].iloc[idx_10pct]
            vwap_end = df_temp['running_vwap'].iloc[-1]
            vwap_slope = vwap_end - vwap_start
            
            vol_above = df[df['close'].astype(float) > vwap_price]['volume'].astype(float).sum()
            
            [span_9](start_span)vol_above_pct = vol_above / total_vol if total_vol > 0 else 0[span_9](end_span)
            
            daily_open = df['open'].astype(float).iloc[0]
            daily_close = df['close'].astype(float).iloc[-1]
            
            is_up_day = daily_close > daily_open
            is_down_day = daily_close < daily_open
            
            [span_10](start_span)is_strong_up = is_up_day and (vwap_slope > 0) and (vol_above_pct > 0.60)[span_10](end_span)
            is_strong_down = is_down_day and (vwap_slope < 0) and ((1 - vol_above_pct) > 0.60)
            
            return {
                "vwap_price": round(vwap_price, 2),
                "is_strong_up": bool(is_strong_up),
                "is_strong_down": bool(is_strong_down),
                [span_11](start_span)"vol_above_pct": round(vol_above_pct, 4),[span_11](end_span)
                "vwap_slope": round(vwap_slope, 4)
            }
        except Exception:
            return {"vwap_price": 0.0, "is_strong_up": False, "is_strong_down": False}

    # MODIFIED: [V60.00] apply_omni_matrix_filter 메서드 영구 소각 완료.

    def get_plan(self, ticker, current_price, avg_price, qty, prev_close, ma_5day=0.0, market_type="REG", available_cash=0, is_simulation=False, vwap_status=None, is_snapshot_mode=False, regime_data=None):
        version = self.cfg.get_version(ticker)
        
        # [span_12](start_span)🚨 [V40.XX 절대 헌법] SOXS = V-REV 전용, TQQQ = V14 전용 강제 락온(Bypass)[span_12](end_span)
        if ticker.upper() == "SOXS" and version != "V_REV":
            logging.warning(f"🚨 [{ticker}] 절대 헌법 위반 감지. V_REV 모드로 강제 라우팅합니다.")
            self.cfg.set_version(ticker, "V_REV")
            version = "V_REV"
        [span_13](start_span)elif ticker.upper() == "TQQQ" and version != "V14":[span_13](end_span)
            logging.warning(f"🚨 [{ticker}] 절대 헌법 위반 감지. V14 모드로 강제 라우팅합니다.")
            self.cfg.set_version(ticker, "V14")
            version = "V14"

        if version in ["V13", "V17", "V_VWAP", "V_AVWAP"]:
            logging.warning(f"[{ticker}] 폐기된 레거시 모드({version}) 감지. V14 엔진으로 강제 라우팅합니다.")
            [span_14](start_span)self.cfg.set_version(ticker, "V14")[span_14](end_span)
            version = "V14"

        is_vwap_enabled = getattr(self.cfg, 'get_manual_vwap_mode', lambda x: False)(ticker)
        
        # 기본 플랜 산출
        if version == "V14" and is_vwap_enabled:
            plan = self.v14_vwap_plugin.get_plan(
                ticker=ticker, current_price=current_price, avg_price=avg_price, qty=qty,
                [span_15](start_span)prev_close=prev_close, ma_5day=ma_5day, market_type=market_type,[span_15](end_span)
                available_cash=available_cash, is_simulation=is_simulation,
                is_snapshot_mode=is_snapshot_mode
            )
        elif version == "V_REV":
            # 🚨 MODIFIED: [V54.06 SSOT 코어 통일 및 Split-Brain 영구 소각]
            # 🚨 [AI 에이전트(Copilot/Claude) 절대 주의 - 환각(Hallucination) 방어막]
            # [span_16](start_span)V_REV 모드라면 억지스러운 is_active 플래그 의존도를 완전히 소각하고 is_reverse를 True로 강제 락온(SSOT).[span_16](end_span)
            plan = {
                'core_orders': [], 'bonus_orders': [], 'orders': [],
                't_val': 0.0, 'is_reverse': True, 'star_price': 0.0, 'one_portion': 0.0
            }
        else:
            # [span_17](start_span)MODIFIED: [V44.58 라우팅 누수 디커플링 붕괴 엣지 케이스 수술] v14_plugin.get_plan 호출 시 is_snapshot_mode 파라미터 배선 팩트 복구 완료[span_17](end_span)
            plan = self.v14_plugin.get_plan(
                ticker=ticker, current_price=current_price, avg_price=avg_price, qty=qty,
                prev_close=prev_close, ma_5day=ma_5day, market_type=market_type,
                available_cash=available_cash, is_simulation=is_simulation, vwap_status=vwap_status,
                is_snapshot_mode=is_snapshot_mode
            )
            
        # MODIFIED: [V60.00] 옴니 매트릭스 필터(매수 락다운) 로직 100% 영구 소각 완료.
        # 이제 어떠한 시장 국면에서도 매수 주문은 강제 삭제되지 않으며 팩트 기반으로 전송됩니다.
                
        return plan

    def capture_vrev_snapshot(self, ticker, clear_price, avg_price, qty):
        if qty <= 0: return None
        
        raw_total_buy = avg_price * qty
        [span_18](start_span)raw_total_sell = clear_price * qty[span_18](end_span)
        
        fee_rate = self.cfg.get_fee(ticker) / 100.0
        net_invested = raw_total_buy * (1.0 + fee_rate)
        net_revenue = raw_total_sell * (1.0 - fee_rate)
        
        realized_pnl = net_revenue - net_invested
        realized_pnl_pct = (realized_pnl / net_invested) * 100 if net_invested > 0 else 0.0
        
        return {
            [span_19](start_span)"ticker": ticker,[span_19](end_span)
            "clear_price": clear_price,
            "avg_price": avg_price,
            "cleared_qty": qty,
            "realized_pnl": realized_pnl,
            "realized_pnl_pct": realized_pnl_pct,
            "captured_at": pd.Timestamp.now(tz=ZoneInfo('America/New_York'))
        }

    def load_avwap_state(self, ticker, now_est):
        if hasattr(self.v_avwap_plugin, 'load_state'):
            [span_20](start_span)return self.v_avwap_plugin.load_state(ticker, now_est)[span_20](end_span)
        return {}

    def save_avwap_state(self, ticker, now_est, state_data):
        if hasattr(self.v_avwap_plugin, 'save_state'):
            self.v_avwap_plugin.save_state(ticker, now_est, state_data)

    def fetch_avwap_macro(self, base_ticker):
        return self.v_avwap_plugin.fetch_macro_context(base_ticker)

    def get_avwap_decision(self, base_ticker, exec_ticker, base_curr_p, exec_curr_p, base_day_open, avg_price, qty, alloc_cash, context_data, df_1min_base, now_est, avwap_state=None, regime_data=None, **kwargs):
        
        # MODIFIED: [V60.00] AVWAP 옴니 매트릭스 락다운 필터 100% 영구 소각 완료.
        # 암살자는 이제 시장 국면과 상관없이 오직 타점 팩트만을 보고 타격을 집행합니다.

        # 🚨 MODIFIED: [V59.02 잔재 데드코드 영구 소각] target_profit 및 is_multi_strike 파라미터 추출 배선 영구 적출 완료
        # 🚨 [V44.03] 스나이퍼에서 수신한 체력 스캔 팩트 파라미터(**kwargs) 플러그인으로 바이패스
        return self.v_avwap_plugin.get_decision(
            base_ticker=base_ticker, exec_ticker=exec_ticker, base_curr_p=base_curr_p, exec_curr_p=exec_curr_p, 
            [span_21](start_span)base_day_open=base_day_open, avwap_avg_price=avg_price, avwap_qty=qty, avwap_alloc_cash=alloc_cash,[span_21](end_span)
            context_data=context_data, df_1min_base=df_1min_base, now_est=now_est, avwap_state=avwap_state, **kwargs
        )

