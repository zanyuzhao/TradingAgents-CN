"""
策略状态机持久化管理器
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import json
import logging

try:
    from pymongo import MongoClient
    from pymongo.errors import DuplicateKeyError
    MONGODB_AVAILABLE = True
except ImportError:
    MONGODB_AVAILABLE = False

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

from core.data_structures import StrategyInstance

class StrategyStateMachinePersistence:
    """策略状态机持久化管理器"""

    def __init__(self, mongo_uri: str = "mongodb://localhost:27017",
                 redis_uri: str = "redis://localhost:6379"):
        """
        初始化持久化管理器

        Args:
            mongo_uri: MongoDB连接字符串
            redis_uri: Redis连接字符串
        """
        self.logger = logging.getLogger("Persistence")

        # MongoDB连接
        if MONGODB_AVAILABLE:
            try:
                self.mongo_client = MongoClient(mongo_uri)
                self.db = self.mongo_client.trading_agents
                self.strategy_states = self.db.strategy_states
                self.daily_snapshots = self.db.daily_snapshots
                self.trade_executions = self.db.trade_executions
                self.performance_metrics = self.db.performance_metrics
                self.logger.info("MongoDB连接成功")
            except Exception as e:
                self.logger.error(f"MongoDB连接失败: {e}")
                self.mongo_client = None
        else:
            self.logger.warning("MongoDB不可用，使用内存存储")
            self.mongo_client = None
            self._init_memory_storage()

        # Redis连接
        if REDIS_AVAILABLE:
            try:
                self.redis_client = redis.from_url(redis_uri)
                self.redis_client.ping()
                self.logger.info("Redis连接成功")
            except Exception as e:
                self.logger.error(f"Redis连接失败: {e}")
                self.redis_client = None
        else:
            self.logger.warning("Redis不可用，禁用缓存")
            self.redis_client = None

        # 缓存TTL
        self.cache_ttl = 3600  # 1小时缓存

        # 创建索引
        if self.mongo_client:
            self._create_indexes()

    def _init_memory_storage(self):
        """初始化内存存储（当MongoDB不可用时）"""
        self.strategy_states = MemoryStorage()
        self.daily_snapshots = MemoryStorage()
        self.trade_executions = MemoryStorage()
        self.performance_metrics = MemoryStorage()

    def _create_indexes(self):
        """创建数据库索引"""
        try:
            # 策略状态索引
            self.strategy_states.create_index([("strategy_id", 1)], unique=True)
            self.strategy_states.create_index([("stock_code", 1)])
            self.strategy_states.create_index([("state", 1)])
            self.strategy_states.create_index([("last_update", 1)])
            self.strategy_states.create_index([("regime", 1)])

            # 日快照索引
            self.daily_snapshots.create_index([("date", 1), ("strategy_id", 1)], unique=True)
            self.daily_snapshots.create_index([("date", 1)])

            # 交易执行索引
            self.trade_executions.create_index([("strategy_id", 1), ("execution_time", 1)])
            self.trade_executions.create_index([("execution_time", 1)])

            # 性能指标索引
            self.performance_metrics.create_index([("strategy_id", 1), ("date", 1)], unique=True)
            self.performance_metrics.create_index([("date", 1)])

            self.logger.info("数据库索引创建成功")

        except Exception as e:
            self.logger.error(f"索引创建失败: {e}")

    def save_strategy_state(self, strategy: StrategyInstance) -> bool:
        """保存策略状态"""
        try:
            strategy_dict = strategy.to_dict()

            if self.mongo_client:
                # 使用MongoDB
                result = self.strategy_states.replace_one(
                    {"strategy_id": strategy.strategy_id},
                    strategy_dict,
                    upsert=True
                )

                # 更新Redis缓存
                if self.redis_client:
                    cache_key = f"strategy_state:{strategy.strategy_id}"
                    self.redis_client.setex(
                        cache_key,
                        self.cache_ttl,
                        json.dumps(strategy_dict, default=str)
                    )

                # 记录变更日志
                self._log_state_change(strategy)

                return result.acknowledged
            else:
                # 使用内存存储
                self.strategy_states.set(strategy.strategy_id, strategy_dict)
                return True

        except Exception as e:
            self.logger.error(f"保存策略状态失败: {e}")
            return False

    def load_strategy_state(self, strategy_id: str) -> Optional[StrategyInstance]:
        """加载策略状态"""
        try:
            # 先从Redis缓存读取
            if self.redis_client:
                cache_key = f"strategy_state:{strategy_id}"
                cached_data = self.redis_client.get(cache_key)

                if cached_data:
                    strategy_dict = json.loads(cached_data)
                    return StrategyInstance.from_dict(strategy_dict)

            # 缓存未命中，从数据库读取
            if self.mongo_client:
                strategy_dict = self.strategy_states.find_one({"strategy_id": strategy_id})

                if strategy_dict:
                    # 更新缓存
                    if self.redis_client:
                        cache_key = f"strategy_state:{strategy_id}"
                        self.redis_client.setex(
                            cache_key,
                            self.cache_ttl,
                            json.dumps(strategy_dict, default=str)
                        )

                    return StrategyInstance.from_dict(strategy_dict)
            else:
                # 使用内存存储
                strategy_dict = self.strategy_states.get(strategy_id)
                if strategy_dict:
                    return StrategyInstance.from_dict(strategy_dict)

            return None

        except Exception as e:
            self.logger.error(f"加载策略状态失败: {e}")
            return None

    def get_active_strategies(self) -> List[StrategyInstance]:
        """获取所有活跃策略"""
        try:
            active_states = [
                "open",
                "pyramiding",
                "holding",
                "ready_to_enter"
            ]

            if self.mongo_client:
                cursor = self.strategy_states.find({
                    "state": {"$in": active_states}
                })
            else:
                cursor = self.strategy_states.find_by_condition(
                    lambda item: item.get("state") in active_states
                )

            strategies = []
            for doc in cursor:
                try:
                    strategy = StrategyInstance.from_dict(doc)
                    strategies.append(strategy)
                except Exception as e:
                    self.logger.error(f"解析策略状态失败: {e}")
                    continue

            return strategies

        except Exception as e:
            self.logger.error(f"获取活跃策略失败: {e}")
            return []

    def get_strategies_by_stock(self, stock_code: str) -> List[StrategyInstance]:
        """获取指定股票的所有策略"""
        try:
            if self.mongo_client:
                cursor = self.strategy_states.find({"stock_code": stock_code})
            else:
                cursor = self.strategy_states.find_by_condition(
                    lambda item: item.get("stock_code") == stock_code
                )

            strategies = []
            for doc in cursor:
                try:
                    strategy = StrategyInstance.from_dict(doc)
                    strategies.append(strategy)
                except Exception as e:
                    self.logger.error(f"解析策略状态失败: {e}")
                    continue

            return strategies

        except Exception as e:
            self.logger.error(f"获取股票策略失败: {e}")
            return []

    def save_daily_snapshot(self, strategy_id: str, date: datetime,
                           snapshot_data: Dict[str, Any]) -> bool:
        """保存每日快照"""
        try:
            snapshot_doc = {
                "strategy_id": strategy_id,
                "date": date,
                "snapshot_data": snapshot_data,
                "created_at": datetime.now()
            }

            if self.mongo_client:
                result = self.daily_snapshots.replace_one(
                    {"strategy_id": strategy_id, "date": date},
                    snapshot_doc,
                    upsert=True
                )
                return result.acknowledged
            else:
                key = f"{strategy_id}_{date.strftime('%Y-%m-%d')}"
                self.daily_snapshots.set(key, snapshot_doc)
                return True

        except Exception as e:
            self.logger.error(f"保存每日快照失败: {e}")
            return False

    def record_trade_execution(self,
                              strategy_id: str,
                              action: str,
                              quantity: int,
                              price: float,
                              execution_time: datetime,
                              execution_details: Dict[str, Any] = None) -> bool:
        """记录交易执行"""
        try:
            trade_doc = {
                "strategy_id": strategy_id,
                "action": action,  # "enter", "exit", "add_position", "reduce_position"
                "quantity": quantity,
                "price": price,
                "total_value": quantity * price,
                "execution_time": execution_time,
                "execution_details": execution_details or {},
                "created_at": datetime.now()
            }

            if self.mongo_client:
                result = self.trade_executions.insert_one(trade_doc)
                return result.acknowledged
            else:
                trade_id = f"{strategy_id}_{execution_time.isoformat()}"
                self.trade_executions.set(trade_id, trade_doc)
                return True

        except Exception as e:
            self.logger.error(f"记录交易执行失败: {e}")
            return False

    def update_performance_metrics(self,
                                  strategy_id: str,
                                  date: datetime,
                                  metrics: Dict[str, Any]) -> bool:
        """更新性能指标"""
        try:
            metrics_doc = {
                "strategy_id": strategy_id,
                "date": date,
                "metrics": metrics,
                "updated_at": datetime.now()
            }

            if self.mongo_client:
                result = self.performance_metrics.replace_one(
                    {"strategy_id": strategy_id, "date": date},
                    metrics_doc,
                    upsert=True
                )
                return result.acknowledged
            else:
                key = f"{strategy_id}_{date.strftime('%Y-%m-%d')}"
                self.performance_metrics.set(key, metrics_doc)
                return True

        except Exception as e:
            self.logger.error(f"更新性能指标失败: {e}")
            return False

    def _log_state_change(self, strategy: StrategyInstance):
        """记录状态变更日志"""
        try:
            log_doc = {
                "strategy_id": strategy.strategy_id,
                "new_state": strategy.state.value,
                "stock_code": strategy.stock_code,
                "timestamp": datetime.now(),
                "reason": strategy.history[-1] if strategy.history else None
            }

            # 这里可以记录到专门的日志集合
            # self.state_change_logs.insert_one(log_doc)

        except Exception as e:
            self.logger.error(f"记录状态变更失败: {e}")

    def get_strategy_history(self, strategy_id: str, days: int = 30) -> List[Dict[str, Any]]:
        """获取策略历史记录"""
        try:
            start_date = datetime.now() - timedelta(days=days)

            if self.mongo_client:
                # 获取交易历史
                trades = list(self.trade_executions.find({
                    "strategy_id": strategy_id,
                    "execution_time": {"$gte": start_date}
                }).sort("execution_time", -1))

                # 获取性能历史
                metrics = list(self.performance_metrics.find({
                    "strategy_id": strategy_id,
                    "date": {"$gte": start_date}
                }).sort("date", -1))

                return {
                    "trades": trades,
                    "metrics": metrics
                }
            else:
                # 简化的内存实现
                return {"trades": [], "metrics": []}

        except Exception as e:
            self.logger.error(f"获取策略历史失败: {e}")
            return {"trades": [], "metrics": []}

    def cleanup_old_data(self, days_to_keep: int = 365):
        """清理旧数据"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days_to_keep)

            if self.mongo_client:
                # 清理旧的交易记录
                result1 = self.trade_executions.delete_many({
                    "execution_time": {"$lt": cutoff_date}
                })

                # 清理旧的性能指标
                result2 = self.performance_metrics.delete_many({
                    "date": {"$lt": cutoff_date}
                })

                # 清理旧的快照
                result3 = self.daily_snapshots.delete_many({
                    "date": {"$lt": cutoff_date}
                })

                self.logger.info(f"清理旧数据完成: trades={result1.deleted_count}, "
                               f"metrics={result2.deleted_count}, snapshots={result3.deleted_count}")

        except Exception as e:
            self.logger.error(f"清理旧数据失败: {e}")

    def get_database_stats(self) -> Dict[str, Any]:
        """获取数据库统计信息"""
        try:
            if not self.mongo_client:
                return {"error": "MongoDB不可用"}

            stats = {
                "strategy_states": self.strategy_states.count_documents({}),
                "trade_executions": self.trade_executions.count_documents({}),
                "performance_metrics": self.performance_metrics.count_documents({}),
                "daily_snapshots": self.daily_snapshots.count_documents({}),
                "storage_size": 0
            }

            # 获取存储大小
            db_stats = self.db.command("dbstats")
            stats["storage_size"] = db_stats.get("storageSize", 0)

            return stats

        except Exception as e:
            self.logger.error(f"获取数据库统计失败: {e}")
            return {"error": str(e)}

    def close(self):
        """关闭连接"""
        try:
            if self.mongo_client:
                self.mongo_client.close()
            if self.redis_client:
                self.redis_client.close()
            self.logger.info("数据库连接已关闭")
        except Exception as e:
            self.logger.error(f"关闭数据库连接失败: {e}")

