"""
Created on 2025-07-01
V-REV 전용 LIFO 로트 장부, 스레드 세이프 코어 I/O 및 무결성 관리 (V71.00 무결점 방탄 아키텍처)
"""

import os
import json
import tempfile
import asyncio
import threading
import logging
from datetime import datetime
# NEW: [제3헌법, 제10경고] pytz 영구 적출 및 ZoneInfo 100% 락온
from zoneinfo import ZoneInfo

# 로깅 설정
logger = logging.getLogger(__name__)

# NEW: [제3헌법] 전역 타임존 단일 소스 락온
EST_TZ = ZoneInfo('America/New_York')

# I/O Race Condition 방어용 뮤텍스 락 (종목별 개별 락온)
_ledger_locks = {}

def _get_lock(symbol: str) -> threading.Lock:
    """종목별 스레드 세이프 락 획득"""
    # NEW: [제16경고] 스코프 리프트
    lock = None
    
    if symbol not in _ledger_locks:
        _ledger_locks[symbol] = threading.Lock()
    lock = _ledger_locks[symbol]
    return lock

def _get_filepath(symbol: str) -> str:
    """장부 파일 경로 반환"""
    return f"ledger_vrev_{symbol}.json"

# ==========================================
# 🏛️ 제4헌법: 멱등성 및 원자적 쓰기 코어 (동기 레이어)
# ==========================================
def _read_sync(symbol: str) -> list:
    """스레드 세이프가 보장된 상태에서 호출되는 장부 읽기"""
    # NEW: [제16경고] 스코프 리프트
    filepath = ""
    data = []
    
    try:
        filepath = _get_filepath(symbol)
        if os.path.exists(filepath):
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
    except Exception as e:
        logger.error(f"🚨 {symbol} 장부 데이터베이스 읽기 실패: {e}")
        
    return data

def _write_sync(symbol: str, data: list):
    """
    NEW: [제4헌법] 파일 파손 방지를 위한 임시 파일 및 os.replace 기반 원자적 쓰기(Atomic Write)
    """
    # NEW: [제16경고] 스코프 리프트
    filepath = ""
    temp_name = ""
    dir_name = ""
    
    try:
        filepath = _get_filepath(symbol)
        dir_name = os.path.dirname(filepath) or "."
        with tempfile.NamedTemporaryFile('w', dir=dir_name, delete=False, encoding='utf-8') as tf:
            json.dump(data, tf, indent=4, ensure_ascii=False)
            temp_name = tf.name
            
        os.replace(temp_name, filepath)
    except Exception as e:
        logger.error(f"🚨 {symbol} 장부 원자적 쓰기 중 치명적 오류: {e}")
        if temp_name and os.path.exists(temp_name):
            try:
                os.remove(temp_name)
            except:
                pass

# ==========================================
# 🛡️ 치명적 경고 2: 다이렉트 I/O 조작 스레드 세이프 코어
# ==========================================
def _delete_lot_sync(symbol: str, target_idx: int) -> bool:
    """지층 삭제 동기 코어 로직"""
    # NEW: [제16경고] 스코프 리프트
    lock = None
    data = []
    success = False
    
    lock = _get_lock(symbol)
    with lock:
        try:
            data = _read_sync(symbol)
            if 0 <= target_idx < len(data):
                data.pop(target_idx)
                _write_sync(symbol, data)
                success = True
            else:
                logger.warning(f"⚠️ {symbol} 장부 삭제 실패. 유효하지 않은 인덱스({target_idx})입니다.")
        except Exception as e:
            logger.error(f"🚨 {symbol} 장부 지층 삭제 중 오류 발생: {e}")
            
    return success

def _edit_lot_sync(symbol: str, target_idx: int, qty: int, price: float) -> bool:
    """지층 수정 동기 코어 로직"""
    # NEW: [제16경고] 스코프 리프트
    lock = None
    data = []
    success = False
    
    lock = _get_lock(symbol)
    with lock:
        try:
            data = _read_sync(symbol)
            if 0 <= target_idx < len(data):
                data[target_idx]['qty'] = qty
                data[target_idx]['price'] = price
                # NEW: [치명적 경고 1] 타임존 락온 갱신
                data[target_idx]['timestamp'] = datetime.now(EST_TZ).strftime("%Y-%m-%d %H:%M:%S")
                _write_sync(symbol, data)
                success = True
            else:
                logger.warning(f"⚠️ {symbol} 장부 수정 실패. 유효하지 않은 인덱스({target_idx})입니다.")
        except Exception as e:
            logger.error(f"🚨 {symbol} 장부 지층 수정 중 오류 발생: {e}")
            
    return success

