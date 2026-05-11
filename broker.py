"""
Created on 2025-07-01
KIS Open API 통신 및 데이터 파싱 코어 (V71.00 무결점 방탄 아키텍처)
"""

import sys
import logging
from typing import Optional
import pandas as pd

sys.path.extend(['../..', '.'])
import kis_auth as ka
import config

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_account_balance() -> pd.DataFrame:
    """
    계좌 실잔고 조회 및 뻥튀기(Double Counting) 중복 합산 절대 방어
    """
    # NEW: [제16경고] 스코프 리프트
    tr_cont = ""
    results = []
    seen_positions = set()
    df = pd.DataFrame()
    output_data = None
    params = {}
    res = None
    
    try:
        # NEW: [치명적 경고 3] 페이징(Pagination, tr_cont) 누락 방지를 위한 락온 반복문
        while True:
            params = {
                "CANO": config.get_cano(),
                "ACNT_PRDT_CD": config.get_acnt_prdt_cd(),
                "OVRS_EXCG_CD": "%",
                "TR_CRCY_CD": "USD",
                "CTX_AREA_FK200": "",
                "CTX_AREA_NK200": ""
            }
            
            res = ka._url_fetch(
                api_url="/uapi/overseas-stock/v1/trading/inquire-balance",
                ptr_id="TTTS3012R" if config.get_env_dv() == "real" else "VTTS3012R",
                tr_cont=tr_cont,
                params=params
            )
            
            if res.isOK():
                output_data = res.getBody().output1
                if isinstance(output_data, list):
                    for item in output_data:
                        # NEW: [치명적 경고 5] 결측치 방어 Safe Casting
                        pdno = str(item.get('ovrs_pdno', ''))
                        qty = float(item.get('ovrs_cblc_qty', 0.0))
                        price = float(item.get('pchs_avg_pric', 0.0))
                        
                        # NEW: [치명적 경고 3] 유령 중복 응답 멱등성 가드 (Double Counting 방어)
                        sig = (pdno, qty, price)
                        if sig in seen_positions:
                            logger.warning(f"🚨 {pdno} 다중 거래소 유령 중복 응답 감지. 누적 합산을 바이패스합니다.")
                            continue
                            
                        seen_positions.add(sig)
                        results.append({
                            'pdno': pdno,
                            'hldg_qty': qty,
                            'pchs_avg_pric': price
                        })
                else:
                    if output_data:
                        pdno = str(output_data.get('ovrs_pdno', ''))
                        qty = float(output_data.get('ovrs_cblc_qty', 0.0))
                        price = float(output_data.get('pchs_avg_pric', 0.0))
                        results.append({'pdno': pdno, 'hldg_qty': qty, 'pchs_avg_pric': price})
                
                tr_cont = res.getHeader().tr_cont
                if tr_cont not in ["M", "F"]:
                    break
            else:
                logger.error(f"🚨 잔고 조회 API 에러: {res.getErrorCode()} - {res.getErrorMessage()}")
                break
                
        df = pd.DataFrame(results)
        
    except Exception as e:
        logger.error(f"🚨 잔고 스캔 중 치명적 오류 발생: {e}")
        
    return df

def get_1min_candles_df(symbol: str) -> pd.DataFrame:
    """
    1분봉 데이터 파싱 및 하이킨아시 데이터 기아 방어
    """
    # NEW: [제16경고] 스코프 리프트
    df = pd.DataFrame()
    output_data = None
    params = {}
    res = None
    
    try:
        params = {
            "AUTH": "",
            "EXCD": config.get_exchange_code(symbol),
            "SYMB": symbol,
            "GUBN": "0",
            "BYMD": "",
            "MODP": "0"
        }
        
        res = ka._url_fetch(
            api_url="/uapi/overseas-price/v1/quotations/inquire-time-itemchartprice",
            ptr_id="HHDFS76950200",
            tr_cont="",
            params=params
        )
        
        if res.isOK():
            output_data = res.getBody().output2
            if isinstance(output_data, list):
                df = pd.DataFrame(output_data)
                
                if not df.empty:
                    # NEW: [치명적 경고 5] 하이킨아시 연산을 위한 open 컬럼 강제 수혈 보존
                    if 'open' not in df.columns:
                        if 'stck_oprc' in df.columns:
                            df['open'] = pd.to_numeric(df['stck_oprc'], errors='coerce').fillna(0.0)
                        else:
                            logger.warning(f"🚨 {symbol} 1분봉 open 컬럼 누락. close 컬럼으로 임시 수혈합니다.")
                            df['open'] = pd.to_numeric(df.get('close', df.get('stck_prpr', 0.0)), errors='coerce').fillna(0.0)
                            
                    df['high'] = pd.to_numeric(df.get('high', df.get('stck_hgpr', 0.0)), errors='coerce').fillna(0.0)
                    df['low'] = pd.to_numeric(df.get('low', df.get('stck_lwpr', 0.0)), errors='coerce').fillna(0.0)
                    df['close'] = pd.to_numeric(df.get('close', df.get('stck_prpr', 0.0)), errors='coerce').fillna(0.0)
                    df['time'] = df.get('stck_cntg_hour', '')
                    
    except Exception as e:
        logger.error(f"🚨 {symbol} 1분봉 파싱 중 치명적 오류 발생: {e}")
        
    return df

