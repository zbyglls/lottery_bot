from utils import logger

_application = None
_initialized = False

def get_bot():
    """获取bot实例"""
    global _application
    if not _application:
        logger.error("机器人实例未初始化")
        return None
    return _application.bot

def set_application(app):
    """设置应用实例"""
    global _application, _initialized
    _application = app
    _initialized = True