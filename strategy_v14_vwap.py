"""
Created on 2025-07-01
V14 공식 기반 장 마감 30분 전 KIS 자체 VWAP 알고리즘 타겟 연산 플러그인 (V71.00 무결점 방탄 아키텍처)
"""

import asyncio
import logging
import time
from datetime import datetime
# NEW: [제3헌법, 제10경고] pytz 영구 적출 및 ZoneInfo 100% 락온
from zoneinfo import ZoneInfo

import config
import broker

# 로깅 설정
logger = logging.getLogger(__name__)

# NEW: [제3헌법] 전역 타임존 단일 소스 락온
EST_TZ = ZoneInfo('America/New_York')

# L1 인메모리 캐시 (팬텀 필 및 자전거래 방어용 타임스탬프 저장소)
_last_vwap_order_cache = {}

async def verify_vwap_phantom_fill(symbol: str) -> bool:
    """
    원장 동기화 지연(Lag)에 따른 유령 체결(Phantom Fill) 8초 교차 검증 코어 (VWAP 전용)
    """
    # NEW: [제16경고] 스코프 리프트 (UnboundLocalError 원천 봉쇄)
    current_time = 0.0
    last_time = 0.0
    is_safe = True
    
    try:
        current_time = time.time()
        last_time = _last_vwap_order_cache.get(symbol, 0.0)
        
        # NEW: [치명적 경고 7] 8초 다중 교차 검증 엔진 통과 여부 하드코딩
        if current_time - last_time < 8.0:
            logger.warning(f"🚨 {symbol} 8초 이내 VWAP 중복 타격 징후 감지. 유령 체결(Phantom Fill) 방어를 위해 진입을 강제 차단합니다.")
            return False
            
        # VWAP 알고리즘 예약 주문의 경우 일반 미체결(unfilled_df) 스캔 대신 L1 캐시에 전적으로 의존하여 멱등성 방어
        is_safe = True
                    
    except Exception as e:
        logger.error(f"🚨 VWAP 팬텀 필 검증 중 런타임 붕괴 방어 ({e}). 타격을 차단합니다.")
        is_safe = False
        
    return is_safe

async def deploy_vwap_trap(symbol: str):
    """
    V14 장 마감 30분 전 KIS 자체 VWAP 알고리즘 타겟 예방적 덫 주문 격발 파이프라인
    """
    # NEW: [제16경고] 스코프 리프트 (모든 참조 변수 최상단 전진 배치)
    is_safe_to_order = False
    daily_budget = 0.0
    current_price = 0.0
    order_qty = 0
    order_res = None
    est_today_str = ""
    
    try:
        # NEW: [치명적 경고 1] 논리적 시계열 EST 100% 종속 캐싱용 날짜 추출
        est_today_str = datetime.now(EST_TZ).strftime("%Y-%m-%d")
        logger.info(f"🔹 [{est_today_str} EST] {symbol} V14 하이브리드 VWAP 알고리즘 덫 장전 시퀀스를 개시합니다.")
        
        # 1. 팬텀 필 및 이중 타격 방어막 검증
        is_safe_to_order = await verify_vwap_phantom_fill(symbol)
        if not is_safe_to_order:
            logger.warning(f"🚫 {symbol} VWAP 덫 장전이 락온 방어막에 의해 바이패스 되었습니다.")
            return
            
        # 2. 예산 할당 및 현재가 파싱
        daily_budget = float(config.get_daily_budget(symbol))
        
        # NEW: [제1헌법] 현재가 수신 동기 I/O 비동기 격리 및 블로킹 원천 차단
        current_price = await asyncio.wait_for(
            asyncio.to_thread(broker.get_current_price, symbol),
            timeout=10.0
        )
        
        # NEW: [치명적 경고 5] 현재가 결측치 0.0 이하 유입 런타임 붕괴 방어
        if current_price <= 0.0:
            logger.error(f"🚨 {symbol} 현재가 수신 실패(결측치 감지). VWAP 덫 장전을 강제 종료합니다.")
            return
            
        # 3. 타격 물량 정밀 연산
        order_qty = int(daily_budget // current_price)
        if order_qty <= 0:
            logger.warning(f"⚠️ {symbol} 1일 차 예산({daily_budget}$)이 현재가({current_price}$)를 하회하여 매수가 불가능합니다. VWAP 주문을 스킵합니다.")
            return
            
        # 4. KIS 서버로 VWAP 알고리즘 예약 주문(02) 덫 격발
        logger.info(f"🚀 {symbol} {order_qty}주 VWAP(02) 예방적 덫 주문을 KIS 서버로 전송합니다.")
        
        # NEW: [제1헌법] 예약/알고리즘 주문 API (order_resv) 호출 및 10초 타임아웃 족쇄
        order_res = await asyncio.wait_for(
            asyncio.to_thread(
                broker.order_resv,
                env_dv=config.get_env_dv(),
                ord_dv="usBuy",
                cano=config.get_cano(),
                acnt_prdt_cd=config.get_acnt_prdt_cd(),
                pdno=symbol,
                ovrs_excg_cd=config.get_exchange_code(symbol),
                ft_ord_qty=str(order_qty),
                ft_ord_unpr3="0",  # 시장가 기준 주문 단가 0 세팅
                algo_ord_tmd_dvsn_cd="02"  # NEW: KIS 알고리즘주문시간구분코드 (02: VWAP 전용 락온)
            ),
            timeout=10.0
        )
        
        # NEW: [치명적 경고 5] DataFrame 결측치 및 빈 객체 Safe Casting
        if order_res is not None and not order_res.empty:
            logger.info(f"✅ {symbol} V14 VWAP 덫 장전이 무결점으로 완료되었습니다. ODNO 타임스탬프를 캐싱합니다.")
            # NEW: [치명적 경고 7] 타격 직후 L1 캐시에 현재 시각 기록하여 8초 락온 방어 활성화
            _last_vwap_order_cache[symbol] = time.time()
        else:
            logger.error(f"🚨 {symbol} VWAP 덫 API 전송 실패. 반환 DataFrame이 비어 있습니다.")
            
    except asyncio.TimeoutError:
        logger.error("🚨 VWAP 예약 주문 전송 중 10초 타임아웃 피격. 교착(Deadlock) 방지를 위해 프로세스를 반환합니다.")
    except Exception as e:
        logger.error(f"🚨 VWAP 덫 장전 중 치명적 런타임 오류 발생: {e}", exc_info=True)
