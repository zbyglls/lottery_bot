import asyncio
from contextlib import asynccontextmanager
import json
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app.routes import router as api_router
from config import BASE_DIR, templates
from app.database import MongoDBConnection, check_db
from bot import create_bot, start_background_tasks, stop_bot, tasks, application
from utils import logger
from fastapi import FastAPI, Response


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    try:
        # 检查并初始化数据库
        await check_db()
        
        # 初始化模板
        app.state.templates = templates
        
        # 初始化机器人
        await create_bot()
        
        # 启动后台任务
        await start_background_tasks()
        
        logger.info("应用初始化完成")
        yield
        
        # 关闭时清理
        logger.info("开始清理资源...")
        for task in tasks:
            if not task.done():
                task.cancel()
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        
        await stop_bot()
        logger.info("资源清理完成")
    except Exception as e:
        logger.error(f"生命周期管理出错: {e}", exc_info=True)
        raise



# 创建FastAPI应用
app = FastAPI(lifespan=lifespan)
# 挂载静态文件
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "app" / "static")), name="static")
app.include_router(api_router)

@app.get("/health")
async def health_check():
    """健康检查接口"""
    try:
        status = {
            "database": False,
            "bot": False,
            "background_tasks": False,
            "details": []
        }

        # 检查数据库连接
        try:
            db = await MongoDBConnection.get_database()
            await db.command("ping")
            status["database"] = True
        except Exception as e:
            status["details"].append(f"数据库连接失败: {str(e)}")

        # 检查 bot 状态
        try:
            if application and application.bot:
                me = await application.bot.get_me()
                if me and me.id:
                    status["bot"] = True
            else:
                status["details"].append("Bot 未初始化")
        except Exception as e:
            status["details"].append(f"Bot 状态检查失败: {str(e)}")

        # 检查后台任务
        if not tasks:
            status["details"].append("无运行中的后台任务")
        else:
            active_count = 0
            for task in tasks:
                if not task.done():
                    active_count += 1
                elif task.exception() and not isinstance(task.exception(), asyncio.CancelledError):
                    status["details"].append(f"任务异常: {task.exception()}")

            if active_count > 0:
                status["tasks"] = True
            else:
                status["details"].append("所有后台任务已停止")

        # 确定响应状态码
        if all([status["database"], status["bot"], status["tasks"]]):
            return {
                "status": "healthy",
                "checks": status
            }
        else:
            return Response(
                content=json.dumps({
                    "status": "unhealthy",
                    "checks": status
                }, ensure_ascii=False),
                status_code=503,
                media_type="application/json"
            )

    except Exception as e:
        logger.error(f"健康检查失败: {e}", exc_info=True)
        return Response(
            content=json.dumps({
                "status": "error",
                "message": str(e)
            }, ensure_ascii=False),
            status_code=503,
            media_type="application/json"
        )
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)