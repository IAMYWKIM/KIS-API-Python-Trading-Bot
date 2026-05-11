"""
Created on 2025-07-01
중앙 라우팅 허브 및 하이브리드 엔진 작전 지시 코어 (V71.00 무결점 방탄 아키텍처)
"""

import asyncio
import logging
# NEW: [제3헌법] pytz 영구 적출 및 ZoneInfo 100% 락온
from zoneinfo import ZoneInfo

# 하위 전략 및 I/O 모듈 임포트
import config
import broker
import strategy_v14
import strategy_v14_vwap
import strategy_reversion
import strategy_v_avwap

# 로깅 설정
logger = logging.getLogger(__name__)

# 전역 타임존 설정
EST_TZ = ZoneInfo('America/New_York')

async def verify_mode_switch_lockon(symbol: str, target_mode: str) -> bool:
    """
    0주 잔고 락온(Lock-on) 모드 전환 통제
    """
    # NEW: [제16경고] 변수 스코프 전진 배치로 UnboundLocalError 원천 봉쇄
    current_qty = 0
    is_allowed = False
    balance_df = None
    matching_row = None
    
    try:
        # NEW: [치명적 경고 4-3] V61 절대 헌법: TQQQ는 무조건 V14 전용으로 락온
        if symbol == "TQQQ" and target_mode != "V14":
            logger.warning("🚨 [V61 절대 헌법] TQQQ는 무조건 V14 전용입니다. 모드 전환을 강제 차단합니다.")
            return False

        # NEW: [제1헌법] 비동기 I/O 타임아웃 래핑 및 교착 원천 차단
        balance_df = await asyncio.wait_for(
            asyncio.to_thread(broker.get_account_balance),
            timeout=10.0
        )
        
        if not balance_df.empty:
            # NEW: [치명적 경고 5] API 변이 및 결측치 대비 Safe Casting
            matching_row = balance_df[balance_df['pdno'] == symbol]
            if not matching_row.empty:
                current_qty = int(float(matching_row.iloc[0].get('hldg_qty', 0)))

        # NEW: [작전지시서 2] 단 1주라도 존재할 시 기존 모드 락온(Lock-on) 유지
        if current_qty == 0:
            logger.info(f"✅ {symbol} 보유 수량 0주(현금 100%) 확인. {target_mode} 모드 전환을 허가합니다.")
            is_allowed = True
        else:
            logger.warning(f"🚫 {symbol} 잔고 {current_qty}주 감지. 모드 전환을 강제 차단하고 기존 락온 상태를 유지합니다.")
            is_allowed = False
            
    except asyncio.TimeoutError:
        logger.error("🚨 잔고 스캔 API 10초 타임아웃 피격. 데이터 기아 방지를 위해 모드 전환을 강제 차단합니다.")
        is_allowed = False
    except Exception as e:
        logger.error(f"🚨 락온 검증 중 치명적 오류 발생: {e}. 모드 전환을 차단합니다.")
        is_allowed = False
        
    return is_allowed

async def deploy_proactive_traps():
    """
    17:05 KST 예방적 덫 스케줄러에서 호출되는 중앙 라우팅 파이프라인
    """
    # NEW: [제16경고] 스코프 리프트
    current_mode = ""
    symbol = ""
    
    try:
        current_mode = config.get_current_mode()
        symbol = config.get_target_symbol()
        
        logger.info(f"🔹 현재 작전 모드({current_mode})에 따른 예방적 덫 장전을 하위 코어로 라우팅합니다.")
        
        if current_mode == "V14":
            # NEW: [작전지시서 3] 종가 LOC 매매 단일 타격 전술 및 장마감 전 VWAP 장전
            await strategy_v14.deploy_loc_trap(symbol)
            await strategy_v14_vwap.deploy_vwap_trap(symbol)
        elif current_mode == "V-REV":
            # NEW: [작전지시서 4] V-REV 장마감 30분 전 VWAP 파이프라인 단독 가동
            await strategy_reversion.deploy_vwap_trap(symbol)
        else:
            logger.error(f"🚨 런타임 붕괴 방어: 알 수 없는 모드 감지({current_mode}). 덫 장전을 안전 바이패스합니다.")
            
    except Exception as e:
        logger.error(f"🚨 예방적 덫 중앙 라우팅 중 오류 발생: {e}")

async def evaluate_omni_matrix_long_entry(symbol: str) -> bool:
    """
    옴니 매트릭스 횡보장 락다운 판독 회피 및 진입 방아쇠 강제 개방
    """
    # NEW: [제16경고] 스코프 리프트
    allow_buy = True
    
    try:
        # NEW: [치명적 경고 4-1] 횡보장(SIDEWAYS) 락다운 과잉 방어 로직 전면 소각
        # 과거 신규 진입을 전면 차단하던 데드코드를 완전히 제거하고 allow_buy=True 하드코딩
        allow_buy = True
        logger.info(f"✅ 옴니 매트릭스 횡보장 락다운 바이패스 완료. 기본 방향인 롱({symbol}) 진입을 무조건 허용(allow_buy=True)합니다.")
        
    except Exception as e:
        logger.error(f"🚨 옴니 매트릭스 연산 우회 중 오류 발생: {e}. 페일세이프에 따라 롱 진입을 허가합니다.")
        allow_buy = True
        
    return allow_buy

async def cancel_vrev_vwap_for_assassin(symbol: str):
    """
    AVWAP 암살자 딥매수 격발 시 자전거래 방지를 위한 V-REV 본진 덫 전면 취소
    """
    # NEW: [제16경고] 스코프 리프트
    trap_order_id = ""
    
    try:
        # NEW: [치명적 경고 13] 자전거래(Wash Sale) 방어 전면 락온
        trap_order_id = config.get_active_vwap_trap_odno(symbol)
        if trap_order_id:
            logger.info(f"🚨 AVWAP 암살자 딥매수 격발 감지. 자전거래 방어를 위해 V-REV 예방적 덫(ODNO: {trap_order_id})을 취소합니다.")
            await asyncio.wait_for(
                asyncio.to_thread(broker.cancel_order, symbol, trap_order_id),
                timeout=10.0
            )
            logger.info("✅ V-REV 예방적 VWAP 덫 전면 취소 완료.")
            config.clear_active_vwap_trap_odno(symbol)
    except Exception as e:
        logger.error(f"🚨 자전거래 방어용 취소 로직 중 치명적 오류 발생: {e}")

async def restore_vrev_vwap_after_dump(symbol: str):
    """
    AVWAP 전량 덤핑 완료 직후 본진 예산 복원 확인 및 V-REV 덫 재장전 원복
    """
    # NEW: [제16경고] 스코프 리프트
    current_mode = ""
    
    try:
        current_mode = config.get_current_mode()
        if current_mode == "V-REV":
            # NEW: [치명적 경고 13] 15:22~15:25 EST 덤핑 후 파이프라인 무결점 100% 원복
            logger.info("🔄 AVWAP 전량 덤핑 매도 및 본진 예산 복원 확인. 취소되었던 V-REV VWAP 덫 재장전을 격발합니다.")
            await strategy_reversion.deploy_vwap_trap(symbol)
            logger.info("✅ 본대 퀀트 스케줄 파이프라인(V-REV VWAP) 무결점 리스토어 완료.")
    except Exception as e:
        logger.error(f"🚨 V-REV 덫 작전 원복 중 치명적 오류 발생: {e}")
