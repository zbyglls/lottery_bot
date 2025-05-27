import random
from datetime import datetime, timezone
from telegram import Bot 
from app.database import MongoDBConnection
from bot.handlers import send_batch_winner_notifications, send_lottery_result_to_group
from utils import logger


async def draw_lottery(bot: Bot, lottery_id: str):
    """执行开奖"""
    try:
        # 获取数据库连接
        db = await MongoDBConnection.get_database()

        # 获取抽奖和设置信息
        pipeline = [
            {
                '$match': {'id': lottery_id}
            },
            {
                '$lookup': {
                    'from': 'lottery_settings',
                    'localField': 'lottery_id',
                    'foreignField': 'id',
                    'as': 'settings'
                }
            },
            {
                '$unwind': '$settings'
            }
        ]
        
        lottery_data = await db.lotteries.aggregate(pipeline).to_list(1)
        if not lottery_data:
            logger.error(f"未找到抽奖 {lottery_id}")
            return
            
        lottery_data = lottery_data[0]
        creator_id = lottery_data['creator_id']
        
        # 处理群组信息
        groups = []
        if lottery_data['settings'].get('keyword_group_id'):
            groups.append(lottery_data['settings']['keyword_group_id'])
        if lottery_data['settings'].get('required_groups'):
            groups.extend(lottery_data['settings']['required_groups'])
        groups = list(set(filter(None, groups)))
        
        lottery_info = {
            'lottery_id': lottery_id,
            'groups': groups
        }

        # 获取奖品信息
        prizes = await db.prizes.find(
            {'lottery_id': lottery_id},
            {'name': 1, 'total_count': 1}
        ).to_list(None)

        # 获取参与者
        participants = await db.participants.find(
            {
                'lottery_id': lottery_id
            },
            {
                'user_id': 1,
                'nickname': 1
            }
        ).to_list(None)

        if not prizes or not participants:
            logger.error(f"抽奖 {lottery_id} 缺少奖品或参与者")
            return

        # 随机选择中奖者
        winners = []
        available_participants = participants.copy()
        total_prize_count = sum(prize['total_count'] for prize in prizes)
        
        if len(participants) < total_prize_count:
            logger.warning(f"参与人数({len(participants)})少于奖品总数({total_prize_count})")
        
        now = datetime.now(timezone.utc)
        winners_to_insert = []
        
        for prize in prizes:
            if not available_participants:
                logger.warning(f"奖品 {prize['name']} 因参与者不足无法完全抽取")
                break
                
            # 确定本轮可抽取的数量
            actual_count = min(prize['total_count'], len(available_participants))
            
            # 随机选择指定数量的中奖者
            current_winners = random.sample(available_participants, actual_count)
            
            # 准备中奖记录
            for winner in current_winners:
                winner_doc = {
                    'prize_id': prize['_id'],
                    'participant_id': winner['_id'],
                    'lottery_id': lottery_id,
                    'status': 'pending',
                    'win_time': now
                }
                winners_to_insert.append(winner_doc)
                
                # 添加到winners列表用于通知
                winners.append((str(prize['_id']), str(winner['_id']), lottery_id))
                
            # 从可用池中移除已中奖者
            available_participants = [
                p for p in available_participants 
                if p not in current_winners
            ]

        # 批量插入中奖记录
        if winners_to_insert:
            await db.prize_winners.insert_many(winners_to_insert)

        # 更新抽奖状态
        await db.lotteries.update_one(
            {'id': lottery_id},
            {
                '$set': {
                    'status': 'completed',
                    'updated_at': now
                }
            }
        )

        # 发送中奖通知
        await send_batch_winner_notifications(winners, creator_id)
        
        # 发送群组通知
        if lottery_info['groups']:
            await send_lottery_result_to_group(
                winners,
                lottery_info['groups']
            )

        return True
        
    except Exception as e:
        logger.error(f"执行开奖时出错: {e}", exc_info=True)
        return False