class MemoryStorage:
    """内存存储实现（用于测试或无数据库环境）"""

    def __init__(self):
        self._data = {}

    def set(self, key: str, value: Any):
        """设置值"""
        self._data[key] = value

    def get(self, key: str) -> Optional[Any]:
        """获取值"""
        return self._data.get(key)

    def find_one(self, query: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """查找单个文档"""
        for item in self._data.values():
            if self._match_query(item, query):
                return item
        return None

    def find(self, query: Dict[str, Any] = None):
        """查找多个文档"""
        if query is None:
            return iter(self._data.values())
        return iter(item for item in self._data.values() if self._match_query(item, query))

    def find_by_condition(self, condition_func):
        """根据条件函数查找"""
        return iter(item for item in self._data.values() if condition_func(item))

    def replace_one(self, query: Dict[str, Any], replacement: Dict[str, Any], upsert: bool = False):
        """替换单个文档"""
        for key, item in self._data.items():
            if self._match_query(item, query):
                self._data[key] = replacement
                return MockResult(acknowledged=True)

        if upsert:
            # 生成新的key
            new_key = replacement.get("strategy_id", f"doc_{len(self._data)}")
            self._data[new_key] = replacement
            return MockResult(acknowledged=True)

        return MockResult(acknowledged=False)

    def insert_one(self, document: Dict[str, Any]):
        """插入单个文档"""
        new_key = f"doc_{len(self._data)}"
        self._data[new_key] = document
        return MockResult(acknowledged=True, inserted_id=new_key)

    def delete_many(self, query: Dict[str, Any]):
        """删除多个文档"""
        keys_to_delete = []
        for key, item in self._data.items():
            if self._match_query(item, query):
                keys_to_delete.append(key)

        for key in keys_to_delete:
            del self._data[key]

        return MockResult(deleted_count=len(keys_to_delete))

    def count_documents(self, query: Dict[str, Any] = None) -> int:
        """统计文档数量"""
        if query is None:
            return len(self._data)
        return sum(1 for item in self._data.values() if self._match_query(item, query))

    def create_index(self, keys: List[tuple], **kwargs):
        """创建索引（内存存储中不实际创建）"""
        pass

    def _match_query(self, item: Dict[str, Any], query: Dict[str, Any]) -> bool:
        """匹配查询条件"""
        for key, condition in query.items():
            if key not in item:
                return False

            if isinstance(condition, dict):
                # 处理操作符，如 {"$in": [...]}
                for op, value in condition.items():
                    if op == "$in" and item[key] not in value:
                        return False
                    elif op == "$gte" and item[key] < value:
                        return False
                    elif op == "$lt" and item[key] >= value:
                        return False
            elif item[key] != condition:
                return False

        return True

class MockResult:
    """模拟MongoDB操作结果"""

    def __init__(self, acknowledged=False, inserted_id=None, deleted_count=0):
        self.acknowledged = acknowledged
        self.inserted_id = inserted_id
        self.deleted_count = deleted_count