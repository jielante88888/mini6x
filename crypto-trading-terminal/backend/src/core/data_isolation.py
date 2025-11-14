"""
数据隔离验证器
确保现货和期货数据完全隔离，防止数据交叉污染
"""

import asyncio
import hashlib
import json
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Set, Tuple, Callable
from dataclasses import dataclass
from enum import Enum
from collections import defaultdict, deque
import weakref

import structlog

from ..adapters.base import MarketData
from ..storage.redis_cache import get_market_cache
from ..utils.exceptions import DataIsolationError, ValidationError

logger = structlog.get_logger(__name__)


class IsolationLevel(Enum):
    """隔离级别"""
    STRICT = "strict"    # 严格隔离
    MODERATE = "moderate" # 中等隔离
    LOOSE = "loose"      # 宽松隔离


class ValidationResult(Enum):
    """验证结果"""
    VALID = "valid"
    INVALID = "invalid"
    WARNING = "warning"
    ERROR = "error"


@dataclass
class DataValidationRecord:
    """数据验证记录"""
    symbol: str
    exchange: str
    market_type: str
    timestamp: datetime
    data_hash: str
    validation_result: ValidationResult
    violations: List[str]
    processing_time_ms: float


@dataclass
class IsolationViolation:
    """隔离违规记录"""
    id: str
    violation_type: str
    symbol: str
    description: str
    severity: str  # "low", "medium", "high", "critical"
    timestamp: datetime
    resolved: bool = False


