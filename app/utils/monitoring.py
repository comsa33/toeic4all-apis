import asyncio
import platform
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

import psutil

from app.utils.db import mongodb
from app.utils.logger import logger


# 성능 데이터 저장용 클래스
class PerformanceMonitor:
    _instance = None
    _lock = asyncio.Lock()
    _data_points = []
    _max_data_points = 100
    _last_update = None
    _monitoring_task = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(PerformanceMonitor, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    async def initialize(self):
        """모니터링 초기화"""
        if self._initialized:
            return

        async with self._lock:
            if self._initialized:
                return

            self._data_points = []
            self._last_update = datetime.now()
            self._start_monitoring()
            self._initialized = True

    def _start_monitoring(self):
        """백그라운드 모니터링 작업 시작"""

        async def monitor_task():
            while True:
                try:
                    await self.collect_metrics()
                    await asyncio.sleep(60)  # 1분마다 수집
                except Exception as e:
                    logger.error(f"Error in monitoring task: {e}")
                    await asyncio.sleep(120)  # 오류 시 2분 대기

        if self._monitoring_task and not self._monitoring_task.done():
            self._monitoring_task.cancel()

        self._monitoring_task = asyncio.create_task(monitor_task())

    async def collect_metrics(self):
        """시스템 및 애플리케이션 지표 수집"""
        try:
            # 시스템 리소스 정보
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()

            # MongoDB 연결 정보
            db_stats = {"status": "unknown"}
            if mongodb._initialized:
                try:
                    db_stats = await mongodb.get_server_status()
                except Exception as e:
                    logger.error(f"Failed to get MongoDB stats: {e}")

            # 데이터 포인트 추가
            data_point = {
                "timestamp": datetime.now().isoformat(),
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "memory_available_mb": memory.available / (1024 * 1024),
                "db_connections": db_stats.get("connections", {}).get("current", 0),
                "db_available_connections": db_stats.get("connections", {}).get(
                    "available", 0
                ),
            }

            async with self._lock:
                self._data_points.append(data_point)
                # 최대 크기 제한
                if len(self._data_points) > self._max_data_points:
                    self._data_points = self._data_points[-self._max_data_points :]
                self._last_update = datetime.now()

        except Exception as e:
            logger.error(f"Error collecting metrics: {e}")

    async def get_metrics(self, timespan: Optional[int] = None) -> Dict[str, Any]:
        """수집된 지표 반환"""
        if not self._initialized:
            await self.initialize()

        async with self._lock:
            if not self._data_points:
                return {
                    "status": "no_data",
                    "message": "No metrics collected yet",
                    "last_update": (
                        self._last_update.isoformat() if self._last_update else None
                    ),
                }

            # 시간 범위 필터링
            filtered_data = self._data_points
            if timespan:
                cutoff = datetime.now() - timedelta(minutes=timespan)
                cutoff_iso = cutoff.isoformat()
                filtered_data = [
                    d for d in self._data_points if d["timestamp"] >= cutoff_iso
                ]

            # 최신 데이터
            latest = self._data_points[-1] if self._data_points else None

            # 평균값 계산
            if filtered_data:
                avg_cpu = sum(d["cpu_percent"] for d in filtered_data) / len(
                    filtered_data
                )
                avg_memory = sum(d["memory_percent"] for d in filtered_data) / len(
                    filtered_data
                )
                avg_connections = sum(
                    d.get("db_connections", 0) for d in filtered_data
                ) / len(filtered_data)
            else:
                avg_cpu = avg_memory = avg_connections = 0

            return {
                "status": "ok",
                "latest": latest,
                "averages": {
                    "cpu_percent": avg_cpu,
                    "memory_percent": avg_memory,
                    "db_connections": avg_connections,
                },
                "timespan_minutes": timespan,
                "data_points": len(filtered_data),
                "last_update": (
                    self._last_update.isoformat() if self._last_update else None
                ),
            }

    async def get_system_info(self) -> Dict[str, Any]:
        """시스템 정보 반환"""
        return {
            "platform": platform.platform(),
            "python_version": platform.python_version(),
            "processor": platform.processor(),
            "cpu_count": psutil.cpu_count(logical=True),
            "physical_cpu_count": psutil.cpu_count(logical=False),
            "memory_total_gb": psutil.virtual_memory().total / (1024**3),
            "hostname": platform.node(),
        }

    async def close(self):
        """모니터링 종료"""
        if self._monitoring_task:
            self._monitoring_task.cancel()
            self._initialized = False


# 싱글턴 인스턴스
monitor = PerformanceMonitor()


# FastAPI 의존성 주입을 위한 함수
async def get_performance_monitor():
    """성능 모니터 의존성 주입"""
    if not monitor._initialized:
        await monitor.initialize()
    return monitor
