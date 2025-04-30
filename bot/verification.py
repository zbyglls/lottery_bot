from datetime import datetime
from telegram.ext import ContextTypes
from utils import logger
from app.database import DatabaseConnection


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
        with DatabaseConnection() as conn:
            # 检查抽奖状态
            conn.execute("SELECT status FROM lotteries WHERE id = ?", (lottery_id,))
            result = conn.fetchone()
            
            if result and result[0] == 'draft':
                # 如果仍然是草稿状态，更新记录状态为 cancelled
                conn.execute("UPDATE lotteries SET status = 'cancelled' WHERE id = ?", (lottery_id,))
                
                # 通知用户
                await context.bot.send_message(
                    chat_id=user_id,
                    text="⚠️ 抽奖创建已超时，记录已被清除。如需创建请重新使用 /new 命令。"
                )
            elif result and result[0] == 'creating':
                conn.execute("""
                    SELECT id, strftime('%s', 'now') - strftime('%s', created_at) as time_diff
                    FROM lotteries WHERE id = ?
                    """, (lottery_id,))
                result = conn.fetchone()
                lottery_id, time_diff = result
                if time_diff > 5400:  # 超过90分钟
                    conn.execute("UPDATE lotteries SET status = 'cancelled' WHERE id = ?", (lottery_id,))
                    await context.bot.send_message(
                        chat_id=user_id,
                        text="⚠️ 抽奖创建已超时，记录已被清除。如需创建请重新使用 /new 命令。"
                    )
            elif result and result[0] == 'cancelled':
                await context.bot.send_message(
                    chat_id=user_id,
                    text="⚠️ 抽奖创建已被取消，记录已被清除。如需创建请重新使用 /new 命令。"
                )
    except Exception as e:
        logger.error(f"检查抽奖创建状态时出错: {e}", exc_info=True)

async def check_lottery_status(lottery_id: str, user_id: str) -> dict:
    """检查抽奖ID并更新状态"""
    try:
        with DatabaseConnection() as c:
            # 检查抽奖是否存在且状态正确
            c.execute("""
                SELECT 
                    status,
                    creator_id,
                    created_at,
                    strftime('%s', 'now') - strftime('%s', created_at) as time_diff
                FROM lotteries 
                WHERE id = ?
            """, (lottery_id,))
            result = c.fetchone()
            
            if not result:
                return {
                    'valid': False,
                    'message': '该抽奖不存在或已被删除'
                }
                
            status, creator_id, created_at, time_diff = result
            
            # 验证创建者
            if str(creator_id) != str(user_id):
                return {
                    'valid': False,
                    'message': '你没有权限访问此抽奖'
                }
                
            # 检查状态
            if status == 'cancelled':
                return {
                    'valid': False,
                    'message': '该抽奖已被取消'
                }
            
            # 检查是否超时（60分钟）
            if int(time_diff) > 3600 and status == 'draft':
                # 更新过期记录状态为 cancelled
                c.execute("UPDATE lotteries SET status = 'cancelled' WHERE id = ?", (lottery_id,))
                logger.info(f"抽奖 {lottery_id} 已过期，状态更新为 cancelled")
                return {
                    'valid': False,
                    'message': '抽奖创建链接已过期'
                }
            if int(time_diff) < 3600 and status == 'draft':
                # 更新状态为 creating
                c.execute("""
                    UPDATE lotteries 
                    SET status = 'creating', updated_at = ? 
                    WHERE id = ?
                """, (datetime.now(), lottery_id))
                logger.info(f"抽奖 {lottery_id} 状态更新为 creating")
                return {
                    'valid': True,
                    'status': 'creating',
                    'created_at': datetime.now()
                }
                
            return {
                'valid': True,
                'status': status,
                'created_at': created_at
            }
            
    except Exception as e:
        logger.error(f"检查抽奖状态时出错: {e}", exc_info=True)
        return {
            'valid': False,
            'message': '系统错误，请稍后重试'
        }