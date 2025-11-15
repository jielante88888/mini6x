"""
数据源优先级管理器
负责管理币安和OKX交易所的数据源优先级选择和切换逻辑
"""

import json
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Set, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
from collections import defaultdict, deque
import random
import statistics

import structlog

from ..adapters.base import MarketData
from ..core.market_analyzer import HealthStatus, PerformanceMetrics

logger = structlog.get_logger(__name__)


class LoadBalancingMode(Enum):
    """负载均衡模式"""
    PRIORITY_ONLY = "priority_only"
    WEIGHTED_ROUND_ROBIN = "weighted_round_robin"
    PERFORMANCE_BASED = "performance_based"
    LEARNING_BASED = "learning_based"


@dataclass
class ExchangePriorityConfig:
    """交易所优先级配置"""
    exchange: str
    market_type: str
    priority: int  # 1=最高优先级
    weight: float  # 负载均衡权重
    enabled: bool = True
    performance_score: float = 1.0
    data_quality_score: float = 1.0
    last_updated: Optional[datetime] = None


@dataclass
class DataQualityMetrics:
    """数据质量指标"""
    completeness: float = 1.0  # 数据完整性
    accuracy: float = 1.0      # 数据准确性
    timeliness: float = 1.0    # 数据时效性
    consistency: float = 1.0   # 数据一致性
    overall_score: float = 1.0


