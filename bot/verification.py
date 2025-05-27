from datetime import datetime, timezone
from telegram.ext import ContextTypes
from utils import logger
from app.database import MongoDBConnection


async def check_channel_subscription(bot, user_id: int, channel_id: str = '@yangshyyds') -> bool:
    """检查用户是否关注了指定频道"""
    try:
        chat_member = await bot.get_chat_member(chat_id=channel_id, user_id=user_id)
        return chat_member.status not in ['left', 'kicked', 'restricted']
    except Exception as e:
        logger.error(f"检查频道关注状态时出错: {e}", exc_info=True)
        return False
              
async def check_lottery_creation(context: ContextTypes.DEFAULT_TYPE):
    """检查抽奖是否已完成创建"""
    job = context.job
    lottery_id = job.data['lottery_id']
    user_id = job.data['user_id']
    
    try:
        db = await MongoDBConnection.get_database()
        
        # 检查抽奖状态
        lottery = await db.lotteries.find_one({'id': lottery_id})
        
        if not lottery:
            logger.error(f"找不到抽奖记录: {lottery_id}")
            return
            
        now = datetime.now(timezone.utc)
        created_at = lottery['created_at']
        created_at = created_at.replace(tzinfo=timezone.utc)
        time_diff = (now - lottery['created_at']).total_seconds()
        
        if lottery['status'] == 'draft':
            # 如果仍然是草稿状态，更新记录状态为 cancelled
            await db.lotteries.update_one(
                {'id': lottery_id},
                {
                    '$set': {
                        'status': 'cancelled',
                        'updated_at': now
                    }
                }
            )
            
            await context.bot.send_message(
                chat_id=user_id,
                text="⚠️ 抽奖创建已超时，记录已被清除。如需创建请重新使用 /new 命令。"
            )
            
        elif lottery['status'] == 'creating' and time_diff > 5400:  # 超过90分钟
            await db.lotteries.update_one(
                {'id': lottery_id},
                {
                    '$set': {
                        'status': 'cancelled',
                        'updated_at': now
                    }
                }
            )
            
            await context.bot.send_message(
                chat_id=user_id,
                text="⚠️ 抽奖创建已超时，记录已被清除。如需创建请重新使用 /new 命令。"
            )
            
        elif lottery['status'] == 'cancelled':
            await context.bot.send_message(
                chat_id=user_id,
                text="⚠️ 抽奖创建已被取消，记录已被清除。如需创建请重新使用 /new 命令。"
            )
            
    except Exception as e:
        logger.error(f"检查抽奖创建状态时出错: {e}", exc_info=True)

async def check_lottery_status(lottery_id: str, user_id: str) -> dict:
    """检查抽奖ID并更新状态"""
    try:
        db = await MongoDBConnection.get_database()
        
        # 检查抽奖是否存在且状态正确
        lottery = await db.lotteries.find_one(
            {'id': lottery_id},
            {
                'status': 1,
                'creator_id': 1,
                'created_at': 1
            }
        )
        
        if not lottery:
            return {
                'valid': False,
                'message': '该抽奖不存在或已被删除'
            }
            
        # 计算时间差
        now = datetime.now(timezone.utc)
        created_at = lottery['created_at']
        created_at = created_at.replace(tzinfo=timezone.utc)
        time_diff = (now - created_at).total_seconds()
        
        # 验证创建者
        if str(lottery['creator_id']) != str(user_id):
            return {
                'valid': False,
                'message': '你没有权限访问此抽奖'
            }
            
        # 检查状态
        if lottery['status'] == 'cancelled':
            return {
                'valid': False,
                'message': '该抽奖已被取消'
            }
        
        # 检查是否超时（60分钟）
        if time_diff > 3600 and lottery['status'] == 'draft':
            # 更新过期记录状态为 cancelled
            await db.lotteries.update_one(
                {'id': lottery_id},
                {
                    '$set': {
                        'status': 'cancelled',
                        'updated_at': now
                    }
                }
            )
            
            return {
                'valid': False,
                'message': '抽奖创建链接已过期'
            }
            
        if time_diff < 3600 and lottery['status'] == 'draft':
            # 更新状态为 creating
            await db.lotteries.update_one(
                {'id': lottery_id},
                {
                    '$set': {
                        'status': 'creating',
                        'updated_at': now
                    }
                }
            )
            return {
                'valid': True,
                'status': 'creating',
                'created_at': now
            }
            
        return {
            'valid': True,
            'status': lottery['status'],
            'created_at': lottery['created_at']
        }
            
    except Exception as e:
        logger.error(f"检查抽奖状态时出错: {e}", exc_info=True)
        return {
            'valid': False,
            'message': '系统错误，请稍后重试'
        }