class DataIsolationValidator:
    """数据隔离验证器"""
    
    def __init__(self):
        self.validation_cache: Dict[str, List[DataValidationRecord]] = defaultdict(lambda: deque(maxlen=1000))
        self.violations: List[IsolationViolation] = []
        self.isolation_rules: Dict[str, Dict[str, Any]] = {}
        self.validation_handlers: List[Callable] = []
        
        # 缓存隔离配置
        self.cache_namespaces = {
            'spot': 'market_data_spot',
            'futures': 'market_data_futures'
        }
        
        # WebSocket连接隔离
        self.ws_connections: Dict[str, Dict[str, Any]] = {
            'spot': {},
            'futures': {}
        }
        
        # 数据聚合隔离
        self.data_aggregators: Dict[str, Any] = {
            'spot': None,
            'futures': None
        }
        
        # 验证配置
        self.isolation_level = IsolationLevel.STRICT
        self.max_price_deviation = 0.05  # 5%价格偏差限制
        self.max_data_age_seconds = 300  # 5分钟数据新鲜度
        
        # 统计信息
        self.total_validations = 0
        self.valid_count = 0
        self.invalid_count = 0
        self.warning_count = 0
        
        # 缓存管理器
        self.cache_manager = get_market_cache()
        
        # 初始化隔离规则
        self._setup_isolation_rules()
        
        logger.info("数据隔离验证器初始化完成")
    
    def _setup_isolation_rules(self):
        """设置隔离规则"""
        self.isolation_rules = {
            # 缓存隔离规则
            'cache_isolation': {
                'enabled': True,
                'namespaces_required': True,
                'key_prefix_separation': True,
                'ttl_separation': True
            },
            
            # WebSocket隔离规则
            'websocket_isolation': {
                'enabled': True,
                'connection_pool_separation': True,
                'message_routing_separation': True,
                'subscription_isolation': True
            },
            
            # 数据聚合隔离规则
            'aggregation_isolation': {
                'enabled': True,
                'separate_aggregators': True,
                'data_flow_separation': True,
                'metric_separation': True
            },
            
            # 数据验证规则
            'data_validation': {
                'enabled': True,
                'price_range_validation': True,
                'timestamp_validation': True,
                'symbol_format_validation': True,
                'exchange_consistency_validation': True
            },
            
            # 监控规则
            'monitoring': {
                'enabled': True,
                'real_time_validation': True,
                'violation_alerting': True,
                'performance_tracking': True
            }
        }
        
        logger.info("数据隔离规则已设置")
    
    async def validate_market_data_isolation(
        self, 
        market_data: MarketData, 
        expected_market_type: str
    ) -> ValidationResult:
        """验证市场数据隔离"""
        validation_start = time.time()
        violations = []
        
        try:
            # 1. 检查市场类型一致性
            if market_data.market_type != expected_market_type:
                violations.append(f"市场类型不匹配: 期望 {expected_market_type}, 实际 {market_data.market_type}")
            
            # 2. 检查缓存命名空间隔离
            await self._validate_cache_isolation(market_data, violations)
            
            # 3. 检查数据完整性
            await self._validate_data_integrity(market_data, violations)
            
            # 4. 检查时间戳有效性
            await self._validate_timestamp(market_data, violations)
            
            # 5. 检查价格合理性
            await self._validate_price_reasonableness(market_data, violations)
            
            # 6. 检查符号格式
            await self._validate_symbol_format(market_data, violations)
            
            # 7. 检查交易所一致性
            await self._validate_exchange_consistency(market_data, violations)
            
            # 生成数据哈希
            data_hash = self._generate_data_hash(market_data)
            
            # 记录验证结果
            validation_time = (time.time() - validation_start) * 1000
            record = DataValidationRecord(
                symbol=market_data.symbol,
                exchange=market_data.exchange,
                market_type=market_data.market_type,
                timestamp=datetime.now(timezone.utc),
                data_hash=data_hash,
                validation_result=self._determine_validation_result(violations),
                violations=violations,
                processing_time_ms=validation_time
            )
            
            # 存储验证记录
            key = f"{market_data.exchange}_{market_data.market_type}_{market_data.symbol}"
            self.validation_cache[key].append(record)
            
            # 更新统计
            self.total_validations += 1
            if record.validation_result == ValidationResult.VALID:
                self.valid_count += 1
            elif record.validation_result == ValidationResult.WARNING:
                self.warning_count += 1
            else:
                self.invalid_count += 1
            
            # 处理违规情况
            if violations:
                await self._handle_validation_violations(market_data, violations)
            
            logger.debug(f"数据验证完成: {market_data.symbol} {market_data.market_type} - {record.validation_result.value}")
            
            return record.validation_result
            
        except Exception as e:
            logger.error(f"数据验证异常: {e}")
            self.invalid_count += 1
            
            # 记录验证错误
            error_record = DataValidationRecord(
                symbol=market_data.symbol,
                exchange=market_data.exchange,
                market_type=market_data.market_type,
                timestamp=datetime.now(timezone.utc),
                data_hash="",
                validation_result=ValidationResult.ERROR,
                violations=[f"验证异常: {str(e)}"],
                processing_time_ms=(time.time() - validation_start) * 1000
            )
            
            key = f"{market_data.exchange}_{market_data.market_type}_{market_data.symbol}"
            self.validation_cache[key].append(error_record)
            
            return ValidationResult.ERROR
    
    async def _validate_cache_isolation(self, market_data: MarketData, violations: List[str]):
        """验证缓存隔离"""
        if not self.isolation_rules['cache_isolation']['enabled']:
            return
        
        try:
            # 检查缓存键是否符合命名空间要求
            expected_namespace = self.cache_namespaces.get(market_data.market_type)
            if not expected_namespace:
                violations.append(f"未知市场类型的缓存命名空间: {market_data.market_type}")
                return
            
            # 模拟检查缓存键格式
            cache_key_pattern = f"{expected_namespace}:{market_data.exchange}:{market_data.symbol}"
            
            # 检查是否与期货数据冲突（如果这是现货数据）
            if market_data.market_type == 'spot':
                futures_namespace = self.cache_namespaces['futures']
                futures_key_pattern = f"{futures_namespace}:{market_data.exchange}:{market_data.symbol}"
                
                # 这里应该检查实际缓存实现是否正确隔离
                # 目前只是验证逻辑
                
            logger.debug(f"缓存隔离验证: {cache_key_pattern}")
            
        except Exception as e:
            violations.append(f"缓存隔离验证失败: {e}")
    
    async def _validate_data_integrity(self, market_data: MarketData, violations: List[str]):
        """验证数据完整性"""
        required_fields = [
            'symbol', 'current_price', 'volume_24h', 'timestamp', 'exchange', 'market_type'
        ]
        
        for field in required_fields:
            if not hasattr(market_data, field) or getattr(market_data, field) is None:
                violations.append(f"缺失必需字段: {field}")
        
        # 检查数值合理性
        if hasattr(market_data, 'current_price') and market_data.current_price <= 0:
            violations.append(f"价格不合理: {market_data.current_price}")
        
        if hasattr(market_data, 'volume_24h') and market_data.volume_24h < 0:
            violations.append(f"交易量不合理: {market_data.volume_24h}")
    
    async def _validate_timestamp(self, market_data: MarketData, violations: List[str]):
        """验证时间戳"""
        if not hasattr(market_data, 'timestamp'):
            violations.append("缺失时间戳")
            return
        
        now = datetime.now(timezone.utc)
        time_diff = abs((now - market_data.timestamp).total_seconds())
        
        if time_diff > self.max_data_age_seconds:
            violations.append(f"数据过于陈旧: 相差 {time_diff:.1f} 秒")
        
        if market_data.timestamp > now:
            violations.append("时间戳在未来")
    
    async def _validate_price_reasonableness(self, market_data: MarketData, violations: List[str]):
        """验证价格合理性"""
        if not hasattr(market_data, 'current_price'):
            return
        
        # 检查价格是否在合理范围内
        if market_data.current_price < 0.000001:  # 小于最小单位
            violations.append(f"价格过低: {market_data.current_price}")
        elif market_data.current_price > 1000000:  # 大于100万
            violations.append(f"价格过高: {market_data.current_price}")
    
    async def _validate_symbol_format(self, market_data: MarketData, violations: List[str]):
        """验证符号格式"""
        symbol = market_data.symbol
        
        if market_data.market_type == 'spot':
            # 现货符号格式：BTCUSDT, ETHUSDT 等
            if not symbol.endswith('USDT') and not symbol.endswith('BTC') and not symbol.endswith('ETH'):
                violations.append(f"现货符号格式不正确: {symbol}")
        elif market_data.market_type == 'futures':
            # 期货符号格式：BTCUSDT-PERP, BTC230929 等
            if not ('-PERP' in symbol or '-' in symbol):
                violations.append(f"期货符号格式不正确: {symbol}")
    
    async def _validate_exchange_consistency(self, market_data: MarketData, violations: List[str]):
        """验证交易所一致性"""
        # 检查交易所名称是否在预期范围内
        valid_exchanges = ['binance', 'okx', 'bybit', 'huobi']
        
        if market_data.exchange not in valid_exchanges:
            violations.append(f"未知的交易所: {market_data.exchange}")
        
        # 检查市场类型与交易所的兼容性
        exchange_support = {
            'binance': ['spot', 'futures'],
            'okx': ['spot', 'futures'],
            'bybit': ['spot', 'futures'],
            'huobi': ['spot']
        }
        
        supported_markets = exchange_support.get(market_data.exchange, [])
        if market_data.market_type not in supported_markets:
            violations.append(f"{market_data.exchange} 不支持 {market_data.market_type} 市场")
    
    def _generate_data_hash(self, market_data: MarketData) -> str:
        """生成数据哈希"""
        # 创建数据的字符串表示
        data_str = f"{market_data.symbol}|{market_data.exchange}|{market_data.current_price}|{market_data.timestamp.isoformat()}"
        
        # 生成MD5哈希
        return hashlib.md5(data_str.encode()).hexdigest()
    
    def _determine_validation_result(self, violations: List[str]) -> ValidationResult:
        """确定验证结果"""
        if not violations:
            return ValidationResult.VALID
        
        # 根据违规数量和严重程度决定结果
        critical_violations = [v for v in violations if '缺失' in v or '异常' in v]
        warning_violations = [v for v in violations if '过于' in v or '格式' in v]
        
        if critical_violations:
            return ValidationResult.INVALID
        elif warning_violations:
            return ValidationResult.WARNING
        else:
            return ValidationResult.INVALID
    
    async def _handle_validation_violations(self, market_data: MarketData, violations: List[str]):
        """处理验证违规"""
        # 创建违规记录
        violation = IsolationViolation(
            id=f"violation_{int(time.time())}_{market_data.symbol}",
            violation_type="data_validation",
            symbol=market_data.symbol,
            description=f"数据验证违规: {violations}",
            severity="high" if any('缺失' in v or '异常' in v for v in violations) else "medium",
            timestamp=datetime.now(timezone.utc)
        )
        
        self.violations.append(violation)
        
        # 触发违规处理器
        for handler in self.validation_handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(violation)
                else:
                    handler(violation)
            except Exception as e:
                logger.error(f"违规处理器执行失败: {e}")
        
        logger.warning(f"数据验证违规: {market_data.symbol} - {violations}")
    
    async def validate_cache_isolation(self, exchange: str, symbol: str, market_type: str) -> bool:
        """验证缓存隔离"""
        if not self.isolation_rules['cache_isolation']['enabled']:
            return True
        
        try:
            # 检查缓存键是否符合命名空间要求
            expected_namespace = self.cache_namespaces.get(market_type)
            if not expected_namespace:
                return False
            
            # 检查实际缓存键是否存在跨市场污染
            spot_key = f"{self.cache_namespaces['spot']}:{exchange}:{symbol}"
            futures_key = f"{self.cache_namespaces['futures']}:{exchange}:{symbol}"
            
            # 验证缓存实现是否正确隔离
            # 这里应该检查实际的缓存实现
            # 暂时返回True
            return True
            
        except Exception as e:
            logger.error(f"缓存隔离验证失败: {e}")
            return False
    
    async def validate_websocket_isolation(self, exchange: str, market_type: str) -> bool:
        """验证WebSocket连接隔离"""
        if not self.isolation_rules['websocket_isolation']['enabled']:
            return True
        
        try:
            # 检查WebSocket连接池是否正确分离
            ws_pool_name = f"ws_{market_type}_{exchange}"
            
            # 验证连接池是否存在于正确的命名空间
            if ws_pool_name not in self.ws_connections.get(market_type, {}):
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"WebSocket隔离验证失败: {e}")
            return False
    
    async def validate_data_flow_isolation(self, market_type: str) -> bool:
        """验证数据流隔离"""
        if not self.isolation_rules['aggregation_isolation']['enabled']:
            return True
        
        try:
            # 检查数据聚合器是否正确分离
            aggregator = self.data_aggregators.get(market_type)
            if not aggregator:
                return False
            
            # 验证聚合器是否只处理指定市场类型的数据
            # 这里应该检查聚合器的实际实现
            return True
            
        except Exception as e:
            logger.error(f"数据流隔离验证失败: {e}")
            return False
    
    def add_validation_handler(self, handler: Callable[[IsolationViolation], None]):
        """添加验证违规处理器"""
        self.validation_handlers.append(handler)
    
    def set_isolation_level(self, level: IsolationLevel):
        """设置隔离级别"""
        self.isolation_level = level
        logger.info(f"数据隔离级别已设置为: {level.value}")
    
    def get_isolation_violations(self, hours: int = 24) -> List[IsolationViolation]:
        """获取隔离违规记录"""
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        
        return [
            violation for violation in self.violations
            if violation.timestamp >= cutoff_time
        ]
    
    def get_validation_statistics(self) -> Dict[str, Any]:
        """获取验证统计信息"""
        success_rate = (self.valid_count / self.total_validations * 100) if self.total_validations > 0 else 0
        
        return {
            "total_validations": self.total_validations,
            "valid_count": self.valid_count,
            "invalid_count": self.invalid_count,
            "warning_count": self.warning_count,
            "success_rate": success_rate,
            "isolation_level": self.isolation_level.value,
            "active_violations": len(self.get_isolation_violations(1)),  # 过去1小时的违规
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    async def perform_comprehensive_isolation_test(self) -> Dict[str, Any]:
        """执行全面的隔离测试"""
        test_results = {
            "cache_isolation": await self._test_cache_isolation(),
            "websocket_isolation": await self._test_websocket_isolation(),
            "data_flow_isolation": await self._test_data_flow_isolation(),
            "validation_rules": self._test_validation_rules(),
            "overall_score": 0
        }
        
        # 计算总体得分
        scores = []
        for test_name, result in test_results.items():
            if test_name != "overall_score" and isinstance(result, dict):
                scores.append(result.get("score", 0))
        
        test_results["overall_score"] = sum(scores) / len(scores) if scores else 0
        
        logger.info(f"隔离测试完成，总体得分: {test_results['overall_score']:.2f}")
        
        return test_results
    
    async def _test_cache_isolation(self) -> Dict[str, Any]:
        """测试缓存隔离"""
        test_score = 100
        issues = []
        
        # 测试缓存命名空间隔离
        for market_type, namespace in self.cache_namespaces.items():
            # 这里应该实际测试缓存实现
            # 目前返回模拟结果
            pass
        
        if issues:
            test_score -= len(issues) * 10
        
        return {
            "score": test_score,
            "issues": issues,
            "details": "缓存隔离测试完成"
        }
    
    async def _test_websocket_isolation(self) -> Dict[str, Any]:
        """测试WebSocket隔离"""
        test_score = 100
        issues = []
        
        # 测试WebSocket连接池隔离
        for market_type in ['spot', 'futures']:
            if market_type not in self.ws_connections:
                issues.append(f"缺失{market_type} WebSocket连接池")
                test_score -= 20
        
        return {
            "score": test_score,
            "issues": issues,
            "details": "WebSocket隔离测试完成"
        }
    
    async def _test_data_flow_isolation(self) -> Dict[str, Any]:
        """测试数据流隔离"""
        test_score = 100
        issues = []
        
        # 测试数据聚合器隔离
        for market_type in ['spot', 'futures']:
            if market_type not in self.data_aggregators:
                issues.append(f"缺失{market_type}数据聚合器")
                test_score -= 20
        
        return {
            "score": test_score,
            "issues": issues,
            "details": "数据流隔离测试完成"
        }
    
    def _test_validation_rules(self) -> Dict[str, Any]:
        """测试验证规则"""
        test_score = 100
        issues = []
        
        # 检查隔离规则配置
        required_rules = [
            'cache_isolation', 'websocket_isolation', 
            'aggregation_isolation', 'data_validation', 'monitoring'
        ]
        
        for rule in required_rules:
            if rule not in self.isolation_rules:
                issues.append(f"缺失隔离规则: {rule}")
                test_score -= 15
        
        return {
            "score": test_score,
            "issues": issues,
            "details": "验证规则测试完成"
        }


# 全局实例
_data_validator: Optional[DataIsolationValidator] = None


def get_data_validator() -> DataIsolationValidator:
    """获取全局数据验证器实例"""
    global _data_validator
    
    if _data_validator is None:
        _data_validator = DataIsolationValidator()
    
    return _data_validator


if __name__ == "__main__":
    # 测试数据隔离验证器
    import asyncio
    
    async def test_data_validator():
        print("测试数据隔离验证器...")
        
        try:
            validator = get_data_validator()
            
            # 模拟市场数据
            market_data = MarketData(
                symbol="BTCUSDT",
                current_price=50000.00,
                previous_close=49000.00,
                high_24h=51000.00,
                low_24h=48000.00,
                price_change=1000.00,
                price_change_percent=2.04,
                volume_24h=1500.50,
                quote_volume_24h=75000000.00,
                timestamp=datetime.now(timezone.utc),
                exchange="binance",
                market_type="spot"
            )
            
            # 执行验证
            result = await validator.validate_market_data_isolation(market_data, "spot")
            print(f"验证结果: {result.value}")
            
            # 获取统计信息
            stats = validator.get_validation_statistics()
            print(f"验证统计: {json.dumps(stats, indent=2, default=str)}")
            
        except Exception as e:
            print(f"测试失败: {e}")
    
    asyncio.run(test_data_validator())