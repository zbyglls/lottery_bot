import asyncio
from datetime import datetime, timedelta
import aiohttp
from app.database import DatabaseConnection
from config import YOUR_BOT
from utils import logger
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto, Update
from telegram.ext import MessageHandler, filters, ContextTypes
from .bot_instance import get_bot


async def handle_media(media_url):
    """处理媒体消息"""
    try:
        bot = get_bot()
        if not bot:
            logger.error("无法获取机器人实例")
            return False
        
        file_url = None
        try: 
            file = await bot.get_file(media_url)
            file_url = file.file_path
        except Exception as e:
            file_url = media_url

        # 下载文件
        async with aiohttp.ClientSession() as session:
            async with session.get(file_url) as response:
                if response.status == 200:
                    content = await response.read()
                    return content
                else:
                    logger.error(f"下载媒体文件失败: {response.status}")
                    return None
    except Exception as e:
        logger.error(f"处理媒体消息时出错: {e}", exc_info=True)
        return None


async def send_lottery_info_to_creator(creator_id: str, lottery_data: dict):
    """发送抽奖信息给创建者"""
    try:
        bot = get_bot()
        if not bot:
            logger.error("无法获取机器人实例")
            return False
        media_message = None
        # 添加媒体链接（如果有）
        if lottery_data.get('media_url'):
            media_message = await handle_media(lottery_data['media_url'])

        # 构建奖品列表文本
        prizes_text = "\n".join([
            f"-- {name}*{count}" 
            for name, count in zip(lottery_data['prize_names'], lottery_data['prize_counts'])
        ])
        required_name = lottery_data.get('require_username')
        # 获取所有必要群组信息
        required_groups = lottery_data.get('required_groups', '').split(',')
        keyword_group_id = lottery_data.get('keyword_group_id', '')
        keyword = lottery_data.get('keyword', '')
        message_group_id = lottery_data.get('message_group_id', '')
        message_count = lottery_data.get('message_count', '')
        message_check_time = lottery_data.get('message_check_time', '')

        requirements = []
        if required_name:
            requirements.append("❗️ 参与者必须设置用户名\n")
        if keyword and keyword_group_id:
            try:
                chat = await bot.get_chat(keyword_group_id)
                chat_link = f"<a href='https://t.me/{chat.username}'>{chat.title}</a>" if chat.username else chat.title
                requirements.append(f"❗️ 在群组{chat_link}中发送关键词：{keyword}\n")
            except Exception as e:
                logger.error(f"获取关键词群组{keyword_group_id}信息失败: {e}")
        if message_group_id:
            try:
                chat = await bot.get_chat(message_group_id)
                chat_link = f"<a href='https://t.me/{chat.username}'>{chat.title}</a>" if chat.username else chat.title
                requirements.append(f"❗️ {message_check_time}小时内在群组{chat_link}中发送消息：{message_count}条\n")
            except Exception as e:
                logger.error(f"获取消息群组 {message_group_id} 信息失败: {e}")
        if required_groups:
            for gid in required_groups:
                try:
                    chat = await bot.get_chat(gid)
                    chat_link = f"<a href='https://t.me/{chat.username}'>{chat.title}</a>" if chat.username else chat.title
                    if chat.type == 'supergroup': 
                        requirements.append(f"❗️ 需要加入群组：{chat_link}\n")
                    elif chat.type == 'channel':
                        requirements.append(f"❗️ 需要关注频道：{chat_link}\n")
                except Exception as e:
                    logger.error(f"获取群组 {gid} 信息失败: {e}")
                    requirements.append(f"❗️ 需要加入群组： {gid}\n")
        
        requirements_text = "\n".join(requirements) if requirements else ""
        
        # 构建开奖时间文本
        draw_time_text = (
            f"满{lottery_data['participant_count']}人自动开奖" 
            if lottery_data['draw_method'] == 'draw_when_full'
            else lottery_data['draw_time']
        )

        # 构建消息文本
        message = (
            f"养生品茶🍵： https://t.me/yangshyyds\n\n"
            f"📑抽奖标题： {lottery_data['title']}\n\n"
            f"📪抽奖说明：\n{lottery_data['description']}\n\n"
            f"🎁 奖品内容:\n{prizes_text}\n\n"
            f"🎫 参与条件:\n"
            f"{requirements_text}\n"
            f"📆 开奖时间：{draw_time_text}\n\n"
        )

        # 为每个频道构建发布按钮
        keyboard = []
        if keyword_group_id:
            required_groups.append(keyword_group_id)
        if message_group_id:
            required_groups.append(message_group_id)
        for group_id in set(required_groups):
            if group_id:
                try:
                    chat = await bot.get_chat(group_id)
                    if chat.type == 'supergroup':
                        keyboard.append([
                            InlineKeyboardButton(
                                f"📢 发布到群组： {chat.title}",
                                callback_data=f"publish_{lottery_data['lottery_id']}_{group_id}"
                            )
                        ])
                    elif chat.type == 'channel':
                        keyboard.append([
                            InlineKeyboardButton(
                                f"📢 发布到频道： {chat.title}",
                                callback_data=f"publish_{lottery_data['lottery_id']}_{group_id}"
                            )
                        ])
                except Exception as e:
                    logger.error(f"获取频道 {group_id} 信息时出错: {e}")
                    keyboard.append([
                        InlineKeyboardButton(
                            f"📢 发布到频道 {group_id}",
                            callback_data=f"publish_{lottery_data['lottery_id']}_{group_id}"
                        )
                    ])

        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # 发送消息
        if media_message:
            # 发送带媒体的消息
            if isinstance(media_message, bytes):
                # 如果是二进制数据（图片/视频）
                if lottery_data['media_type'] == 'image':
                    await bot.send_photo(
                        chat_id=creator_id,
                        photo=media_message,
                        caption=message,
                        reply_markup=reply_markup,
                        parse_mode='HTML'
                    )
                elif lottery_data['media_type'] == 'video':
                    await bot.send_video(
                        chat_id=creator_id,
                        video=media_message,
                        caption=message,
                        reply_markup=reply_markup,
                        parse_mode='HTML'
                    )
            else:
                # 如果是文件ID
                await bot.send_media_group(
                    chat_id=creator_id,
                    media=[InputMediaPhoto(media_message, caption=message)],
                    reply_markup=reply_markup
                )
        else:
            # 发送纯文本消息
            await bot.send_message(
                chat_id=creator_id,
                text=message,
                reply_markup=reply_markup,
                parse_mode='HTML',
                disable_web_page_preview=False
            )
        logger.info(f"已发送抽奖信息给创建者 {creator_id}")
        return True

    except Exception as e:
        logger.error(f"发送抽奖信息给创建者时出错: {e}", exc_info=True)
        return False

