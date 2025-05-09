from datetime import datetime, timezone
from app.database import MongoDBConnection
from bot.callbacks import verify_follow
from utils import logger
from bson import Int64
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler, MessageHandler, filters
from bot.conversation import SELECTING_ACTION
from config import YOUR_DOMAIN
from bot.verification import check_channel_subscription, check_lottery_creation
from bot.handlers import handle_keyword_participate, handle_media_message, handle_message_count_participate


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理 /start 命令"""
    user = update.effective_user
    welcome_message = (
        f"👋 你好 {user.first_name}!\n\n"
        "欢迎使用抽奖机器人。你可以：\n"
        "1. 查看当前正在进行的抽奖\n"
        "2. 参与抽奖活动\n"
        "3. 查看我的抽奖记录"
    )
    
    keyboard = [
        [InlineKeyboardButton("查看抽奖活动", callback_data='view_lotteries')],
        [InlineKeyboardButton("我的抽奖记录", callback_data='my_records')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(welcome_message, reply_markup=reply_markup)
    return SELECTING_ACTION

async def create_lottery(user, context, chat_id):
    """创建抽奖的核心逻辑"""
    try:
        now = datetime.now(timezone.utc)
        lottery_id = str(now.timestamp()).replace('.', '')
        
        # 创建初始抽奖记录
        db = await MongoDBConnection.get_database()
        lottery_doc = {
            'id': lottery_id,
            'creator_id': Int64(user.id),
            'creator_name': user.first_name,
            'status': 'draft',
            'created_at': now,
            'updated_at': now
        }
        await db.lotteries.insert_one(lottery_doc)
        logger.info(f"成功插入抽奖记录，ID 为 {lottery_id}")
            
        # 构建创建链接
        create_url = f"{YOUR_DOMAIN}/?lottery_id={lottery_id}&user_id={user.id}"
        
        # 构建按钮
        keyboard = [
            [InlineKeyboardButton("👉 点击创建抽奖", url=create_url)],
            [InlineKeyboardButton("❌ 取消创建", callback_data=f'cancel_lottery_{lottery_id}')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await context.bot.send_message(
            chat_id=chat_id,
            text=(
                f"👋 {user.first_name}，开始创建新的抽奖活动！\n\n"
                "✨ 请点击下方按钮进入创建页面\n"
                "⚠️ 如果不想创建，请点击取消按钮\n\n"
                "🔔 注意：创建页面链接有效期为60分钟"
            ),
            reply_markup=reply_markup
        )
        
        # 设置抽奖创建超时
        if context.job_queue:
            context.job_queue.run_once(
                check_lottery_creation,
                3600,  # 60分钟后检查
                data={'lottery_id': lottery_id, 'user_id': user.id}
            )
            logger.info(f"已设置抽奖 {lottery_id} 的创建超时检查")
    except Exception as e:
        logger.error(f"创建抽奖时出错: {e}", exc_info=True)
        await context.bot.send_message(
            chat_id=chat_id,
            text="创建抽奖时发生错误，请稍后重试。"
        )

async def new_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理 /new 命令 - 新建普通抽奖"""
    try:
        user = update.effective_user
        logger.info(f"收到 /new 命令，来自用户: {user.id}")
        
        # 检查用户是否关注了频道
        is_subscribed = await check_channel_subscription(context.bot, user.id)
        if not is_subscribed:
            keyboard = [
                [InlineKeyboardButton("👉 加入群组", url='https://t.me/yangshyyds')],
                [InlineKeyboardButton("✅ 已加入，验证", callback_data='verify_follow')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                "⚠️ 创建抽奖需要先加入 养生品茶🍵 群组\n\n"
                "1️⃣ 点击下方按钮加入群组\n"
                "2️⃣ 加入后点击验证按钮\n\n"
                "🔔 加入后即可创建抽奖活动",
                reply_markup=reply_markup
            )
            return

        # 用户已关注频道，继续创建抽奖
        from bot.callbacks import verify_follow
        await create_lottery(user, context, update.message.chat_id)
        
    except Exception as e:
        logger.error(f"处理 /new 命令时出错: {e}", exc_info=True)
        if update.message:
            await update.message.reply_text("创建抽奖时发生错误，请稍后重试。")


async def mylottery_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理 /mylottery 命令 - 查看我创建的抽奖"""
    try:
        user = update.effective_user
        # 从数据库获取用户创建的抽奖列表
        db = await MongoDBConnection.get_database() 
        pipeline = [
            {
                '$match': {
                    'creator_id': user.id
                }
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
                '$sort': {'created_at': -1}
            },
            {
                '$limit': 5
            }
        ]
        lotteries = await db.lotteries.aggregate(pipeline).to_list(length=None)

        if not lotteries:
            await update.message.reply_text("你还没有创建过抽奖活动。")
            return

        # 构建抽奖列表消息
        message = "📋 你创建的最近抽奖活动：\n\n"
        for lottery in lotteries:
            message += f"🎲 {lottery['settings']['title']}\n"
            message += f"状态: {lottery['status']}\n"
            message += f"创建时间: {lottery['created_at']}\n"
            message += f"管理链接: {YOUR_DOMAIN}/?lottery_id={lottery['id']}&user_id={user.id}\n\n"

        await update.message.reply_text(message)
    except Exception as e:
        logger.error(f"处理 /mylottery 命令时出错: {e}", exc_info=True)
        await update.message.reply_text("获取抽奖列表时发生错误，请稍后重试。")

async def get_media_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理 /media_id 命令 - 获取媒体文件的 ID"""
    try:
        reply = update.message.reply_to_message
        if not reply:
            await update.message.reply_text(
                "❌ 请回复一条包含媒体文件的消息来获取媒体 ID。\n"
                "支持的媒体类型：\n"
                "• 图片\n"
                "• 视频\n"
                "• 文档\n"
                "• 音频\n"
                "• 贴纸",
                reply_to_message_id=update.message.message_id  # 使用这个替代 quote=True
            )
            return

        media_info = []
        
        # 检查各种媒体类型
        if reply.photo:
            # 获取最大尺寸的图片
            photo = reply.photo[-1]
            media_info.append(f"📸 图片 ID: {photo.file_id}")
            media_info.append(f"📏 尺寸: {photo.width}x{photo.height}")
            
        elif reply.video:
            media_info.append(f"🎥 视频 ID: {reply.video.file_id}")
            media_info.append(f"📏 尺寸: {reply.video.width}x{reply.video.height}")
            media_info.append(f"⏱️ 时长: {reply.video.duration}秒")
            
        elif reply.document:
            media_info.append(f"📄 文档 ID: {reply.document.file_id}")
            if reply.document.file_name:
                media_info.append(f"📋 文件名: {reply.document.file_name}")
            if reply.document.file_size:
                size_mb = reply.document.file_size / 1024 / 1024
                media_info.append(f"📦 大小: {size_mb:.2f}MB")
                
        elif reply.audio:
            media_info.append(f"🎵 音频 ID: {reply.audio.file_id}")
            media_info.append(f"⏱️ 时长: {reply.audio.duration}秒")
            if reply.audio.title:
                media_info.append(f"📌 标题: {reply.audio.title}")
                
        elif reply.sticker:
            media_info.append(f"😀 贴纸 ID: {reply.sticker.file_id}")
            media_info.append(f"📏 尺寸: {reply.sticker.width}x{reply.sticker.height}")
            
        else:
            await update.message.reply_text(
                "❌ 未找到支持的媒体文件\n"
                "请确保回复的消息包含以下类型之一：\n"
                "• 图片\n"
                "• 视频\n"
                "• 文档\n"
                "• 音频\n"
                "• 贴纸"
            )
            return

        # 发送媒体信息
        await update.message.reply_text(
            "✅ 成功获取媒体信息：\n\n" + "\n".join(media_info),
            reply_to_message_id=update.message.message_id  # 使用这个替代 quote=True
        )

    except Exception as e:
        logger.error(f"处理 /media_id 命令时出错: {e}", exc_info=True)
        await update.message.reply_text(
            "❌ 获取媒体 ID 时发生错误，请稍后重试。",
            reply_to_message_id=update.message.message_id  # 使用这个替代 quote=True
        )



def register_commands(app):
    """注册所有命令处理器"""
    keyword_filter = (filters.TEXT & ~filters.COMMAND & filters.ChatType.GROUPS)
    message_count_filter = (filters.TEXT & ~filters.COMMAND & filters.ChatType.GROUPS)
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("new", new_command))
    app.add_handler(CommandHandler("mylottery", mylottery_command))
    app.add_handler(CommandHandler("media_id", get_media_id))
    app.add_handler(CallbackQueryHandler(verify_follow, pattern='^verify_follow$'))
    app.add_handler(MessageHandler(keyword_filter, handle_keyword_participate), group=1)
    app.add_handler(MessageHandler(message_count_filter, handle_message_count_participate), group=2)
    app.add_handler(MessageHandler(filters.PHOTO | filters.VIDEO | filters.Document.ALL | filters.AUDIO | filters.Sticker.ALL, handle_media_message), group=3)