def get_current_price(symbol: str) -> float:
    """
    실시간 현재가 조회 및 Safe Casting 방어막
    """
    # NEW: [제16경고] 스코프 리프트
    current_price = 0.0
    params = {}
    res = None
    raw_price = None
    
    try:
        params = {
            "AUTH": "",
            "EXCD": config.get_exchange_code(symbol),
            "SYMB": symbol
        }
        
        res = ka._url_fetch(
            api_url="/uapi/overseas-price/v1/quotations/price",
            ptr_id="HHDFS76200200",
            tr_cont="",
            params=params
        )
        
        if res.isOK():
            # NEW: [치명적 경고 5] 결측치(None) 대비 Safe Casting (0.0 강제 형변환)
            raw_price = res.getBody().output.get('last', 0.0)
            current_price = float(raw_price) if raw_price is not None else 0.0
            
    except Exception as e:
        logger.error(f"🚨 {symbol} 현재가 조회 중 치명적 오류 발생: {e}")
        current_price = 0.0
        
    return current_price

def get_unfilled_orders(symbol: str) -> pd.DataFrame:
    """
    미체결 내역 조회 (팬텀 필 및 8초 교차 검증용)
    """
    # NEW: [제16경고] 스코프 리프트
    df = pd.DataFrame()
    results = []
    params = {}
    res = None
    output_data = None
    
    try:
        params = {
            "CANO": config.get_cano(),
            "ACNT_PRDT_CD": config.get_acnt_prdt_cd(),
            "OVRS_EXCG_CD": config.get_exchange_code(symbol),
            "SORT_SQN": "DSND",
            "CTX_AREA_FK200": "",
            "CTX_AREA_NK200": ""
        }
        
        res = ka._url_fetch(
            api_url="/uapi/overseas-stock/v1/trading/inquire-nccs",
            ptr_id="TTTS3018R" if config.get_env_dv() == "real" else "VTTS3018R",
            tr_cont="",
            params=params
        )
        
        if res.isOK():
            output_data = res.getBody().output
            if isinstance(output_data, list):
                for item in output_data:
                    if str(item.get('pdno', '')) == symbol:
                        results.append(item)
            df = pd.DataFrame(results)
            
    except Exception as e:
        logger.error(f"🚨 {symbol} 미체결 조회 중 치명적 오류 발생: {e}")
        
    return df

def cancel_order(symbol: str, odno: str) -> bool:
    """
    자전거래 방지 및 덫 취소 연동 코어 (order_rvsecncl 기반)
    """
    # NEW: [제16경고] 스코프 리프트
    is_success = False
    params = {}
    res = None
    
    try:
        params = {
            "CANO": config.get_cano(),
            "ACNT_PRDT_CD": config.get_acnt_prdt_cd(),
            "OVRS_EXCG_CD": config.get_exchange_code(symbol),
            "PDNO": symbol,
            "ORGN_ODNO": odno,
            "RVSE_CNCL_DVSN_CD": "02",  # 02: 취소
            "ORD_QTY": "0",
            "OVRS_ORD_UNPR": "0",
            "MGCO_APTM_ODNO": "",
            "ORD_SVR_DVSN_CD": "0"
        }
        
        res = ka._url_fetch(
            api_url="/uapi/overseas-stock/v1/trading/order-rvsecncl",
            ptr_id="TTTT1004U" if config.get_env_dv() == "real" else "VTTT1004U",
            tr_cont="",
            params=params,
            postFlag=True
        )
        
        if res.isOK():
            logger.info(f"✅ {symbol} 주문({odno}) 전면 취소 완료.")
            is_success = True
        else:
            logger.error(f"🚨 {symbol} 주문 취소 실패: {res.getErrorMessage()}")
            
    except Exception as e:
        logger.error(f"🚨 {symbol} 주문 취소 중 치명적 오류 발생: {e}")
        
    return is_success

