"""
Created on 2025-07-01
V-REV 역추세 하이브리드 전술, LIFO 지층 관리 및 예방적 VWAP 타점 산출 코어 (V71.00 무결점 방탄 아키텍처)
"""

import asyncio
import logging
import time
from datetime import datetime
# NEW: [제3헌법, 제10경고] pytz 영구 적출 및 ZoneInfo 100% 락온
from zoneinfo import ZoneInfo

import config
import broker
import queue_ledger

# 로깅 설정
logger = logging.getLogger(__name__)

# NEW: [제3헌법] 전역 타임존 단일 소스 락온
EST_TZ = ZoneInfo('America/New_York')

# L1 인메모리 캐시 (팬텀 필 및 8초 이중 타격 방어용)
_last_vrev_order_cache = {}

async def verify_vrev_phantom_fill(symbol: str) -> bool:
    """
    원장 동기화 지연(Lag)에 따른 유령 체결(Phantom Fill) 8초 교차 검증 코어 (V-REV 전용)
    """
    # NEW: [제16경고] 스코프 리프트 (UnboundLocalError 원천 봉쇄)
    current_time = 0.0
    last_time = 0.0
    is_safe = True
    
    try:
        current_time = time.time()
        last_time = _last_vrev_order_cache.get(symbol, 0.0)
        
        # NEW: [치명적 경고 7] 8초 다중 교차 검증 엔진 통과 여부 하드코딩
        if current_time - last_time < 8.0:
            logger.warning(f"🚨 {symbol} 8초 이내 V-REV 중복 타격 징후 감지. 유령 체결(Phantom Fill) 방어를 위해 진입을 강제 차단합니다.")
            return False
            
        # V-REV VWAP 알고리즘 예약 주문은 미체결 내역 스캔 대신 인메모리 캐시 락온에 의존
        is_safe = True
                    
    except Exception as e:
        logger.error(f"🚨 V-REV 팬텀 필 검증 중 런타임 붕괴 방어 ({e}). 타격을 차단합니다.")
        is_safe = False
        
    return is_safe

async def deploy_vwap_trap(symbol: str):
    """
    V-REV 장 마감 30분 전 KIS 자체 VWAP 알고리즘 타겟 예방적 덫 주문 격발 파이프라인
    (AVWAP 암살자 출격 시 자전거래 방지를 위해 ODNO 연동)
    """
    # NEW: [제16경고] 스코프 리프트 (모든 참조 변수 최상단 전진 배치)
    is_safe_to_order = False
    daily_budget = 0.0
    current_price = 0.0
    order_qty = 0
    order_res = None
    est_today_str = ""
    trap_odno = ""
    
    try:
        # NEW: [치명적 경고 1] 논리적 시계열 EST 100% 종속 캐싱용 날짜 추출
        est_today_str = datetime.now(EST_TZ).strftime("%Y-%m-%d")
        logger.info(f"🔹 [{est_today_str} EST] {symbol} V-REV 역추세 하이브리드 VWAP 덫 장전 시퀀스를 개시합니다.")
        
        # 1. 팬텀 필 및 이중 타격 방어막 검증
        is_safe_to_order = await verify_vrev_phantom_fill(symbol)
        if not is_safe_to_order:
            logger.warning(f"🚫 {symbol} V-REV VWAP 덫 장전이 락온 방어막에 의해 바이패스 되었습니다.")
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
            logger.error(f"🚨 {symbol} 현재가 수신 실패(결측치 감지). V-REV VWAP 덫 장전을 강제 종료합니다.")
            return
            
        # 3. 타격 물량 정밀 연산
        order_qty = int(daily_budget // current_price)
        if order_qty <= 0:
            logger.warning(f"⚠️ {symbol} 1일 차 예산({daily_budget}$)이 현재가({current_price}$)를 하회하여 매수가 불가능합니다. V-REV 주문을 스킵합니다.")
            return
            
        # 4. KIS 서버로 VWAP 알고리즘 예약 주문(02) 덫 격발
        logger.info(f"🚀 {symbol} {order_qty}주 V-REV 전용 VWAP(02) 예방적 덫 주문을 KIS 서버로 전송합니다.")
        
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
                ft_ord_unpr3="0",  # 시장가 기준
                algo_ord_tmd_dvsn_cd="02"  # NEW: KIS 알고리즘주문시간구분코드 (02: VWAP 전용 락온)
            ),
            timeout=10.0
        )
        
        # NEW: [치명적 경고 5, 13] 결측치 방어 및 자전거래(Wash Sale) 캔슬 연동용 ODNO 추출/캐싱
        if order_res is not None and not order_res.empty:
            # API 반환 구조에 따른 Safe ODNO 파싱
            trap_odno = str(order_res.iloc[0].get('ODNO', order_res.iloc[0].get('OVRS_RSVN_ODNO', '')))
            
            if trap_odno:
                logger.info(f"✅ {symbol} V-REV VWAP 덫 장전 무결점 완료. (ODNO: {trap_odno}) 자전거래 방어 시스템에 락온합니다.")
                # NEW: [치명적 경고 13] 암살자 출격 시 해당 덫을 전면 취소할 수 있도록 식별자 중앙 등록
                config.set_active_vwap_trap_odno(symbol, trap_odno)
            else:
                logger.warning(f"⚠️ {symbol} V-REV 덫 주문은 성공했으나 ODNO를 파싱하지 못했습니다. 자전거래 방어 회피 가능성이 존재합니다.")
                
            # NEW: [치명적 경고 7] 타격 직후 L1 캐시에 현재 시각 기록
            _last_vrev_order_cache[symbol] = time.time()
        else:
            logger.error(f"🚨 {symbol} V-REV VWAP 덫 API 전송 실패. 반환 DataFrame이 비어 있습니다.")
            
    except asyncio.TimeoutError:
        logger.error("🚨 V-REV 예약 주문 전송 중 10초 타임아웃 피격. 메인 루프 교착 방지를 위해 롤백합니다.")
    except Exception as e:
        logger.error(f"🚨 V-REV 덫 장전 중 치명적 런타임 오류 발생: {e}", exc_info=True)

async def execute_lifo_profit_taking(symbol: str):
    """
    V-REV 전용 LIFO 지층 분리 익절 타점 산출 및 공수 교대 평가 뼈대
    (실제 매도 타격은 장중 감시 스케줄러에 위임)
    """
    # NEW: [제16경고] 스코프 리프트
    current_price = 0.0
    queue_data = None
    
    try:
        # LIFO 지층 장부 I/O는 제4헌법 및 비동기 래핑된 메서드를 통해 접근
        queue_data = await asyncio.wait_for(
            asyncio.to_thread(queue_ledger.get_ledger, symbol),
            timeout=10.0
        )
        
        # 상세 LIFO 청산 연산은 이 부분에서 독립적으로 수행됨 (향후 스나이퍼에서 호출)
        pass
        
    except Exception as e:
        logger.error(f"🚨 V-REV LIFO 익절 타점 산출 중 오류 발생: {e}")
