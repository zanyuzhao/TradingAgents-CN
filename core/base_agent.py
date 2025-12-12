"""
基础智能体类
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from datetime import datetime

class BaseAgent(ABC):
    """智能体基类"""

    def __init__(self, name: str = None):
        self.name = name or self.__class__.__name__
        self.logger = logging.getLogger(self.name)
        self.created_at = datetime.now()

    @abstractmethod
    def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """处理数据的抽象方法"""
        pass

    def validate_input(self, data: Dict[str, Any]) -> bool:
        """验证输入数据"""
        return isinstance(data, dict)

    def log_execution(self, method_name: str, input_data: Any, output_data: Any, execution_time: float):
        """记录执行日志"""
        self.logger.debug(f"{method_name} executed in {execution_time:.3f}s")

    def get_info(self) -> Dict[str, Any]:
        """获取智能体信息"""
        return {
            "name": self.name,
            "type": self.__class__.__name__,
            "created_at": self.created_at.isoformat(),
            "description": self.__doc__
        }