async def send_winner_notification(winner_id: int, lottery_info: dict, prize_info: dict):
    """发送中奖通知给获奖者
    
    Args:
        winner_id: 获奖者的用户ID
        lottery_info: 抽奖信息字典
        prize_info: 奖品信息字典
    """
    try:
        bot = get_bot()
        if not bot:
            logger.error("无法获取机器人实例")
            return False

        # 构建中奖通知消息
        message = (
            f"🎉 恭喜你中奖了！\n\n"
            f"🎲 抽奖活动：{lottery_info['title']}\n"
            f"🎁 获得奖品：{prize_info['name']}\n\n"
            f"📋 领奖说明：\n"
            f"请联系抽奖创建人领取奖品\n"
            f"🔔 温馨提示：\n"
            f"• 请确保你的账号可以接收私信\n"
            f"• 领奖时请提供本中奖通知截图"
        )

        # 添加确认按钮
        keyboard = [[
            InlineKeyboardButton("📞 联系创建人", url=f"https://t.me/{lottery_info['creator_name']}")
        ]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        # 发送通知
        try:
            await bot.send_message(
                chat_id=winner_id,
                text=message,
                reply_markup=reply_markup,
                parse_mode='HTML'
            )
            logger.info(f"已发送中奖通知给用户 {winner_id}")
            return True

        except Exception as e:
            logger.error(f"发送中奖通知给用户 {winner_id} 时出错: {e}")
            # 如果是因为用户封禁机器人导致的错误，记录到数据库
            if "Forbidden" in str(e):
                logger.warning(f"用户 {winner_id} 封禁了机器人")
            return False

    except Exception as e:
        logger.error(f"准备中奖通知时出错: {e}", exc_info=True)
        return False

# 批量发送中奖通知
async def send_batch_winner_notifications(winners: list, creator_id: str):
    """批量发送某个抽奖活动的所有中奖通知"""
    try:
        bot = get_bot()
        if not bot:
            logger.error("无法获取机器人实例")
            return False
        creator = await bot.get_chat(creator_id)
        creator_name = creator.username
        for _ in winners:
            prize_id, participant_id, lottery_id = _
            with DatabaseConnection() as c:
                # 获取中奖记录
                c.execute("SELECT user_id FROM participants WHERE id = ?", (participant_id,))
                user_id = c.fetchone()[0]
                c.execute("SELECT name FROM prizes WHERE id = ?", (prize_id,))
                prize_name = c.fetchone()[0]
                c.execute("SELECT title FROM lottery_settings WHERE lottery_id = ?", (lottery_id,))
                title = c.fetchone()[0]
                await send_winner_notification(
                    user_id,
                    {'lottery_id': lottery_id, 'title': title, 'creator_name': creator_name},
                    {'id': prize_id, 'name': prize_name}
                )
                # 添加延迟避免触发限制
                await asyncio.sleep(0.1)

    except Exception as e:
        logger.error(f"批量发送中奖通知时出错: {e}", exc_info=True)

async def send_lottery_result_to_group(winners: list, groups: list):
    """发送抽奖结果到群组
    
    Args:
        winners: 中奖者信息列表
        groups: 群组ID列表
    """
    try:
        bot = get_bot()
        if not bot:
            logger.error("无法获取机器人实例")
            return False
        lottery_id = winners[0][2]  # 获取抽奖ID
        # 获取抽奖和中奖信息
        with DatabaseConnection() as c:
            # 获取抽奖基本信息
            c.execute("""
                SELECT ls.title, ls.description,
                       l.creator_id,
                       (SELECT COUNT(*) FROM participants 
                        WHERE lottery_id = ls.lottery_id) as total_participants
                FROM lottery_settings ls
                JOIN lotteries l ON ls.lottery_id = l.id
                WHERE ls.lottery_id = ?
            """, (lottery_id,))
            lottery_info = c.fetchone()
            
            if not lottery_info:
                logger.error(f"未找到抽奖活动: {lottery_id}")
                return False
                
            title, description, creator_id, total_participants = lottery_info
            user = await bot.get_chat(creator_id)
            creator_name = user.username
            # 获取中奖信息
            winns = []
            for _ in winners:
                prize_id, participant_id, lottery_id = _
                c.execute("SELECT nickname, username FROM participants WHERE id = ?", (participant_id,))
                nickname, username = c.fetchall()[0]
                c.execute("SELECT name FROM prizes WHERE id = ?", (prize_id,))
                prize_name = c.fetchall()[0][0]
                winns.append((nickname, username, prize_name))

        # 构建开奖结果消息
        message = (
            f"🎉 抽奖结果公布！\n\n"
            f"📑 活动标题：{title}\n"
            f"👥 参与人数：{total_participants}\n\n"
            f"🎯 中奖名单：\n"
        )

        # 添加中奖者信息
        for winner in winns:
            nickname, username, prize_name = winner
            winner_text = f"@{username}" if username else nickname
            message += f"🎁 {prize_name}：{winner_text}\n"

        message += (
            f"\n📋 领奖方式：\n"
            f"请中奖者联系创建人 @{creator_name} 领取奖品\n\n"
            f"🔔 温馨提示：\n"
            f"• 请在规定时间内联系领取\n"
            f"• 逾期未领取视为自动放弃"
        )

        # 添加抽奖工具推广信息
        message += (
            f"\n\n🤖 机器人推荐：\n"
            f"使用 @{YOUR_BOT} 轻松创建抽奖"
        )

        # 发送消息到群组
        logger.info(f"准备发送开奖结果到群组: {groups}")
        for group_id in groups:
            try:
                await bot.send_message(
                    chat_id=group_id,
                    text=message,
                    parse_mode='HTML',
                    disable_web_page_preview=True
                )
                logger.info(f"已发送开奖结果到群组 {group_id}")
            except Exception as e:
                logger.error(f"发送开奖结果到群组 {group_id} 时出错: {e}")
    except Exception as e:
        logger.error(f"准备开奖结果通知时出错: {e}", exc_info=True)


async def handle_keyword_participate(update: Update, context):
    """处理用户发送关键词参与抽奖"""
    try:
        message = update.message
        if not message or not message.text:
            if not message:
                logger.error("update.message 为空")
                return
            if not message.text:
                logger.error("message.text 为空")
            return
        
        # 获取发送者信息
        user = message.from_user
        chat_id = message.chat.id
        logger.info(f"收到消息: {message.text} from {user.full_name} in chat {chat_id}")
        # 检查是否是群组消息
        if message.chat.type not in ['group', 'supergroup']:
            logger.debug(f"不是群组消息: {message.chat.type}")
            return
        
        # 获取对应的抽奖活动
        with DatabaseConnection() as c:
            logger.info(f"查找关键词匹配: chat_id={chat_id}, keyword={message.text.strip()}")
            c.execute("""
                SELECT 
                    l.id, ls.title, ls.require_username, 
                    ls.required_groups, ls.participant_count,
                    ls.draw_method, ls.draw_time,
                    (SELECT COUNT(*) FROM participants 
                     WHERE lottery_id = l.id) as current_count
                FROM lotteries l
                JOIN lottery_settings ls ON l.id = ls.lottery_id
                WHERE l.status = 'active'
                AND ls.keyword_group_id = ?
                AND ls.keyword = ?
            """, (str(chat_id), message.text.strip()))
            
            lottery = c.fetchone()
            if not lottery:
                return

            lottery_id, title = lottery[0], lottery[1]
            required_username = lottery[2]
            required_groups = lottery[3].split(',') if lottery[3] else []
            current_count = lottery[7]

            # 检查重复参与
            c.execute("""
                SELECT 1 FROM participants 
                WHERE lottery_id = ? AND user_id = ?
            """, (lottery_id, user.id))
            
            if c.fetchone():
                await message.reply_text(
                    "❌ 你已经参与过这个抽奖了",
                    reply_to_message_id=message.message_id
                )
                return
            
            # 检查用户名要求
            if required_username and not user.username:
                await message.reply_text(
                    "❌ 参与失败：请先设置用户名后再参与抽奖",
                    reply_to_message_id=message.message_id
                )
                return
            
            # 检查群组要求
            for group_id in required_groups:
                if group_id and group_id.strip():
                    try:
                        member = await context.bot.get_chat_member(group_id, user.id)
                        if member.status not in ['member', 'administrator', 'creator']:
                            chat = await context.bot.get_chat(group_id)
                            await message.reply_text(
                                f"❌ 参与失败：请先加入群组 {chat.title}",
                                reply_to_message_id=message.message_id
                            )
                            return
                    except Exception as e:
                        logger.error(f"检查用户群组成员状态时出错: {e}")
                        continue

            # 添加参与记录
            c.execute("""
                INSERT INTO participants (
                    lottery_id, user_id, nickname, username,
                    join_time, status
                ) VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP, 'active')
            """, (lottery_id, user.id, user.full_name, user.username))
            
            # 发送参与成功提示
            await message.reply_text(
                f"✅ 参与成功！\n\n"
                f"🎲 抽奖活动：{title}\n"
                f"👥 当前参与人数：{current_count + 1}\n\n"
                f"🔔 开奖后会通过机器人私信通知",
                reply_to_message_id=message.message_id
            )
            
            logger.info(f"用户 {user.full_name} (ID: {user.id}) 成功参与抽奖 {title}")

    except Exception as e:
        logger.error(f"处理关键词参与抽奖时出错: {e}", exc_info=True)

async def handle_media_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理接收到的媒体消息"""
    try:
        message = update.message
        media_info = []
        
        # 检查各种媒体类型
        if message.photo:
            photo = message.photo[-1]
            media_info.append(f"📸 图片 ID: {photo.file_id}")
            media_info.append(f"📏 尺寸: {photo.width}x{photo.height}")
            
        elif message.video:
            media_info.append(f"🎥 视频 ID: {message.video.file_id}")
            media_info.append(f"📏 尺寸: {message.video.width}x{message.video.height}")
            media_info.append(f"⏱️ 时长: {message.video.duration}秒")
            
        elif message.document:
            media_info.append(f"📄 文档 ID: {message.document.file_id}")
            if message.document.file_name:
                media_info.append(f"📋 文件名: {message.document.file_name}")
            if message.document.file_size:
                size_mb = message.document.file_size / 1024 / 1024
                media_info.append(f"📦 大小: {size_mb:.2f}MB")
                
        elif message.audio:
            media_info.append(f"🎵 音频 ID: {message.audio.file_id}")
            media_info.append(f"⏱️ 时长: {message.audio.duration}秒")
            if message.audio.title:
                media_info.append(f"📌 标题: {message.audio.title}")
                
        elif message.sticker:
            media_info.append(f"😀 贴纸 ID: {message.sticker.file_id}")
            media_info.append(f"📏 尺寸: {message.sticker.width}x{message.sticker.height}")
        
        # 发送媒体信息，使用 reply_to_message_id 代替 quote
        if media_info:
            await message.reply_text(
                "✅ 收到媒体文件：\n\n" + "\n".join(media_info),
                reply_to_message_id=message.message_id  # 使用这个替代 quote=True
            )
            
    except Exception as e:
        logger.error(f"处理媒体消息时出错: {e}", exc_info=True)
        await message.reply_text(
            "❌ 处理媒体文件时发生错误，请稍后重试。",
            reply_to_message_id=message.message_id  # 使用这个替代 quote=True
        )


async def check_user_messages(bot, user_id: int, group_id: str, required_count: int, check_hours: int, lottery_id: int, update=None) -> bool:
    """检查用户在群组中的发言数量（实时统计）
    
    Args:
        bot: Telegram bot 实例
        user_id: 用户ID
        group_id: 群组ID
        required_count: 要求的发言数量
        check_hours: 检查时间范围(小时)
        lottery_id: 抽奖ID

    Returns:
        bool: 是否满足发言要求
    """
    try:
        # 获取抽奖发布时间
        with DatabaseConnection() as c:
            c.execute("""
                SELECT l.updated_at, ls.message_count_tracked
                FROM lotteries l
                LEFT JOIN lottery_settings ls ON l.id = ls.lottery_id
                WHERE l.id = ?
            """, (lottery_id,))
            result = c.fetchone()
            
            if not result:
                return False
            
            publish_time = datetime.strptime(result[0], '%Y-%m-%d %H:%M:%S')
            message_count_tracked = result[1] or False

        # 如果还没有开始跟踪消息，创建消息跟踪记录
        if not message_count_tracked:
            try:
                with DatabaseConnection() as c:
                    # 更新抽奖设置，标记已开始跟踪
                    c.execute("""
                        UPDATE lottery_settings 
                        SET message_count_tracked = 1 
                        WHERE lottery_id = ?
                    """, (lottery_id,))
            except Exception as e:
                logger.error(f"创建消息计数表时出错: {e}")
                return False

        # 检查用户当前消息
        current_message = update.message if update else None
        current_time = datetime.now()

        # 获取用户现有的消息计数
        with DatabaseConnection() as c:
            c.execute("""
                SELECT message_count, last_message_time 
                FROM message_counts 
                WHERE lottery_id = ? AND user_id = ? AND group_id = ?
            """, (lottery_id, user_id, group_id))
            result = c.fetchone()

            if result:
                message_count, last_message_time = result
                last_message_time = datetime.strptime(last_message_time.split('.')[0], '%Y-%m-%d %H:%M:%S')
            else:
                message_count = 0
                last_message_time = publish_time

            # 如果有新消息且是文本消息，增加计数
            if (current_message and 
                current_message.text and 
                current_message.chat.id == int(group_id) and 
                current_message.from_user.id == user_id):
                
                # 检查消息时间是否在有效期内
                check_start_time = current_time - timedelta(hours=check_hours)
                if current_time >= check_start_time:
                    current_time = current_time.strftime('%Y-%m-%d %H:%M:%S')
                    message_count += 1
                    logger.info(f"用户 {user_id} 新增一条有效消息，当前数量: {message_count}")

                    # 更新数据库
                    c.execute("""
                        INSERT INTO message_counts 
                        (lottery_id, user_id, group_id, message_count, last_message_time)
                        VALUES (?, ?, ?, ?, ?)
                        ON CONFLICT(lottery_id, user_id, group_id) 
                        DO UPDATE SET 
                            message_count = ?,
                            last_message_time = ?
                    """, (
                        lottery_id, user_id, group_id, message_count, current_time,
                        message_count, current_time
                    ))

            # 检查是否达到要求
            if message_count >= required_count:
                logger.info(f"用户 {user_id} 已达到发言要求: {message_count}/{required_count}")
                return True

            logger.info(f"用户 {user_id} 发言数量不足: {message_count}/{required_count}")
            return False

    except Exception as e:
        logger.error(f"检查用户发言数量时出错: {e}", exc_info=True)
        return False


async def handle_message_count_participate(update: Update, context):
    """处理用户通过发言数量参与抽奖"""
    try:
        message = update.message
        if not message or not message.text:
            return
            
        user = message.from_user
        chat_id = message.chat.id
        
        # 检查是否是群组消息
        if message.chat.type not in ['group', 'supergroup']:
            return
            
        # 获取该群组的发言要求抽奖
        with DatabaseConnection() as c:
            c.execute("""
                SELECT 
                    l.id, ls.title, ls.require_username, 
                    ls.required_groups, ls.participant_count,
                    ls.message_count, ls.message_check_time,
                    (SELECT COUNT(*) FROM participants WHERE lottery_id = l.id) as current_count
                FROM lotteries l
                JOIN lottery_settings ls ON l.id = ls.lottery_id
                WHERE l.status = 'active'
                AND ls.message_group_id = ?
                AND ls.message_count > 0
            """, (str(chat_id),))
            
            lottery = c.fetchone()
            if not lottery:
                return
            logger.info(f"找到发言数量参与的抽奖活动: {lottery}")
            lottery_id, title = lottery[0], lottery[1]
            required_username = lottery[2]
            required_groups = lottery[3].split(',') if lottery[3] else []
            message_count = lottery[5]
            message_check_time = lottery[6]
            current_count = lottery[7]

            # 检查重复参与
            c.execute("""
                SELECT 1 FROM participants 
                WHERE lottery_id = ? AND user_id = ?
            """, (lottery_id, user.id))
            
            if c.fetchone():
                logger.info(f"用户 {user.full_name} (ID: {user.id}) 已参与过抽奖 {title}")
                return
            # 检查用户名要求
            if required_username and not user.username:
                await message.reply_text(
                    "❌ 参与失败：请先设置用户名后再参与抽奖",
                    reply_to_message_id=message.message_id
                )
                return
            # 检查群组要求
            for group_id in required_groups:
                if not group_id:
                    continue
                try:
                    member = await context.bot.get_chat_member(group_id, user.id)
                    if member.status not in ['member', 'administrator', 'creator']:
                        chat = await context.bot.get_chat(group_id)
                        await message.reply_text(
                            f"❌ 参与失败：请先加入群组 {chat.title}",
                            reply_to_message_id=message.message_id
                        )
                        return
                except Exception as e:
                    logger.error(f"检查用户群组成员状态时出错: {e}")
                    continue

            # 检查发言数量
            if not await check_user_messages(
                context.bot,
                user.id,
                chat_id,
                message_count,
                message_check_time,
                lottery_id,
                update
            ):
                return

            # 添加参与记录
            c.execute("""
                INSERT INTO participants (
                    lottery_id, user_id, nickname, username,
                    join_time, status
                ) VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP, 'active')
            """, (lottery_id, user.id, user.full_name, user.username))
            
            # 发送参与成功提示
            await message.reply_text(
                f"✅ 参与成功！\n\n"
                f"🎲 抽奖活动：{title}\n"
                f"👥 当前参与人数：{current_count + 1}\n\n"
                f"🔔 开奖后会通过机器人私信通知",
                reply_to_message_id=message.message_id
            )
            
            logger.info(f"用户 {user.full_name} (ID: {user.id}) 成功参与抽奖 {title}")
            # 清除该用户的消息记录数据
            c.execute("""
                DELETE FROM message_counts 
                WHERE lottery_id = ? AND user_id = ? AND group_id = ?
            """, (lottery_id, user.id, chat_id))
            
    except Exception as e:
        logger.error(f"处理发言数量参与抽奖时出错: {e}", exc_info=True)

async def check_keyword_message(bot, user_id: int, group_id: str, keyword: str) -> bool:
    """检查用户是否在群组发送过关键词"""
    try:
        current_time = datetime.now()
        check_time = current_time - timedelta(hours=1)  # 检查最近1小时
        
        async for message in bot.get_chat_history(
            chat_id=group_id,
            offset_date=check_time,
            limit=1000
        ):
            if (message.from_user and 
                message.from_user.id == user_id and 
                message.text and 
                message.text.strip() == keyword):
                return True
        
        return False
    except Exception as e:
        logger.error(f"检查关键词发送记录时出错: {e}")
        return False

def register_handlers(app):
    """注册所有非命令处理器"""
    logger.info("开始注册处理器")
    app.add_handler(MessageHandler(filters.PHOTO | filters.VIDEO, handle_media_message))
    app.add_handler(MessageHandler(filters.TEXT & (filters.GroupChat | filters.SUPERGROUP), handle_keyword_participate))
    app.add_handler(MessageHandler(filters.TEXT & (filters.GroupChat | filters.SUPERGROUP), handle_message_count_participate))
    logger.info("处理器注册完成")