def _add_lot_sync(symbol: str, qty: int, price: float) -> bool:
    """지층 추가 (매수 후 큐 장입 또는 비파괴 보정 CALIB 연동용)"""
    # NEW: [제16경고] 스코프 리프트
    lock = None
    data = []
    success = False
    new_lot = {}
    
    lock = _get_lock(symbol)
    with lock:
        try:
            data = _read_sync(symbol)
            new_lot = {
                'qty': qty,
                'price': price,
                'timestamp': datetime.now(EST_TZ).strftime("%Y-%m-%d %H:%M:%S")
            }
            data.append(new_lot)
            _write_sync(symbol, data)
            success = True
        except Exception as e:
            logger.error(f"🚨 {symbol} 장부 지층 추가 중 오류 발생: {e}")
            
    return success

def _overwrite_queue_sync(symbol: str, new_data: list) -> bool:
    """전체 장부 덮어쓰기 (수동 리셋/초기화 시 예외적 사용, 남용 금지)"""
    # NEW: [제16경고] 스코프 리프트
    lock = None
    success = False
    
    lock = _get_lock(symbol)
    with lock:
        try:
            _write_sync(symbol, new_data)
            success = True
        except Exception as e:
            logger.error(f"🚨 {symbol} 장부 전체 덮어쓰기 중 오류 발생: {e}")
            
    return success

def _get_total_qty_sync(symbol: str) -> int:
    """장부 총 보유 수량 합산"""
    # NEW: [제16경고] 스코프 리프트
    lock = None
    data = []
    total = 0
    
    lock = _get_lock(symbol)
    with lock:
        try:
            data = _read_sync(symbol)
            total = sum(int(item.get('qty', 0)) for item in data)
        except Exception as e:
            logger.error(f"🚨 {symbol} 장부 수량 합산 중 오류 발생: {e}")
            
    return total

# ==========================================
# ⚡ 제1헌법 & 치명적 경고 6: 비동기 래핑 API 레이어
# ==========================================

async def get_ledger(symbol: str) -> list:
    """비동기 장부 읽기"""
    # NEW: [제16경고] 스코프 리프트
    data = []
    try:
        data = await asyncio.wait_for(
            asyncio.to_thread(_read_sync, symbol),
            timeout=10.0
        )
    except asyncio.TimeoutError:
        logger.error(f"🚨 {symbol} 장부 조회 10초 타임아웃 피격. 메인 루프를 보호합니다.")
    except Exception as e:
        logger.error(f"🚨 {symbol} 비동기 장부 조회 중 오류: {e}")
    return data

async def delete_lot(symbol: str, target_idx: int) -> bool:
    """비동기 단일 지층 삭제"""
    # NEW: [제16경고] 스코프 리프트
    result = False
    try:
        result = await asyncio.wait_for(
            asyncio.to_thread(_delete_lot_sync, symbol, target_idx),
            timeout=10.0
        )
    except Exception as e:
        logger.error(f"🚨 {symbol} 비동기 삭제 호출 중 오류: {e}")
    return result

async def edit_lot(symbol: str, target_idx: int, qty: int, price: float) -> bool:
    """비동기 단일 지층 텍스트 수정"""
    # NEW: [제16경고] 스코프 리프트
    result = False
    try:
        result = await asyncio.wait_for(
            asyncio.to_thread(_edit_lot_sync, symbol, target_idx, qty, price),
            timeout=10.0
        )
    except Exception as e:
        logger.error(f"🚨 {symbol} 비동기 수정 호출 중 오류: {e}")
    return result

async def add_lot(symbol: str, qty: int, price: float) -> bool:
    """비동기 신규 지층 생성 (CALIB 연동)"""
    # NEW: [제16경고] 스코프 리프트
    result = False
    try:
        result = await asyncio.wait_for(
            asyncio.to_thread(_add_lot_sync, symbol, qty, price),
            timeout=10.0
        )
    except Exception as e:
        logger.error(f"🚨 {symbol} 비동기 추가 호출 중 오류: {e}")
    return result

async def overwrite_queue(symbol: str, new_data: list) -> bool:
    """비동기 전체 장부 덮어쓰기"""
    # NEW: [제16경고] 스코프 리프트
    result = False
    try:
        result = await asyncio.wait_for(
            asyncio.to_thread(_overwrite_queue_sync, symbol, new_data),
            timeout=10.0
        )
    except Exception as e:
        logger.error(f"🚨 {symbol} 비동기 덮어쓰기 호출 중 오류: {e}")
    return result

async def get_total_qty(symbol: str) -> int:
    """비동기 장부 총 수량 반환"""
    # NEW: [제16경고] 스코프 리프트
    total = 0
    try:
        total = await asyncio.wait_for(
            asyncio.to_thread(_get_total_qty_sync, symbol),
            timeout=10.0
        )
    except Exception as e:
        logger.error(f"🚨 {symbol} 비동기 수량 합산 중 오류: {e}")
    return total
