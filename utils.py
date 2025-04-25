import logging
from datetime import datetime
from typing import Optional

# 修改初始化组件定义
_INITIALIZED_COMPONENTS = {
    'bot': False,
    'database': False,
    'handlers': False,
    'commands': False
}

def reset_initialization(component: Optional[str] = None) -> None:
    """重置初始化标记
    
    Args:
        component: 要重置的特定组件，如果为None则重置所有组件
    """
    global _INITIALIZED_COMPONENTS
    if component:
        if component in _INITIALIZED_COMPONENTS:
            _INITIALIZED_COMPONENTS[component] = False
            logger.debug(f"已重置组件 {component} 的初始化状态")
    else:
        _INITIALIZED_COMPONENTS = {k: False for k in _INITIALIZED_COMPONENTS}
        logger.info("已重置所有组件的初始化状态")

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
# 创建一个控制台处理器，将日志输出到控制台
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)
# 定义日志格式
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)
# 将处理器添加到日志记录器
logger.addHandler(console_handler)

def mark_initialized(component: str, force: bool = False) -> bool:
    """标记组件为已初始化状态
    
    Args:
        component: 要标记的组件名称
        force: 是否强制标记（即使已经初始化）
    """
    global _INITIALIZED_COMPONENTS
    if component not in _INITIALIZED_COMPONENTS:
        logger.warning(f"未知的组件: {component}")
        return False
    
    was_initialized = _INITIALIZED_COMPONENTS[component]
    if not was_initialized or force:
        _INITIALIZED_COMPONENTS[component] = True
        logger.debug(f"组件 {component} 已标记为初始化")
    return was_initialized


def parse_time(time_str: str) -> str:
    """解析开奖时间字符串"""
    try:
        # 尝试解析 ISO 格式 (2025-04-21T16:01)
        if 'T' in time_str:
            time = datetime.strptime(time_str, '%Y-%m-%dT%H:%M')
        # 尝试解析标准格式 (2025-04-21 16:01)
        else:
            time = datetime.strptime(time_str, '%Y-%m-%d %H:%M')
        return time.strftime('%Y-%m-%d %H:%M')
    except ValueError:
        logger.error(f"无效的时间格式: {time_str}")
        return "时间格式错误"


async def parse_group_input(query: str) -> tuple[Optional[int], Optional[str]]:
    """解析输入的群组/频道信息"""
    try:
        # 1. 处理数字ID
        if query.startswith('-100'):
            return int(query), None
            
        # 2. 处理用户名
        elif query.startswith('@'):
            return None, query
           
        # 3. 处理链接
        elif 't.me/' in query:
            # 移除协议部分
            query = query.replace('https://', '').replace('http://', '')
            # 获取路径部分
            path = query.split('t.me/')[-1]
            # 如果是私有链接（包含 joinchat）
            if 'joinchat' in path:
                invite_link = f'@path.split("joinchat/")[-1]'
                return None, invite_link
            # 如果是公开链接
            else:
                username = f'@{path.strip("/")}'
                return None, username
        # 4. 处理userID
        elif query.isdigit():
            return int(query), None
        # 5. 处理其他情况
        else:
            return None, f'@{query}' 
    except Exception as e:
        logger.error(f"解析群组输入时出错: {e}")
        return None, None

