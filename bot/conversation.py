

# 定义对话状态
SELECTING_ACTION, CREATING_LOTTERY = range(2)

async def start_creating(update, context):
    """Handle the /new command to start creating a lottery"""
    await update.message.reply_text("Let's create a new lottery!")
    return SELECTING_ACTION

