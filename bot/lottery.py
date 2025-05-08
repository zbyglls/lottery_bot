import random
from telegram import Bot
from app.database import DatabaseConnection
from bot.handlers import send_batch_winner_notifications, send_lottery_result_to_group
from utils import logger


async def draw_lottery(bot: Bot, lottery_id: str):
    """执行开奖"""
    try:
        with DatabaseConnection() as conn:

            #获取创建者ID
            conn.execute("""
                SELECT creator_id 
                FROM lotteries 
                WHERE id = ?
            """, (lottery_id,))
            creator_id = conn.fetchone()[0]

            #获取抽奖信息
            conn.execute("""
                SELECT keyword_group_id,required_groups
                FROM lottery_settings    
                WHERE lottery_id = ?
            """, (lottery_id,))
            keyword_group, required_groups = conn.fetchone()
            groups = required_groups.split(',')
            groups.append(keyword_group)
            groups = [_ for _ in set(groups) if _]
            lottery_info = {
                'lottery_id': lottery_id,
                'groups': groups
            }

            # 获取奖品信息
            conn.execute("""
                SELECT id, name, total_count 
                FROM prizes 
                WHERE lottery_id = ?
            """, (lottery_id,))
            prizes = conn.fetchall()

            # 获取参与者
            conn.execute("""
                SELECT id, user_id, nickname 
                FROM participants 
                WHERE lottery_id = ? AND status = 'active'
            """, (lottery_id,))
            participants = conn.fetchall()

            if not prizes or not participants:
                logger.error(f"抽奖 {lottery_id} 缺少奖品或参与者")
                return

            # 随机选择中奖者
            winners = []
            available_participants = participants.copy() 
            total_prize_count = sum(prize[2] for prize in prizes)  # 计算总奖品数
            if len(participants) < total_prize_count:
                logger.warning(f"参与人数({len(participants)})少于奖品总数({total_prize_count})")
            
            for prize_id, prize_name, count in prizes:
                if not available_participants:
                    logger.warning(f"奖品 {prize_name} 因参与者不足无法完全抽取")
                    break
                # 确定本轮可抽取的数量
                actual_count = min(count, len(available_participants))
                
                # 随机选择指定数量的中奖者
                current_winners = random.sample(available_participants, actual_count)

                # 记录中奖信息
                winners.extend([
                    (prize_id, winner[0], lottery_id) 
                    for winner in current_winners
                ])
                # 从可用池中移除已中奖者
                available_participants = [
                    p for p in available_participants 
                    if p not in current_winners
                ]

            # 记录中奖信息
            conn.executemany("""
                INSERT INTO prize_winners (
                    prize_id, participant_id, lottery_id, status, win_time
                ) VALUES (?, ?, ?, 'pending', CURRENT_TIMESTAMP)
            """, winners)

            # 更新抽奖状态
            conn.execute("""
                UPDATE lotteries 
                SET status = 'completed', updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (lottery_id,))
            

            # 发送中奖通知
            logger.info(f"准备给中奖者发送中奖通知：")
            await send_batch_winner_notifications(winners, creator_id)
            
            # 发送群组通知
            if lottery_info.get('groups'):
                await send_lottery_result_to_group(
                    winners,
                    lottery_info['groups']
                )
            logger.info(f"成功发送中奖通知和群组通知")

        return
    except Exception as e:
        logger.error(f"执行开奖时出错: {e}", exc_info=True)