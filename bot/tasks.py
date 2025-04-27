import asyncio
from datetime import datetime, timedelta
import aiohttp
from utils import logger
from bot.bot_instance import get_bot
from bot.lottery import draw_lottery
from app.database import DatabaseConnection

async def check_lottery_draws():
    """检查并执行需要开奖的抽奖活动"""
    while True:
        try:
            bot = get_bot()
            if not bot:
                logger.warning("机器人实例不可用，等待1分钟后重试")
                await asyncio.sleep(60)
                continue
                
            try:
                # 尝试获取机器人信息来检查是否在运行
                await bot.get_me()
            except Exception as e:
                logger.error(f"机器人未响应: {e}")
                await asyncio.sleep(60)
                continue

            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            with DatabaseConnection() as c:
                # 1. 检查定时开奖
                c.execute("""
                    SELECT l.id, ls.title
                    FROM lotteries l
                    JOIN lottery_settings ls ON l.id = ls.lottery_id
                    WHERE l.status = 'active' 
                    AND ls.draw_method = 'draw_time'
                    AND ls.draw_time <= %s
                """, (current_time,))
                time_draws = c.fetchall()

                # 2. 检查满人开奖
                c.execute("""
                    SELECT 
                        l.id, 
                        ls.title,
                        ls.participant_count as required_count,
                        COUNT(p.id) as current_count
                    FROM lotteries l
                    JOIN lottery_settings ls ON l.id = ls.lottery_id
                    LEFT JOIN participants p ON l.id = p.lottery_id
                    WHERE l.status = 'active'
                    AND ls.draw_method = 'draw_when_full'
                    GROUP BY l.id, ls.title, ls.participant_count
                    HAVING COUNT(p.id) >= ls.participant_count
                """)
                full_draws = c.fetchall()

            # 处理定时开奖
            for lottery_id, title in time_draws:
                try:
                    logger.info(f"执行定时开奖: {title} (ID: {lottery_id})")
                    await draw_lottery(bot, lottery_id)
                    logger.info(f"定时开奖完成: {title}")
                except Exception as e:
                    logger.error(f"执行定时开奖 {title} 时出错: {e}", exc_info=True)

            # 处理满人开奖
            for lottery_id, title, required_count, current_count in full_draws:
                try:
                    logger.info(f"执行满人开奖: {title} (ID: {lottery_id}, 参与人数: {current_count}/{required_count})")
                    await draw_lottery(bot, lottery_id)
                    logger.info(f"满人开奖完成: {title}")
                except Exception as e:
                    logger.error(f"执行满人开奖 {title} 时出错: {e}", exc_info=True)

            # 清理过期抽奖记录
            await cleanup_old_lotteries()
            # 每分钟检查一次
            await asyncio.sleep(60)
            
        except Exception as e:
            logger.error(f"检查抽奖任务时出错: {e}", exc_info=True)
            await asyncio.sleep(60)

async def cleanup_old_lotteries():
    """清理过期的抽奖记录"""
    try:
        # 计算一天前的时间
        one_day_ago = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d %H:%M:%S')
        
        with DatabaseConnection() as c:
            # 获取需要清理的抽奖ID
            c.execute("""
                SELECT l.id, ls.title, l.status 
                FROM lotteries l
                JOIN lottery_settings ls ON l.id = ls.lottery_id
                WHERE l.status IN ('completed', 'cancelled')
                AND l.updated_at <= %s
            """, (one_day_ago,))
            
            old_lotteries = c.fetchall()
            
            for lottery_id, title, status in old_lotteries:
                try:
                    # 按顺序删除相关记录
                    # 1. 删除中奖记录
                    c.execute("DELETE FROM prize_winners WHERE lottery_id = %s", (lottery_id,))
                    
                    # 2. 删除参与者记录
                    c.execute("DELETE FROM participants WHERE lottery_id = %s", (lottery_id,))
                    
                    # 3. 删除奖品记录
                    c.execute("DELETE FROM prizes WHERE lottery_id = %s", (lottery_id,))
                    
                    # 4. 删除抽奖设置
                    c.execute("DELETE FROM lottery_settings WHERE lottery_id = %s", (lottery_id,))
                    
                    # 5. 最后删除抽奖主记录
                    c.execute("DELETE FROM lotteries WHERE id = %s", (lottery_id,))
                    
                    logger.info(f"已清理抽奖记录: {title} (ID: {lottery_id}, 状态: {status})")
                    
                except Exception as e:
                    logger.error(f"清理抽奖 {title} (ID: {lottery_id}) 时出错: {e}", exc_info=True)
                    
    except Exception as e:
        logger.error(f"清理过期抽奖记录时出错: {e}", exc_info=True)

async def ping_service():
    """定时唤醒服务"""
    while True:
        try:
            # 构造请求 URL
            service_url = "https://yangshenbot.onrender.com/"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(service_url) as response:
                    if response.status == 200:
                        logger.info("服务唤醒成功")
                    else:
                        logger.warning(f"服务唤醒失败: {response.status}")
                        
        except Exception as e:
            logger.error(f"服务唤醒出错: {e}", exc_info=True)
            
        # 每14分钟唤醒一次
        await asyncio.sleep(14 * 60)
