import asyncio
from datetime import datetime, timedelta, timezone
import aiohttp
from bson.objectid import ObjectId 
from config import SERVICE_URL
from utils import logger
from bot.bot_instance import get_bot
from bot.lottery import draw_lottery
from app.database import MongoDBConnection

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

            current_time = datetime.now(timezone.utc)
            db = await MongoDBConnection.get_database()
            # 1. 查找定时开奖的抽奖
            pipeline_time = [
                {
                    '$match': {
                        'status': 'active'
                    }
                },
                {
                    '$lookup': {
                        'from': 'lottery_settings',
                        'localField': 'id',
                        'foreignField': 'lottery_id',
                        'as': 'settings'
                    }
                },
                {
                    '$unwind': '$settings'
                },
                {
                    '$match': {
                        'settings.draw_method': 'draw_at_time',
                        'settings.draw_time': {'$lte': current_time}
                    }
                },
                {
                    '$project': {
                        'id': 1,
                        'title': '$settings.title'
                    }
                }
            ]
            time_draws = await db.lotteries.aggregate(pipeline_time).to_list(None)
            logger.info(f"定时开奖抽奖活动: {time_draws}")

            # 2. 查找满人开奖的抽奖
            pipeline_full = [
                {
                    '$match': {
                        'status': 'active'
                    }
                },
                {
                    '$lookup': {
                        'from': 'lottery_settings',
                        'localField': 'id',
                        'foreignField': 'lottery_id',
                        'as': 'settings'
                    }
                },
                {
                    '$unwind': '$settings'
                },
                {
                    '$match': {
                        'settings.draw_method': 'draw_when_full'
                    }
                },
                {
                    '$lookup': {
                        'from': 'participants',
                        'localField': 'id',
                        'foreignField': 'lottery_id',
                        'pipeline': [{'$count': 'count'}],
                        'as': 'participant_count'
                    }
                },
                {
                    '$match': {
                        '$expr': {
                            '$gte': [
                                {'$first': '$participant_count.count'},
                                '$settings.participant_count'
                            ]
                        }
                    }
                },
                {
                    '$project': {
                        'id': 1,
                        'title': '$settings.title',
                        'required_count': '$settings.participant_count',
                        'current_count': {'$first': '$participant_count.count'}
                    }
                }
            ]
            full_draws = await db.lotteries.aggregate(pipeline_full).to_list(None)
            logger.info(f"满人开奖抽奖活动: {full_draws}")

            # 处理定时开奖
            for lottery in time_draws:
                try:
                    logger.info(f"执行定时开奖: {lottery['title']} (ID: {lottery['id']})")
                    await draw_lottery(bot, lottery['id'])
                    logger.info(f"定时开奖完成: {lottery['title']}")
                except Exception as e:
                    logger.error(f"执行定时开奖 {lottery['title']} 时出错: {e}", exc_info=True)

            # 处理满人开奖
            for lottery in full_draws:
                try:
                    logger.info(
                        f"执行满人开奖: {lottery['title']} "
                        f"(ID: {lottery['id']}, "
                        f"参与人数: {lottery['current_count']}/{lottery['required_count']})"
                    )
                    await draw_lottery(bot, lottery['id'])
                    logger.info(f"满人开奖完成: {lottery['title']}")
                except Exception as e:
                    logger.error(f"执行满人开奖 {lottery['title']} 时出错: {e}", exc_info=True)

            # 清理过期抽奖记录
            await cleanup_old_lotteries()
            await asyncio.sleep(60)
            
        except Exception as e:
            logger.error(f"检查抽奖任务时出错: {e}", exc_info=True)
            await asyncio.sleep(60)

async def cleanup_old_lotteries():
    """清理过期的抽奖记录"""
    try:
        # 计算一天前的时间
        one_day_ago = datetime.now(timezone.utc) - timedelta(days=1)
        db = await MongoDBConnection.get_database()
        
        # 获取需要清理的抽奖
        pipeline = [
            {
                '$match': {
                    'status': {'$in': ['completed', 'cancelled']},
                    'updated_at': {'$lte': one_day_ago}
                }
            },
            {
                '$lookup': {
                    'from': 'lottery_settings',
                    'localField': 'id',
                    'foreignField': 'lottery_id',
                    'as': 'settings'
                }
            },
            {
                '$unwind': '$settings'
            }
        ]
        
        old_lotteries = await db.lotteries.aggregate(pipeline).to_list(None)
        logger.info(f"需要清理的抽奖活动: {old_lotteries}")
        for lottery in old_lotteries:
            try:
                lottery_id = lottery['id']
                title = lottery['settings']['title']
                logger.info(f"清理抽奖活动: {title} (ID: {lottery_id}, 状态: {lottery['status']})")
                # 删除相关记录
                await asyncio.gather(
                    db.prize_winners.delete_many({'lottery_id': lottery_id}),
                    db.participants.delete_many({'lottery_id': lottery_id}),
                    db.prizes.delete_many({'lottery_id': lottery_id}),
                    db.lottery_settings.delete_many({'lottery_id': lottery_id}),
                    db.lotteries.delete_one({'id': lottery_id})
                )
                
                logger.info(f"已清理抽奖记录: {title} (ID: {lottery_id}, 状态: {lottery['status']})")
                
            except Exception as e:
                logger.error(f"清理抽奖 {title} (ID: {lottery_id}) 时出错: {e}", exc_info=True)
                
    except Exception as e:
        logger.error(f"清理过期抽奖记录时出错: {e}", exc_info=True)

async def ping_service():
    """定时唤醒服务"""
    while True:
        try:
            # 构造请求 URL
            service_url = SERVICE_URL
            
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
