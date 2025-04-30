import asyncio
import aiohttp
from app.database import DatabaseConnection
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
        required_name = lottery_data.get('required_username')
        require_text = ''
        if required_name:
            require_text = f"-- 参与者必须设置用户名\n"
        # 获取所有必要群组信息
        required_group_ids = lottery_data.get('required_groups', '').split(',')
        keyword_group_id = lottery_data.get('keyword_group_id', '')
        keyword = lottery_data.get('keyword', '')
        groups_text = ""
        try:
            if keyword_group_id:
                chat = await bot.get_chat(keyword_group_id)
                groups_text += f"-- 在群组 {chat.title} 中发送： {keyword}  参与抽奖\n"
            for group_id in required_group_ids:
                if group_id:
                    chat = await bot.get_chat(group_id)
                    if chat.type == 'supergroup':
                        groups_text += f"-- 加入群组： {chat.title} \n"
                    elif chat.type == 'channel':
                        groups_text += f"-- 加入频道： {chat.title}\n"
        except Exception as e:
            logger.error(f"获取群组信息时出错: {e}")
            groups_text = "\n".join([f"-- 加入频道 {gid}" for gid in required_group_ids if gid])
        
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
            f"{require_text}\n"
            f"{groups_text}\n"
            f"📆 开奖时间：{draw_time_text}\n\n"
        )

        # 为每个频道构建发布按钮
        keyboard = []
        if keyword_group_id:
            required_group_ids.append(keyword_group_id)
        for group_id in required_group_ids:
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
            f"使用 @YangShenBot 轻松创建抽奖"
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
                logger.debug(f"未找到匹配的抽奖活动")
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

def register_handlers(app):
    """注册所有非命令处理器"""
    logger.info("开始注册处理器")
    app.add_handler(MessageHandler(filters.PHOTO | filters.VIDEO, handle_media_message))
    app.add_handler(MessageHandler(filters.TEXT & (filters.GroupChat | filters.SUPERGROUP), handle_keyword_participate))
    logger.info("处理器注册完成")
