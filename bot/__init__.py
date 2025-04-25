from telegram.ext import Application, CallbackQueryHandler
from bot.tasks import check_lottery_draws, ping_service
from config import TELEGRAM_BOT_TOKEN
from utils import logger, reset_initialization
from bot.bot_instance import set_application, get_bot
from bot.commands import register_commands
from bot.callbacks import handle_callback_query
import asyncio

async def create_bot():
    """创建并初始化bot"""
    try:
        # 重置初始化状态
        reset_initialization()
        
        # 创建新的Application实例
        application = (
            Application.builder()
            .token(TELEGRAM_BOT_TOKEN)
            .build()
        )

        # 设置全局实例并立即标记为已初始化
        set_application(application)
        
        # 初始化机器人
        await application.initialize()
        
        # 注册所有处理器
        register_commands(application)
        application.add_handler(CallbackQueryHandler(handle_callback_query))
        logger.info("所有处理器注册完成")
        
        # 启动机器人和轮询
        await application.start()
        await application.updater.start_polling(drop_pending_updates=True)
        logger.info("机器人初始化完成并开始轮询")
        
        return application
        
    except Exception as e:
        logger.error(f"创建bot实例时出错: {e}", exc_info=True)
        raise

async def start_bot():
    """启动机器人轮询（如果尚未启动）"""
    try:
        application = get_bot()
        if not application or not application.running:  # 增加实例存在性检查
            application = await create_bot()
            if application:
                await application.updater.start_polling(drop_pending_updates=True)
                logger.info("机器人开始轮询")
        
        return application
            
    except Exception as e:
        logger.error(f"启动机器人轮询时出错: {e}", exc_info=True)
        raise

async def stop_bot():
    """停止机器人"""
    application = get_bot()
    if application and application.running:
        try:
            await application.updater.stop()
            await application.stop()
            await application.shutdown()
            logger.info("机器人已停止")
        except Exception as e:
            logger.error(f"停止机器人时出错: {e}", exc_info=True)

async def start_background_tasks():
    """启动后台任务"""
    try:
        # 创建任务组
        tasks = [
            asyncio.create_task(check_lottery_draws()),
            asyncio.create_task(ping_service())  # 添加唤醒服务任务
        ]
        
        # 等待所有任务
        await asyncio.gather(*tasks)
        
    except Exception as e:
        logger.error(f"启动后台任务时出错: {e}", exc_info=True)

# 定义导出的函数
__all__ = [
    'create_bot',
    'start_bot',
    'stop_bot',
    'get_bot',
    'set_application'
]