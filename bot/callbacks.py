from datetime import datetime
import sqlite3
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto, Update
from telegram.ext import ContextTypes
from app.database import DatabaseConnection
from bot.handlers import handle_media
from config import DB_PATH, YOUR_BOT
from utils import logger
from bot.verification import check_channel_subscription



async def verify_follow(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理关注验证回调"""
    query = update.callback_query
    user = query.from_user
    
    try:
        # 再次验证用户是否关注频道
        is_subscribed = await check_channel_subscription(context.bot, user.id)
        
        if not is_subscribed:
            await query.message.edit_text("❌ 您还未加入群组，请先加入后再验证")
            return
            
        # 用户已关注，删除验证消息
        await query.message.delete()
        
        # 调用新建抽奖逻辑
        from bot.commands import create_lottery
        await create_lottery(user, context, query.message.chat.id)
        
    except Exception as e:
        logger.error(f"验证关注状态时出错: {e}", exc_info=True)
        if query:
            await query.message.edit_text("验证失败，请稍后重试")

async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理按钮回调"""
    query = update.callback_query
    try:
        # 解析回调数据
        callback_data = query.data
        if callback_data.startswith('cancel_lottery_'):
            # 处理取消创建抽奖
            lottery_id = callback_data.replace('cancel_lottery_', '')
            logger.info(f"用户 {query.from_user.id} 请求取消创建抽奖 {lottery_id}")
            
            try:
                with sqlite3.connect(DB_PATH) as conn:
                    cursor = conn.cursor()
                    # 检查抽奖状态
                    cursor.execute("""
                        SELECT status, creator_id 
                        FROM lotteries 
                        WHERE id = ?
                    """, (lottery_id,))
                    result = cursor.fetchone()
                    
                    if not result:
                        await query.message.edit_text("❌ 抽奖记录不存在")
                        return
                        
                    status, creator_id = result
                    
                    # 验证操作权限
                    if creator_id != query.from_user.id:
                        await query.message.edit_text("⚠️ 你没有权限取消这个抽奖")
                        return
                    
                    # 删除抽奖记录
                    cursor.execute("DELETE FROM lotteries WHERE id = ?", (lottery_id,))
                    conn.commit()
                    
                    # 更新消息
                    await query.message.edit_text("✅ 抽奖创建已取消")
                    logger.info(f"抽奖 {lottery_id} 已被用户取消")
                    
            except sqlite3.Error as e:
                logger.error(f"取消抽奖时数据库错误: {e}", exc_info=True)
                await query.message.reply_text("❌ 取消抽奖失败，请稍后重试")
                
        elif callback_data == 'view_lotteries':
            # 处理查看抽奖列表
            try:
                with sqlite3.connect(DB_PATH) as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        SELECT l.id, l.status, ls.title, ls.draw_method, 
                               ls.participant_count, ls.draw_time,
                               (SELECT COUNT(*) FROM participants p WHERE p.lottery_id = l.id) as current_count
                        FROM lotteries l
                        JOIN lottery_settings ls ON l.id = ls.lottery_id
                        WHERE l.status = 'active'
                        ORDER BY l.created_at DESC
                        LIMIT 10
                    """)
                    active_lotteries = cursor.fetchall()

                    if not active_lotteries:
                        await query.message.edit_text(
                            "😔 目前没有正在进行的抽奖活动\n",
                            parse_mode='HTML'
                        )
                        return

                    message = "🎲 <b>当前进行中的抽奖活动</b>\n\n"
                    keyboard = []

                    for lottery in active_lotteries:
                        lottery_id, status, title, draw_method, max_participants, draw_time, current_count = lottery
                        
                        # 处理开奖方式显示
                        if draw_method == 'draw_when_full':
                            draw_info = f"👥 {current_count}/{max_participants}人"
                        else:
                            draw_info = f"⏰ {draw_time}"

                        message += (
                            f"📌 <b>{title}</b>\n"
                            f"📊 {draw_info}\n\n"
                        )

                        # 添加参与按钮
                        keyboard.append([
                            InlineKeyboardButton(
                                f"参与 {title}", 
                                callback_data=f'join_{lottery_id}'
                            )
                        ])

                    # 添加返回按钮
                    keyboard.append([
                        InlineKeyboardButton("🔙 返回", callback_data='back_to_main')
                    ])

                    await query.message.edit_text(
                        message,
                        reply_markup=InlineKeyboardMarkup(keyboard),
                        parse_mode='HTML'
                    )

            except Exception as e:
                logger.error(f"获取抽奖列表时出错: {e}", exc_info=True)
                await query.message.edit_text("❌ 获取抽奖列表失败，请稍后重试")
        elif callback_data == 'back_to_main':
            # 返回主菜单
            keyboard = [
                [InlineKeyboardButton("👀 查看抽奖活动", callback_data='view_lotteries')],
                [InlineKeyboardButton("📋 我的抽奖记录", callback_data='my_records')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            welcome_message = (
                f"👋 你好 {query.from_user.first_name}!\n\n"
                "欢迎使用抽奖机器人。你可以：\n"
                "1. 查看当前正在进行的抽奖\n"
                "2. 参与抽奖活动\n"
                "3. 查看我的抽奖记录"
            )
            
            await query.message.edit_text(
                welcome_message,
                reply_markup=reply_markup
            )
        elif callback_data == 'my_records':
            # 处理查看我的记录
            try:
                user_id = query.from_user.id
                with sqlite3.connect(DB_PATH) as conn:
                    cursor = conn.cursor()
                    
                    # 获取参与记录
                    cursor.execute("""
                        SELECT l.id, ls.title, p.status, p.join_time,
                               CASE 
                                   WHEN pw.id IS NOT NULL THEN pr.name
                                   ELSE NULL
                               END as prize_name
                        FROM participants p
                        JOIN lotteries l ON p.lottery_id = l.id
                        JOIN lottery_settings ls ON l.id = ls.lottery_id
                        LEFT JOIN prize_winners pw ON p.id = pw.participant_id
                        LEFT JOIN prizes pr ON pw.prize_id = pr.id
                        WHERE p.user_id = ?
                        ORDER BY p.join_time DESC
                        LIMIT 10
                    """, (user_id,))
                    records = cursor.fetchall()

                    if not records:
                        await query.message.edit_text(
                            "😔 你还没有参与过任何抽奖\n"
                            "点击下方按钮查看可参与的抽奖活动",
                            reply_markup=InlineKeyboardMarkup([[
                                InlineKeyboardButton("👀 查看抽奖活动", callback_data='view_lotteries'),
                                InlineKeyboardButton("🔙 返回", callback_data='back_to_main')
                            ]])
                        )
                        return

                    message = "🎯 <b>我的抽奖记录</b>\n\n"
                    for lottery_id, title, status, join_time, prize_name in records:
                        status_emoji = {
                            'active': '⏳',
                            'won': '🎉',
                            'lost': '💔'
                        }.get(status, '❓')

                        prize_info = f"🎁 中奖：{prize_name}" if prize_name else ""
                        message += (
                            f"📌 <b>{title}</b>\n"
                            f"{status_emoji} 状态：{status}\n"
                            f"⏰ 参与时间：{join_time}\n"
                            f"{prize_info}\n\n"
                        )

                    # 添加导航按钮
                    keyboard = [
                        [InlineKeyboardButton("👀 查看更多抽奖", callback_data='view_lotteries')],
                        [InlineKeyboardButton("🔙 返回", callback_data='back_to_main')]
                    ]

                    await query.message.edit_text(
                        message,
                        reply_markup=InlineKeyboardMarkup(keyboard),
                        parse_mode='HTML'
                    )
            except Exception as e:
                logger.error(f"获取参与记录时出错: {e}", exc_info=True)
                await query.message.edit_text("❌ 获取参与记录失败，请稍后重试")
        elif callback_data.startswith('join_'):
            # 处理参与抽奖
            try:
                lottery_id = callback_data.split('_')[1]
                user = query.from_user

                # 检查抽奖信息
                with sqlite3.connect(DB_PATH) as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        SELECT ls.title, ls.require_username, ls.required_groups,
                               ls.participant_count, l.status,
                               (SELECT COUNT(*) FROM participants WHERE lottery_id = l.id) as current_count
                        FROM lottery_settings ls
                        JOIN lotteries l ON ls.lottery_id = l.id
                        WHERE l.id = ?
                    """, (lottery_id,))
                    result = cursor.fetchone()

                    if not result:
                        await query.message.edit_text("❌ 抽奖活动不存在")
                        return

                    title, require_username, required_groups, max_participants, status, current_count = result

                    # 检查抽奖状态
                    if status != 'active':
                        await query.message.edit_text("❌ 该抽奖活动已结束或暂停")
                        return

                    # 检查是否已参与
                    cursor.execute("""
                        SELECT id FROM participants 
                        WHERE lottery_id = ? AND user_id = ?
                    """, (lottery_id, user.id))
                    if cursor.fetchone():
                        await query.message.edit_text("❌ 你已经参与过这个抽奖了")
                        return

                    # 检查人数限制
                    if current_count >= max_participants:
                        await query.message.edit_text("❌ 抽奖参与人数已满")
                        return

                    # 检查用户名要求
                    if require_username and not user.username:
                        await query.message.reply_text("❌ 参与此抽奖需要设置用户名")
                        return

                    # 检查群组要求
                    if required_groups:
                        groups = required_groups.split(',')
                        for group_id in groups:
                            try:
                                member = await context.bot.get_chat_member(group_id, user.id)
                                if member.status in ['left', 'kicked', 'restricted']:
                                    chat = await context.bot.get_chat(group_id)
                                    keyboard = [[InlineKeyboardButton(
                                        "👉 加入群组",
                                        url=f"https://t.me/{chat.username}"
                                    )]]
                                    await query.message.reply_text(
                                        f"❌ 需要先加入群组 {chat.title}",
                                        reply_markup=InlineKeyboardMarkup(keyboard)
                                    )
                                    return
                            except Exception as e:
                                logger.error(f"检查群组成员状态时出错: {e}")
                                continue

                    # 添加参与记录
                    join_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    cursor.execute("""
                        INSERT INTO participants (
                            lottery_id, user_id, nickname, username, 
                            status, join_time
                        ) VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                        lottery_id,
                        user.id,
                        user.first_name,
                        user.username,
                        'active',
                        join_time
                    ))
                    conn.commit()
                    chat_type = query.message.chat.type
                    if chat_type in ['group', 'supergroup']:
                        # 添加聊天消息确认
                        await context.bot.send_message(
                            chat_id=query.message.chat_id,
                            text=f"🎉 恭喜 {user.first_name} 成功参与抽奖《{title}》！"
                        )
                    else:
                        await context.bot.send_message(
                            chat_id=query.message.chat_id,
                            text=f"🎉 恭喜 {user.first_name} 成功参与抽奖《{title}》！"
                        )
                        # 刷新抽奖列表
                        await refresh_lottery_list(update, context)
                        await query.message.delete()  # 删除临时提示消息

            except Exception as e:
                logger.error(f"处理参与抽奖时出错: {e}", exc_info=True)
                await query.message.reply_text("❌ 参与失败，请稍后重试")
        elif callback_data.startswith('publish_'):
            try:
                parts = callback_data.split('_')
                if len(parts) != 3:
                    logger.error(f"回调数据格式错误: {callback_data}")
                    await query.message.reply_text("❌ 回调数据格式错误")
                    return
                _, lottery_id, group_id = parts
                # 从数据库获取抽奖信息
                with DatabaseConnection() as c:
                    # 获取抽奖基本信息
                    c.execute("""
                        SELECT ls.title, ls.description, ls.media_type, ls.media_url, 
                            ls.draw_method, ls.participant_count, ls.draw_time,
                            ls.required_groups, ls.keyword_group_id, ls.keyword,
                            ls.require_username
                        FROM lottery_settings ls
                        WHERE ls.lottery_id = ?
                    """, (lottery_id,))
                    lottery_data = c.fetchone()
                    if not lottery_data:
                        await query.message.reply_text("❌ 找不到抽奖信息")
                        return
                    (title, description, media_type, media_url, draw_method, participant_count, 
                     draw_time, required_groups, keyword_group_id, keyword, 
                    require_username) = lottery_data
                    # 获取奖品信息
                    c.execute("SELECT name, total_count FROM prizes WHERE lottery_id = ?", (lottery_id,))
                    prizes = c.fetchall()
                # 构建抽奖消息
                prize_text = "\n".join([f"🎁 {name} x {count}" for name, count in prizes])
                requirements = []
                if require_username:
                    requirements.append("❗️ 需要设置用户名")
                if keyword and keyword_group_id:
                    requirements.append(f"❗️ 在群组中发送关键词：{keyword}")
                if required_groups:
                    group_ids = required_groups.split(',')
                    for gid in group_ids:
                        try:
                            chat = await context.bot.get_chat(gid)
                            requirements.append(f"❗️ 需要加入：{chat.title}")
                        except Exception as e:
                            logger.error(f"获取群组 {gid} 信息失败: {e}")
                requirements_text = "\n".join(requirements) if requirements else "无特殊要求"
                # 处理开奖时间显示
                if draw_method == 'draw_when_full':
                    draw_info = f"👥 满{participant_count}人自动开奖"
                else:
                    draw_info = f"⏰ {draw_time} 准时开奖"
                message = (
                    f"🎉 抽奖活动\n\n"
                    f"📢 抽奖标题： {title}\n\n"
                    f"📝 抽奖描述： \n{description}\n\n"
                    f"🎁 奖品清单：\n{prize_text}\n\n"
                    f"📋 参与要求：\n{requirements_text}\n\n"
                    f"⏳ 开奖方式：\n{draw_info}\n\n"
                    f"🔔 开奖后会在机器人处通知获奖信息\n"
                    f"🤖 @{YOUR_BOT}"
                )
                    # 添加媒体消息（如果有）
                if media_url:
                    media_message = await handle_media(media_url)
                
                # 创建参与按钮
                try:
                    chat = await context.bot.get_chat(group_id)
                except Exception as e:
                    logger.error(f"获取群组/频道信息失败: {e}")
                    await query.message.reply_text("❌ 获取群组信息失败，请重试")
                    return
                if chat.type == 'channel':
                    keyboard = [
                        [InlineKeyboardButton("🎲 私聊机器人参与抽奖", url=f"https://t.me/{YOUR_BOT}?start=join_{lottery_id}")]
                    ]
                elif chat.type == 'group' or chat.type == 'supergroup':
                    keyboard = [
                        [InlineKeyboardButton("🎲 参与抽奖", callback_data=f"join_{lottery_id}")]
                    ]
                reply_markup = InlineKeyboardMarkup(keyboard)

                # 发送到群组/频道
                if media_message:
                    # 发送带媒体的消息
                    if isinstance(media_message, bytes):
                        if media_type == 'image':
                            sent_message = await context.bot.send_photo(
                                chat_id=group_id,
                                photo=media_message,
                                caption=message,
                                reply_markup=reply_markup,
                                parse_mode='HTML'
                            )
                        elif media_type == 'video':
                            sent_message = await context.bot.send_video(
                                chat_id=group_id,
                                video=media_message,
                                caption=message,
                                reply_markup=reply_markup,
                                parse_mode='HTML'
                            )
                        else:
                            # 如果是文件ID
                            sent_message = await context.bot.send_media_group(
                                chat_id=group_id,
                                media=[InputMediaPhoto(media_message, caption=message)],
                                reply_markup=reply_markup
                            )
                    else:
                        # 发送纯文本消息
                       sent_message = await context.bot.send_message(
                            chat_id=group_id,
                            text=message,
                            reply_markup=reply_markup,
                            parse_mode='HTML',
                            disable_web_page_preview=False
                        )    
                if sent_message:
                    # 发布成功提示    
                    await context.bot.send_message(chat_id=query.message.chat_id, text="✅ 发布成功！")
                    logger.info(f"query.message.chat_id: {query.message.chat_id}, typy:{type(query.message.chat_id)}")
                    if group_id != "-1001526013692" and group_id != "-1001638087196":
                        if media_message:
                            # 发送带媒体的消息
                            if isinstance(media_message, bytes):
                                if media_type == 'image':
                                    await context.bot.send_photo(
                                        chat_id="-1001526013692",
                                        photo=media_message,
                                        caption=message,
                                        reply_markup=reply_markup,
                                        parse_mode='HTML'
                                    )
                                elif media_type == 'video':
                                    await context.bot.send_video(
                                        chat_id="-1001526013692",
                                        video=media_message,
                                        caption=message,
                                        reply_markup=reply_markup,
                                        parse_mode='HTML'
                                    )
                                else:
                                    # 如果是文件ID
                                    await context.bot.send_media_group(
                                        chat_id="-1001526013692",
                                        media=[InputMediaPhoto(media_message, caption=message)],
                                        reply_markup=reply_markup
                                    )
                            else:
                                # 发送纯文本消息
                                await context.bot.send_message(
                                    chat_id="-1001526013692",
                                    text=message,
                                    reply_markup=reply_markup,
                                    parse_mode='HTML',
                                    disable_web_page_preview=False
                                )
                        logger.info(f"发布到频道 - -1001526013692")
                    logger.info(f"抽奖 {lottery_id} 已成功发布到群组 {group_id}")
                else:
                    await context.bot.send_message(chat_id=query.message.chat_id, text="❌ 发布失败，请重试")
            except Exception as e:
                logger.error(f"发布抽奖时出错: {e}", exc_info=True)
                await context.bot.send_message(chat_id=query.message.chat_id, text="❌ 发布失败，请稍后重试")

    except Exception as e:
        logger.error(f"处理回调查询时出错: {e}", exc_info=True)
        await query.message.reply_text("❌ 处理请求时出错，请稍后重试")

async def refresh_lottery_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """刷新抽奖列表"""
    query = update.callback_query
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT l.id, l.status, ls.title, ls.draw_method, 
                       ls.participant_count, ls.draw_time,
                       (SELECT COUNT(*) FROM participants p WHERE p.lottery_id = l.id) as current_count
                FROM lotteries l
                JOIN lottery_settings ls ON l.id = ls.lottery_id
                WHERE l.status = 'active'
                ORDER BY l.created_at DESC
                LIMIT 10
            """)
            active_lotteries = cursor.fetchall()

            message = "🎲 <b>当前进行中的抽奖活动</b>\n\n"
            keyboard = []

            if not active_lotteries:
                message += "😔 目前没有正在进行的抽奖活动\n"
            else:
                for lottery in active_lotteries:
                    lottery_id, status, title, draw_method, max_participants, draw_time, current_count = lottery
                    
                    # 处理开奖方式显示
                    if draw_method == 'draw_when_full':
                        draw_info = f"👥 {current_count}/{max_participants}人"
                    else:
                        draw_info = f"⏰ {draw_time}"

                    message += (
                        f"📌 <b>{title}</b>\n"
                        f"📊 {draw_info}\n\n"
                    )

                    # 添加参与按钮
                    keyboard.append([
                        InlineKeyboardButton(
                            f"参与 {title}", 
                            callback_data=f'join_{lottery_id}'
                        )
                    ])

            # 添加返回按钮
            keyboard.append([
                InlineKeyboardButton("🔙 返回", callback_data='back_to_main')
            ])

            await query.message.edit_text(
                message,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='HTML'
            )

    except Exception as e:
        logger.error(f"刷新抽奖列表时出错: {e}", exc_info=True)
        await query.message.reply_text("❌ 刷新列表失败，请稍后重试")