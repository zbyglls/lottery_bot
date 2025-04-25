import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app.routes import router as api_router
from config import BASE_DIR, templates
from app.database import check_db
from bot import create_bot, stop_bot
from utils import logger
from bot.tasks import check_lottery_draws

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    try:
        # 检查并初始化数据库
        check_db()
        
        # 初始化模板
        app.state.templates = templates
        
        # 初始化机器人
        await create_bot()
        
        # 启动开奖监听任务
        app.state.lottery_task = asyncio.create_task(check_lottery_draws())
        
        logger.info("应用初始化完成")
        yield
        
        # 关闭时清理
        if hasattr(app.state, 'lottery_task'):
            app.state.lottery_task.cancel()
            try:
                await app.state.lottery_task
            except asyncio.CancelledError:
                pass
        
        await stop_bot()
        
    except Exception as e:
        logger.error(f"生命周期管理出错: {e}", exc_info=True)
        raise

# 创建FastAPI应用
app = FastAPI(lifespan=lifespan)
# 挂载静态文件
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "app" / "static")), name="static")
app.include_router(api_router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)