class ExchangePriorityManager:
    """交易所优先级管理器"""
    
    def __init__(self):
        self.market_priorities: Dict[str, Dict[str, ExchangePriorityConfig]] = defaultdict(dict)
        self.exchange_performance: Dict[str, Dict[str, PerformanceMetrics]] = defaultdict(dict)
        self.data_quality_scores: Dict[str, Dict[str, DataQualityMetrics]] = defaultdict(lambda: defaultdict(lambda: DataQualityMetrics()))
        self.pair_specific_priorities: Dict[str, Dict[str, Dict[str, ExchangePriorityConfig]]] = defaultdict(lambda: defaultdict(lambda: defaultdict(ExchangePriorityConfig)))
        self.time_based_priorities: Dict[str, Dict[str, Dict[int, List[str]]]] = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
        self.load_balancing_mode = LoadBalancingMode.PRIORITY_ONLY
        self.usage_statistics: Dict[str, Dict[str, Dict[str, int]]] = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))
        self.learning_data: Dict[str, Dict[str, List[Dict]]] = defaultdict(lambda: defaultdict(lambda: deque(maxlen=1000)))
        
        # 默认配置
        self._setup_default_priorities()
        
        logger.info("交易所优先级管理器初始化完成")
    
    def _setup_default_priorities(self):
        """设置默认优先级配置"""
        # 现货市场：币安优先
        self.set_market_priority('spot', {
            'binance': {'priority': 1, 'weight': 0.8},
            'okx': {'priority': 2, 'weight': 0.2}
        })
        
        # 期货市场：币安优先
        self.set_market_priority('futures', {
            'binance': {'priority': 1, 'weight': 0.7},
            'okx': {'priority': 2, 'weight': 0.3}
        })
        
        # 主流交易对优先级
        major_pairs = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'ADAUSDT', 'SOLUSDT']
        self.set_pairs_priority('spot', major_pairs, {
            'binance': {'priority': 1, 'weight': 0.9},
            'okx': {'priority': 2, 'weight': 0.1}
        })
        
        logger.info("默认优先级配置已设置")
    
    def set_market_priority(self, market_type: str, priorities: Dict[str, Dict[str, float]]):
        """设置市场类型优先级"""
        for exchange, config in priorities.items():
            self.market_priorities[market_type][exchange] = ExchangePriorityConfig(
                exchange=exchange,
                market_type=market_type,
                priority=int(config.get('priority', 2)),
                weight=float(config.get('weight', 0.5)),
                enabled=config.get('enabled', True),
                last_updated=datetime.now(timezone.utc)
            )
        
        logger.info(f"已设置 {market_type} 市场优先级: {priorities}")
    
    def set_pairs_priority(self, market_type: str, pairs: List[str], priorities: Dict[str, Dict[str, float]]):
        """设置特定交易对优先级"""
        for pair in pairs:
            pair_config = {}
            for exchange, config in priorities.items():
                pair_config[exchange] = ExchangePriorityConfig(
                    exchange=exchange,
                    market_type=market_type,
                    priority=int(config.get('priority', 2)),
                    weight=float(config.get('weight', 0.5)),
                    enabled=config.get('enabled', True),
                    last_updated=datetime.now(timezone.utc)
                )
            self.pair_specific_priorities[market_type][pair] = pair_config
        
        logger.info(f"已设置 {market_type} 市场 {len(pairs)} 个交易对的优先级")
    
    def set_exchange_priority(self, exchange: str, market_type: str, priority: int, weight: float = 0.5):
        """设置单个交易所优先级"""
        if market_type not in self.market_priorities:
            self.market_priorities[market_type] = {}
        
        self.market_priorities[market_type][exchange] = ExchangePriorityConfig(
            exchange=exchange,
            market_type=market_type,
            priority=priority,
            weight=weight,
            last_updated=datetime.now(timezone.utc)
        )
        
        logger.info(f"已设置 {exchange}/{market_type} 优先级: {priority}")
    
    def set_load_balancing_mode(self, mode: LoadBalancingMode):
        """设置负载均衡模式"""
        self.load_balancing_mode = mode
        logger.info(f"负载均衡模式已设置为: {mode.value}")
    
    def update_exchange_performance(self, exchange: str, market_type: str, performance_metrics: Dict[str, float]):
        """更新交易所性能数据"""
        # 转换性能指标格式
        metrics = PerformanceMetrics(
            exchange=exchange,
            market_type=market_type,
            timestamp=datetime.now(timezone.utc),
            response_time_ms=performance_metrics.get('latency_ms', 0),
            success_rate=performance_metrics.get('success_rate', 1.0),
            error_count=performance_metrics.get('error_count', 0),
            total_requests=performance_metrics.get('total_requests', 1),
            data_freshness=performance_metrics.get('data_freshness', 1.0),
            uptime_percentage=performance_metrics.get('uptime', 100.0),
            latency_trend=performance_metrics.get('trend', 'stable')
        )
        
        self.exchange_performance[market_type][exchange] = metrics
        
        # 重新计算性能得分
        if market_type in self.market_priorities and exchange in self.market_priorities[market_type]:
            config = self.market_priorities[market_type][exchange]
            config.performance_score = self._calculate_performance_score(metrics)
            config.last_updated = datetime.now(timezone.utc)
        
        logger.debug(f"已更新 {exchange}/{market_type} 性能数据: {metrics.response_time_ms:.2f}ms")
    
    def set_data_quality_score(self, exchange: str, market_type: str, quality_metrics: Dict[str, float]):
        """设置数据质量评分"""
        quality = DataQualityMetrics(
            completeness=quality_metrics.get('completeness', 1.0),
            accuracy=quality_metrics.get('accuracy', 1.0),
            timeliness=quality_metrics.get('timeliness', 1.0),
            consistency=quality_metrics.get('consistency', 1.0)
        )
        
        quality.overall_score = (
            quality.completeness * 0.3 +
            quality.accuracy * 0.4 +
            quality.timeliness * 0.2 +
            quality.consistency * 0.1
        )
        
        self.data_quality_scores[market_type][exchange] = quality
        
        # 更新配置中的数据质量得分
        if market_type in self.market_priorities and exchange in self.market_priorities[market_type]:
            config = self.market_priorities[market_type][exchange]
            config.data_quality_score = quality.overall_score
            config.last_updated = datetime.now(timezone.utc)
        
        logger.debug(f"已设置 {exchange}/{market_type} 数据质量得分: {quality.overall_score:.2f}")
    
    def recalculate_priorities(self, market_type: str):
        """重新计算市场优先级"""
        if market_type not in self.market_priorities:
            return
        
        # 基于性能重新排序
        sorted_exchanges = sorted(
            self.market_priorities[market_type].items(),
            key=lambda x: (
                x[1].priority,
                -x[1].performance_score,
                -x[1].data_quality_score
            ),
            reverse=False
        )
        
        # 重新分配优先级
        for rank, (exchange, config) in enumerate(sorted_exchanges, 1):
            config.priority = rank
            config.last_updated = datetime.now(timezone.utc)
        
        logger.info(f"已重新计算 {market_type} 市场优先级")
    
    def get_optimal_exchange(self, market_type: str, symbol: str = None) -> Optional[str]:
        """获取最优交易所"""
        # 首先检查是否有特定交易对的优先级配置
        if symbol and market_type in self.pair_specific_priorities and symbol in self.pair_specific_priorities[market_type]:
            pair_configs = self.pair_specific_priorities[market_type][symbol]
            return self._select_exchange_with_mode(market_type, pair_configs)
        
        # 使用市场级配置
        if market_type in self.market_priorities:
            return self._select_exchange_with_mode(market_type, self.market_priorities[market_type])
        
        return None
    
    def _select_exchange_with_mode(self, market_type: str, configs: Dict[str, ExchangePriorityConfig]) -> Optional[str]:
        """根据负载均衡模式选择交易所"""
        # 过滤可用的交易所
        available_exchanges = {
            exchange: config for exchange, config in configs.items()
            if config.enabled
        }
        
        if not available_exchanges:
            return None
        
        # 记录使用统计
        selected_exchange = None
        
        if self.load_balancing_mode == LoadBalancingMode.PRIORITY_ONLY:
            # 只根据优先级选择
            selected_exchange = min(
                available_exchanges.items(),
                key=lambda x: x[1].priority
            )[0]
        
        elif self.load_balancing_mode == LoadBalancingMode.WEIGHTED_ROUND_ROBIN:
            # 加权轮询
            weights = [config.weight for config in available_exchanges.values()]
            exchanges = list(available_exchanges.keys())
            selected_exchange = self._weighted_random_selection(exchanges, weights)
        
        elif self.load_balancing_mode == LoadBalancingMode.PERFORMANCE_BASED:
            # 基于性能选择
            selected_exchange = self._performance_based_selection(available_exchanges)
        
        elif self.load_balancing_mode == LoadBalancingMode.LEARNING_BASED:
            # 基于学习的选择
            selected_exchange = self._learning_based_selection(market_type, available_exchanges)
        
        # 更新使用统计
        if selected_exchange:
            self._update_usage_statistics(market_type, selected_exchange)
        
        return selected_exchange
    
    def _weighted_random_selection(self, exchanges: List[str], weights: List[float]) -> str:
        """加权随机选择"""
        total_weight = sum(weights)
        if total_weight == 0:
            return random.choice(exchanges)
        
        normalized_weights = [w / total_weight for w in weights]
        return random.choices(exchanges, weights=normalized_weights)[0]
    
    def _performance_based_selection(self, configs: Dict[str, ExchangePriorityConfig]) -> str:
        """基于性能的选择"""
        # 综合得分 = 性能得分 * 数据质量得分 * 优先级权重
        scored_exchanges = []
        
        for exchange, config in configs.items():
            if exchange in self.exchange_performance.get(config.market_type, {}):
                metrics = self.exchange_performance[config.market_type][exchange]
                performance_score = config.performance_score
                quality_score = config.data_quality_score
                priority_score = 1.0 / config.priority  # 优先级越高，得分越高
                
                total_score = (
                    performance_score * 0.4 +
                    quality_score * 0.3 +
                    priority_score * 0.3
                )
                
                scored_exchanges.append((exchange, total_score))
            else:
                scored_exchanges.append((exchange, 0.1))  # 默认低分
        
        # 选择得分最高的交易所
        return max(scored_exchanges, key=lambda x: x[1])[0]
    
    def _learning_based_selection(self, market_type: str, configs: Dict[str, ExchangePriorityConfig]) -> str:
        """基于机器学习的选择"""
        # 简单的基于历史学习的选择算法
        best_exchange = None
        best_score = -1
        
        for exchange, config in configs.items():
            learning_data = self.learning_data[market_type].get(exchange, [])
            
            if learning_data:
                # 基于历史成功率、延迟、错误率计算得分
                success_rate = sum(1 for record in learning_data if record.get('success', False)) / len(learning_data)
                avg_latency = statistics.mean(record.get('latency', 0) for record in learning_data)
                error_rate = sum(record.get('errors', 0) for record in learning_data) / len(learning_data)
                
                # 简化的学习得分计算
                performance_score = config.performance_score
                success_bonus = success_rate * 0.3
                latency_penalty = min(avg_latency / 1000, 0.2)  # 延迟惩罚
                error_penalty = error_rate * 0.1
                
                total_score = performance_score + success_bonus - latency_penalty - error_penalty
            else:
                total_score = config.performance_score * 0.5  # 新交易所的基础分数
            
            if total_score > best_score:
                best_score = total_score
                best_exchange = exchange
        
        return best_exchange or min(configs.keys(), key=lambda x: configs[x].priority)
    
    def _calculate_performance_score(self, metrics: PerformanceMetrics) -> float:
        """计算性能得分"""
        # 响应时间得分
        if metrics.response_time_ms < 100:
            response_score = 1.0
        elif metrics.response_time_ms < 500:
            response_score = 0.8
        elif metrics.response_time_ms < 1000:
            response_score = 0.6
        else:
            response_score = 0.4
        
        # 成功率得分
        success_score = metrics.success_rate
        
        # 数据新鲜度得分
        freshness_score = metrics.data_freshness
        
        # 可用性得分
        uptime_score = metrics.uptime_percentage / 100.0
        
        # 综合得分
        return (
            response_score * 0.3 +
            success_score * 0.3 +
            freshness_score * 0.2 +
            uptime_score * 0.2
        )
    
    def mark_exchange_unavailable(self, exchange: str):
        """标记交易所为不可用"""
        for market_type, configs in self.market_priorities.items():
            if exchange in configs:
                configs[exchange].enabled = False
                configs[exchange].last_updated = datetime.now(timezone.utc)
        
        logger.warning(f"交易所 {exchange} 已标记为不可用")
    
    def mark_exchange_available(self, exchange: str):
        """标记交易所为可用"""
        for market_type, configs in self.market_priorities.items():
            if exchange in configs:
                configs[exchange].enabled = True
                configs[exchange].last_updated = datetime.now(timezone.utc)
        
        logger.info(f"交易所 {exchange} 已标记为可用")
    
    def _update_usage_statistics(self, market_type: str, exchange: str):
        """更新使用统计"""
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d-%H")
        self.usage_statistics[market_type][exchange][timestamp] += 1
    
    def record_learning_data(self, market_type: str, exchange: str, success: bool, latency: float, errors: int = 0):
        """记录学习数据"""
        record = {
            'timestamp': datetime.now(timezone.utc),
            'success': success,
            'latency': latency,
            'errors': errors
        }
        
        self.learning_data[market_type][exchange].append(record)
    
    def get_optimal_exchange_with_quality(self, market_type: str, symbol: str = None) -> Optional[str]:
        """获取包含质量评分的最优交易所"""
        return self.get_optimal_exchange(market_type, symbol)
    
    def get_exchange_for_time(self, market_type: str, symbol: str, target_time: datetime) -> Optional[str]:
        """根据时间获取最优交易所"""
        # 时间优先级逻辑（可以扩展为根据时段调整优先级）
        hour = target_time.hour
        
        # 简单的时间优先级策略：高峰时段优先币安
        if hour in [8, 9, 13, 14, 20, 21]:  # 高峰时段
            return self.get_optimal_exchange(market_type, symbol) or 'binance'
        else:
            # 低峰时段可以使用负载均衡
            return self.get_optimal_exchange(market_type, symbol)
    
    def get_priority_statistics(self) -> Dict[str, Any]:
        """获取优先级统计信息"""
        stats = {
            'load_balancing_mode': self.load_balancing_mode.value,
            'market_priorities': {},
            'usage_statistics': {},
            'learning_data_summary': {}
        }
        
        # 市场优先级统计
        for market_type, configs in self.market_priorities.items():
            stats['market_priorities'][market_type] = {
                exchange: {
                    'priority': config.priority,
                    'weight': config.weight,
                    'enabled': config.enabled,
                    'performance_score': config.performance_score,
                    'data_quality_score': config.data_quality_score
                }
                for exchange, config in configs.items()
            }
        
        # 使用统计
        for market_type, exchanges in self.usage_statistics.items():
            stats['usage_statistics'][market_type] = {
                exchange: dict(timestamps)
                for exchange, timestamps in exchanges.items()
            }
        
        # 学习数据统计
        for market_type, exchanges in self.learning_data.items():
            stats['learning_data_summary'][market_type] = {
                exchange: len(data)
                for exchange, data in exchanges.items()
            }
        
        return stats
    
    def save_config(self, file_path: str):
        """保存配置到文件"""
        config_data = {
            'market_priorities': {
                market_type: {
                    exchange: asdict(config) for exchange, config in configs.items()
                }
                for market_type, configs in self.market_priorities.items()
            },
            'pair_specific_priorities': {
                market_type: {
                    pair: {
                        exchange: asdict(config) for exchange, config in pair_configs.items()
                    }
                    for pair, pair_configs in market_pairs.items()
                }
                for market_type, market_pairs in self.pair_specific_priorities.items()
            },
            'load_balancing_mode': self.load_balancing_mode.value,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(config_data, f, indent=2, default=str)
        
        logger.info(f"优先级配置已保存到: {file_path}")
    
    def load_config(self, file_path: str):
        """从文件加载配置"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            
            # 加载市场优先级
            for market_type, exchanges in config_data.get('market_priorities', {}).items():
                self.market_priorities[market_type] = {}
                for exchange, config_dict in exchanges.items():
                    config_dict['last_updated'] = datetime.now(timezone.utc)
                    self.market_priorities[market_type][exchange] = ExchangePriorityConfig(**config_dict)
            
            # 加载负载均衡模式
            mode_name = config_data.get('load_balancing_mode', 'priority_only')
            self.load_balancing_mode = LoadBalancingMode(mode_name)
            
            logger.info(f"优先级配置已从 {file_path} 加载")
            
        except Exception as e:
            logger.error(f"加载配置失败: {e}")


# 全局实例
_priority_manager: Optional[ExchangePriorityManager] = None


def get_priority_manager() -> ExchangePriorityManager:
    """获取全局优先级管理器实例"""
    global _priority_manager
    
    if _priority_manager is None:
        _priority_manager = ExchangePriorityManager()
    
    return _priority_manager


if __name__ == "__main__":
    # 测试优先级管理器
    import asyncio
    
    async def test_priority_manager():
        print("测试优先级管理器...")
        
        try:
            manager = get_priority_manager()
            
            # 测试优先级选择
            spot_exchange = manager.get_optimal_exchange('spot', 'BTCUSDT')
            futures_exchange = manager.get_optimal_exchange('futures', 'BTCUSDT-PERP')
            
            print(f"现货首选交易所: {spot_exchange}")
            print(f"期货首选交易所: {futures_exchange}")
            
            # 测试性能更新
            manager.update_exchange_performance('spot', 'binance', {
                'latency_ms': 150,
                'success_rate': 0.95,
                'error_count': 2,
                'total_requests': 100,
                'data_freshness': 0.9,
                'uptime': 99.5
            })
            
            # 重新计算优先级
            manager.recalculate_priorities('spot')
            
            # 获取统计信息
            stats = manager.get_priority_statistics()
            print(f"优先级统计: {json.dumps(stats, indent=2, default=str)}")
            
        except Exception as e:
            print(f"测试失败: {e}")
    
    asyncio.run(test_priority_manager())