def order(
    cano: str,
    acnt_prdt_cd: str,
    ovrs_excg_cd: str,
    pdno: str,
    ord_qty: str,
    ovrs_ord_unpr: str,
    ord_dv: str,
    ctac_tlno: str,
    mgco_aptm_odno: str,
    ord_svr_dvsn_cd: str,
    ord_dvsn: str,
    env_dv: str = "real",
) -> Optional[pd.DataFrame]:
    """
    [해외주식] 주문/계좌 > 해외주식 주문 [v1_해외주식-001]
    """
    # NEW: [제16경고] 스코프 리프트
    tr_id = ""
    sll_type = ""
    params = {}
    res = None
    output_data = None
    dataframe = pd.DataFrame()

    if ord_dv == "buy":
        if ovrs_excg_cd in ("NASD", "NYSE", "AMEX"):
            tr_id = "TTTT1002U"
        else:
            tr_id = "TTTS1002U"
        sll_type = ""
    elif ord_dv == "sell":
        if ovrs_excg_cd in ("NASD", "NYSE", "AMEX"):
            tr_id = "TTTT1006U"
        else:
            tr_id = "TTTS1001U"
        sll_type = "00"

    if env_dv == "demo":
        tr_id = "V" + tr_id[1:]

    params = {
        "CANO": cano,
        "ACNT_PRDT_CD": acnt_prdt_cd,
        "OVRS_EXCG_CD": ovrs_excg_cd,
        "PDNO": pdno,
        "ORD_QTY": ord_qty,
        "OVRS_ORD_UNPR": ovrs_ord_unpr,
        "CTAC_TLNO": ctac_tlno,
        "MGCO_APTM_ODNO": mgco_aptm_odno,
        "SLL_TYPE": sll_type,
        "ORD_SVR_DVSN_CD": ord_svr_dvsn_cd,
        "ORD_DVSN": ord_dvsn,
    }

    res = ka._url_fetch(
        api_url="/uapi/overseas-stock/v1/trading/order",
        ptr_id=tr_id,
        tr_cont="",
        params=params,
        postFlag=True
    )

    if res.isOK():
        if hasattr(res.getBody(), 'output'):
            output_data = res.getBody().output
            if not isinstance(output_data, list):
                output_data = [output_data]
            dataframe = pd.DataFrame(output_data)
        logger.info("Data fetch complete.")
        return dataframe
    else:
        logger.error(f"API call failed: {res.getErrorCode()} - {res.getErrorMessage()}")
        return pd.DataFrame()

def order_resv(
    env_dv: str,
    ord_dv: str,
    cano: str,
    acnt_prdt_cd: str,
    pdno: str,
    ovrs_excg_cd: str,
    ft_ord_qty: str,
    ft_ord_unpr3: str,
    sll_buy_dvsn_cd: Optional[str] = "",
    rvse_cncl_dvsn_cd: Optional[str] = "",
    prdt_type_cd: Optional[str] = "",
    ord_svr_dvsn_cd: Optional[str] = "",
    rsvn_ord_rcit_dt: Optional[str] = "",
    ord_dvsn: Optional[str] = "",
    ovrs_rsvn_odno: Optional[str] = "",
    algo_ord_tmd_dvsn_cd: Optional[str] = ""
) -> pd.DataFrame:
    """
    [해외주식] 예약주문접수[v1_해외주식-002] (VWAP 알고리즘 덫 장전용)
    """
    # NEW: [제16경고] 스코프 리프트
    tr_id = ""
    params = {}
    res = None
    current_data = pd.DataFrame()

    if env_dv == "real":
        if ord_dv == "usBuy": tr_id = "TTTT3014U"
        elif ord_dv == "usSell": tr_id = "TTTT3016U"
        else: tr_id = "TTTS3013U"
    elif env_dv == "demo":
        if ord_dv == "usBuy": tr_id = "VTTT3014U"
        elif ord_dv == "usSell": tr_id = "VTTT3016U"
        else: tr_id = "VTTS3013U"

    params = {
        "CANO": cano,
        "ACNT_PRDT_CD": acnt_prdt_cd,
        "PDNO": pdno,
        "OVRS_EXCG_CD": ovrs_excg_cd,
        "FT_ORD_QTY": ft_ord_qty,
        "FT_ORD_UNPR3": ft_ord_unpr3
    }
    
    if sll_buy_dvsn_cd: params["SLL_BUY_DVSN_CD"] = sll_buy_dvsn_cd
    if rvse_cncl_dvsn_cd: params["RVSE_CNCL_DVSN_CD"] = rvse_cncl_dvsn_cd
    if prdt_type_cd: params["PRDT_TYPE_CD"] = prdt_type_cd
    if ord_svr_dvsn_cd: params["ORD_SVR_DVSN_CD"] = ord_svr_dvsn_cd
    if rsvn_ord_rcit_dt: params["RSVN_ORD_RCIT_DT"] = rsvn_ord_rcit_dt
    if ord_dvsn: params["ORD_DVSN"] = ord_dvsn
    if ovrs_rsvn_odno: params["OVRS_RSVN_ODNO"] = ovrs_rsvn_odno
    if algo_ord_tmd_dvsn_cd: params["ALGO_ORD_TMD_DVSN_CD"] = algo_ord_tmd_dvsn_cd
    
    res = ka._url_fetch(
        api_url="/uapi/overseas-stock/v1/trading/order-resv",
        ptr_id=tr_id,
        tr_cont="",
        params=params,
        postFlag=True
    )
    
    if res.isOK():
        current_data = pd.DataFrame(res.getBody().output, index=[0])
        logger.info("Data fetch complete.")
        return current_data
    else:
        logger.error(f"API call failed: {res.getErrorCode()} - {res.getErrorMessage()}")
        return pd.DataFrame()
