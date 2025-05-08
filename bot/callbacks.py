from datetime import datetime, timezone
from bson import Int64
from telegram import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto, Update
from telegram.ext import ContextTypes
from telegram.error import BadRequest
from app.database import MongoDBConnection
from bot.handlers import check_keyword_message, check_user_messages, handle_media
from config import YOUR_BOT
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
        db = await MongoDBConnection.get_database()
        callback_data = query.data
        if callback_data.startswith('cancel_lottery_'):
            # 处理取消创建抽奖
            lottery_id = callback_data.replace('cancel_lottery_', '')
            logger.info(f"用户 {query.from_user.id} 请求取消创建抽奖 {lottery_id}")
            
            try:
                # 检查抽奖状态
                lottery = await db.lotteries.find_one({'id': lottery_id})
                    
                if not lottery:
                    await query.message.edit_text("❌ 抽奖记录不存在")
                    return
                        
                # 验证操作权限
                if lottery['creator_id'] != query.from_user.id:
                    await query.message.edit_text("⚠️ 你没有权限取消这个抽奖")
                    return
                    
                # 更新抽奖状态
                result = await db.lotteries.update_one(
                    {'id': lottery_id},
                    {'$set': {
                        'status': 'cancelled',
                        'updated_at': datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
                    }}
                )
                    
                # 更新消息
                if result.modified_count > 0:
                    await query.message.edit_text("✅ 抽奖创建已取消")
                    logger.info(f"抽奖 {lottery_id} 已被用户取消")
                else:
                    await query.message.edit_text("❌ 取消抽奖失败，请重试")
                    
            except Exception as e:
                logger.error(f"取消抽奖时数据库错误: {e}", exc_info=True)
                await query.message.reply_text("❌ 取消抽奖失败，请稍后重试")
                
        elif callback_data == 'view_lotteries':
            # 处理查看抽奖列表
            try:
                pipeline = [
                    {
                        '$match': {'status': 'active'}
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
                    },
                    {
                        '$lookup': {
                            'from': 'participants',
                            'localField': 'lottery_id',
                            'foreignField': 'id',
                            'pipeline': [{'$count': 'count'}],
                            'as': 'participant_count'
                        }
                    },
                    {
                        '$sort': {'created_at': -1}
                    },
                    {
                        '$limit': 10
                    }
                ]
                active_lotteries = await db.lotteries.aggregate(pipeline).to_list(None)

                if not active_lotteries:
                    await query.message.edit_text(
                        "😔 目前没有正在进行的抽奖活动\n",
                        parse_mode='HTML'
                    )
                    return

                message = "🎲 <b>当前进行中的抽奖活动</b>\n\n"
                keyboard = []

                for lottery in active_lotteries:
                    current_count = lottery['participant_count'][0]['count'] if lottery['participant_count'] else 0
                    settings = lottery['settings']  

                    # 处理开奖方式显示
                    if settings['draw_method'] == 'draw_when_full':
                        draw_info = f"👥 {current_count}/{settings['max_participants']}人"
                    else:
                        draw_info = f"⏰ {settings['draw_time']}"

                    message += (
                        f"📌 <b>{settings['title']}</b>\n"
                        f"📊 {draw_info}\n\n"
                    )

                    # 添加参与按钮
                    keyboard.append([
                        InlineKeyboardButton(
                            f"参与 {settings['title']}", 
                            callback_data=f'join_{lottery["lottery_id"]}'
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
                db = await MongoDBConnection.get_database()
                    
                # 获取参与记录
                pipeline = [
                    {
                        '$match': {
                            'user_id': user_id
                        }
                    },
                    {
                        '$lookup': {
                            'from': 'lotteries',
                            'localField': 'lottery_id',
                            'foreignField': 'lottery_id',
                            'as': 'lottery'
                        }
                    },
                    {
                        '$unwind': '$lottery'
                    },
                    {
                        '$lookup': {
                            'from': 'lottery_settings',
                            'localField': 'lottery_id',
                            'foreignField': 'lottery_id',
                            'as': 'settings'
                        }
                    },
                    {
                        '$unwind': '$settings'
                    },
                    {
                        '$lookup': {
                            'from': 'prize_winners',
                            'localField': '_id',
                            'foreignField': 'participant_id',
                            'as': 'winner'
                        }
                    },
                    {
                        '$lookup': {
                            'from': 'prizes',
                            'localField': 'winner.prize_id',
                            'foreignField': '_id',
                            'as': 'prize'
                        }
                    },
                    {
                        '$sort': {'join_time': -1}
                    },
                    {
                        '$limit': 10
                    }
                ]
                records = await db.participants.aggregate(pipeline).to_list(None)

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
                for record in records:
                    status_emoji = {
                        'active': '⏳',
                        'won': '🎉',
                        'lost': '💔'
                    }.get(record['status'], '❓')

                    prize_info = ""
                    if record.get('prize'):
                        prize = record['prize'][0]
                        prize_info = f"🎁 奖品：{prize['name']}"

                    message += (
                        f"📌 <b>{record['settings']['title']}</b>\n"
                        f"{status_emoji} 状态：{record['status']}\n"
                        f"⏰ 参与时间：{record['join_time'].strftime('%Y-%m-%d %H:%M:%S')}\n"
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

                # 获取抽奖信息
                db = await MongoDBConnection.get_database()
                lottery = await db.lottery_settings.find_one(
                    {'lottery_id': lottery_id},
                    {
                        'title': 1,
                        'require_username': 1,
                        'required_groups': 1,
                        'keyword_group_id': 1,
                        'keyword': 1,
                        'message_group_id': 1,
                        'message_count': 1,
                        'message_check_time': 1,
                        'participant_count': 1
                    }
                )

                if not lottery:
                    await query.message.edit_text("❌ 抽奖活动不存在")
                    return
                # 检查抽奖状态
                lottery_status = await db.lotteries.find_one(
                    {'id': lottery_id},
                    {'status': 1}
                )
                if not lottery_status or lottery_status['status'] != 'active':
                    await query.message.edit_text("❌ 该抽奖活动已结束或暂停")
                    return

                # 检查是否已参与
                participant = await db.participants.find_one({
                    'lottery_id': lottery_id,
                    'user_id': user.id
                })
                if participant:
                    await query.message.edit_text("❌ 你已经参与过这个抽奖了")
                    return

                # 检查人数限制
                current_count = await db.participants.count_documents({
                    'lottery_id': lottery_id
                })
                if current_count >= lottery['participant_count']:
                    await query.message.edit_text("❌ 抽奖参与人数已满")
                    return

                # 检查用户名要求
                if lottery['require_username'] and not user.username:
                    await query.message.reply_text("❌ 参与此抽奖需要设置用户名")
                    return

                # 检查群组要求
                if lottery['required_groups']:
                    for group_id in lottery['required_groups']:
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
                # 检查关键词要求
                if lottery.get('keyword_group_id') and lottery.get('keyword'):
                    if not await check_keyword_message(
                        context.bot, 
                        user.id, 
                        lottery['keyword_group_id'], 
                        lottery['keyword']
                    ):
                        chat = await context.bot.get_chat(lottery['keyword_group_id'])
                        await query.message.reply_text(
                            f"❌ 请先在群组 {chat.title} 中发送关键词：{lottery['keyword']}"
                        )
                        return
                        
                # 检查发言要求
                if (lottery.get('message_group_id') and lottery.get('message_count') and lottery.get('message_check_time')):
                    if not await check_user_messages(
                        context.bot,
                        user.id,
                        lottery['message_group_id'],
                        lottery['message_count'],
                        lottery['message_check_time'],
                        lottery_id,
                        update
                    ):
                        chat = await context.bot.get_chat(lottery['message_group_id'])
                        await query.message.reply_text(
                            f"❌ 需要在群组 {chat.title} 中最近 {lottery['message_check_time']} 小时内发言 {lottery['message_count']} 条\n"
                            "💡 提示：只统计文本消息"
                        )
                        return
                # 添加参与记录
                now = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
                try:
                    await db.participants.insert_one({
                        'lottery_id': lottery_id,
                        'user_id': Int64(user.id),
                        'nickname': user.first_name,
                        'username': user.username,
                        'status': 'active',
                        'join_time': now
                    })
                    chat_type = query.message.chat.type
                    success_message = f"🎉 恭喜 {user.first_name} 成功参与抽奖《{lottery['title']}》！"
                    if chat_type in ['group', 'supergroup']:
                        # 添加聊天消息确认
                        await context.bot.send_message(
                            chat_id=query.message.chat_id,
                            text=success_message
                        )
                    else:
                        await context.bot.send_message(
                            chat_id=query.message.chat_id,
                            text=success_message
                        )
                        # 刷新抽奖列表
                        await refresh_lottery_list(update, context)
                        await query.message.delete()  # 删除临时提示消息
                except Exception as e:
                    logger.error(f"保存参与记录时出错: {e}", exc_info=True)
                    await query.message.reply_text("❌ 参与失败，请稍后重试")
                    return
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
                db = await MongoDBConnection.get_database()
                lottery = await db.lottery_settings.find_one(
                    {'lottery_id': lottery_id},
                    {
                        'title': 1,
                        'description': 1,
                        'media_type': 1,
                        'media_url': 1,
                        'draw_method': 1,
                        'participant_count': 1,
                        'draw_time': 1,
                        'required_groups': 1,
                        'keyword_group_id': 1,
                        'keyword': 1,
                        'message_group_id': 1,
                        'message_count': 1,
                        'message_check_time': 1,
                        'require_username': 1
                    }
                )
                    
                if  lottery:
                    await query.message.reply_text("❌ 找不到抽奖信息")
                    return

                # 获取奖品信息
                prizes = await db.prizes.find(
                    {'lottery_id': lottery_id},
                    {'name': 1, 'total_count': 1}
                ).to_list(None)
                # 构建抽奖消息
                prize_text = "\n".join([f"🎁 {p['name']} x {p['total_count']}" for p in prizes])
                requirements = []
                if lottery['require_username']:
                    requirements.append("❗️ 需要设置用户名")
                if lottery.get('keyword') and lottery.get('keyword_group_id'):
                    try:
                        chat = await context.bot.get_chat(lottery['keyword_group_id'])
                        chat_link = f"<a href='https://t.me/{chat.username}'>{chat.title}</a>" if chat.username else chat.title
                        requirements.append(f"❗️ 在群组{chat_link}中发送关键词：{lottery['keyword']}")
                    except Exception as e:
                        logger.error(f"获取关键词群组{lottery['keyword_group_id']}信息失败: {e}")

                if lottery.get('required_groups'):
                    for gid in lottery['required_groups']:
                        try:
                            chat = await context.bot.get_chat(gid)
                            chat_link = f"<a href='https://t.me/{chat.username}'>{chat.title}</a>" if chat.username else chat.title
                            requirements.append(f"❗️ 需要加入：{chat_link}")
                        except Exception as e:
                            logger.error(f"获取群组 {gid} 信息失败: {e}")
                if lottery.get('message_group_id'):
                    try:
                        chat = await context.bot.get_chat(lottery['message_group_id'])
                        chat_link = f"<a href='https://t.me/{chat.username}'>{chat.title}</a>" if chat.username else chat.title
                        requirements.append(f"❗️ {lottery['message_check_time']}小时内在群组{chat_link}中发送消息：{lottery['message_count']}条")
                    except Exception as e:
                        logger.error(f"获取消息群组 {lottery['message_group_id']} 信息失败: {e}")
                requirements_text = "\n".join(requirements) if requirements else ""
                # 处理开奖时间显示
                if lottery['draw_method'] == 'draw_when_full':
                    draw_info = f"👥 满{lottery['participant_count']}人自动开奖"
                else:
                    draw_time = lottery['draw_time'].strftime('%Y-%m-%d %H:%M:%S')
                    draw_info = f"⏰ {draw_time} 准时开奖"
                message = (
                    f"养生品茶🍵： https://t.me/yangshyyds\n\n"
                    f"🎉 抽奖活动\n\n"
                    f"📢 抽奖标题： {lottery['title']}\n\n"
                    f"📝 抽奖描述： \n{lottery['description']}\n\n"
                    f"🎁 奖品清单：\n{prize_text}\n\n"
                    f"📋 参与要求：\n{requirements_text}\n\n"
                    f"⏳ 开奖方式：\n{draw_info}\n\n"
                    f"🔔 开奖后会在机器人处通知获奖信息\n"
                    f"🤖 @{YOUR_BOT}"
                )
                    # 添加媒体消息（如果有）
                if lottery.get('media_url'):
                    try:
                        media_message = await handle_media(lottery['media_url'])
                    except Exception as e:
                        logger.error(f"处理媒体文件失败: {e}")
                        media_message = None
                else:
                    media_message = None
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
                sent_message = None
                if media_message:
                    # 发送带媒体的消息
                    if isinstance(media_message, bytes):
                        if lottery['media_type'] == 'image':
                            sent_message = await context.bot.send_photo(
                                chat_id=group_id,
                                photo=media_message,
                                caption=message,
                                reply_markup=reply_markup,
                                parse_mode='HTML'
                            )
                        elif lottery['media_type'] == 'video':
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
                    if group_id != "-1001526013692" and group_id != "-1001638087196":
                        if media_message:
                            # 发送带媒体的消息
                            if isinstance(media_message, bytes):
                                if lottery['media_type'] == 'image':
                                    await context.bot.send_photo(
                                        chat_id="-1001526013692",
                                        photo=media_message,
                                        caption=message,
                                        reply_markup=reply_markup,
                                        parse_mode='HTML'
                                    )
                                elif lottery['media_type'] == 'video':
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
        db = await MongoDBConnection.get_database()
        pipeline = [
            {
                '$match': {'status': 'active'}
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
            },
            {
                '$lookup': {
                    'from': 'participants',
                    'localField': 'lottery_id',
                    'foreignField': 'id',
                    'pipeline': [{'$count': 'count'}],
                    'as': 'participant_count'
                }
            },
            {
                '$sort': {'created_at': -1}
            },
            {
                '$limit': 10
            }
        ]
        active_lotteries = await db.lotteries.aggregate(pipeline).to_list(None)

        message = "🎲 <b>当前进行中的抽奖活动</b>\n\n"
        keyboard = []

        if not active_lotteries:
            message += "😔 目前没有正在进行的抽奖活动\n"
        else:
            for lottery in active_lotteries:
                current_count = lottery['participant_count'][0]['count'] if lottery['participant_count'] else 0
                settings = lottery['settings']
                    
                # 处理开奖方式显示
                if settings['draw_method'] == 'draw_when_full':
                    draw_info = f"👥 {current_count}/{settings['participant_count']}人"
                else:
                    draw_time = settings['draw_time'].strftime('%Y-%m-%d %H:%M:%S')
                    draw_info = f"⏰ {draw_time}"

                message += (
                    f"📌 <b>{settings['title']}</b>\n"
                    f"📊 {draw_info}\n\n"
                )

                # 添加参与按钮
                keyboard.append([
                    InlineKeyboardButton(
                        f"参与 {settings['title']}", 
                        callback_data=f'join_{lottery["lottery_id"]}'  # Updated to use lottery["lottery_id"]
                    )
                ])

            # 添加返回按钮
            keyboard.append([
                InlineKeyboardButton("🔙 返回", callback_data='back_to_main')
            ])

            try:
                await query.message.edit_text(
                    message,
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode='HTML'
                )
            except BadRequest as e:
                if "Message is not modified" in str(e):
                    # 消息内容未改变，这是正常的，可以忽略
                    await query.answer("列表已是最新")
                else:
                    # 其他错误需要处理
                    raise

    except Exception as e:
        logger.error(f"刷新抽奖列表时出错: {e}", exc_info=True)
        # 只在非"Message is not modified"错误时显示错误消息
        if not isinstance(e, BadRequest) or "Message is not modified" not in str(e):
            await query.message.reply_text("❌ 刷新列表失败，请稍后重试")

