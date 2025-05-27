import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timezone
import json
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from app.routes import router as api_router
from config import BASE_DIR, templates
from app.database import MongoDBConnection, check_db
from bot import create_bot, start_background_tasks, stop_bot, bot_state
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
        for task in bot_state.tasks:
            if not task.done():
                task.cancel()
        
        if bot_state.tasks:
            await asyncio.gather(*bot_state.tasks, return_exceptions=True)

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


@app.head("/health")
@app.get("/health")
async def health_check(request: Request):
    """健康检查接口"""
    try:
        if request.method == "HEAD":
            return Response(status_code=200)
        
        status = {
            "database": False,
            "bot": False,
            "background_tasks": False,
            "details": [],
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        # 检查数据库连接
        try:
            db = await MongoDBConnection.get_database()
            await db.command("ping")
            status["database"] = True
            status["details"].append("数据库连接正常")
        except Exception as e:
            status["details"].append(f"数据库连接失败: {str(e)}")
            logger.error(f"健康检查 - 数据库连接失败: {e}")

        # 检查 bot 状态
        try:
            if bot_state.application and bot_state.application.bot:
                me = await bot_state.application.bot.get_me()
                if me and me.id:
                    status["bot"] = True
                    status["details"].append(f"Bot 正常运行 (ID: {me.id})")
            else:
                status["details"].append("Bot 未初始化或未连接")
                logger.warning("健康检查 - Bot 未初始化")
        except Exception as e:
            status["details"].append(f"Bot 状态检查失败: {str(e)}")
            logger.error(f"健康检查 - Bot 状态检查失败: {e}")

        # 检查后台任务
        try:
            if not bot_state.tasks:
                status["details"].append("无运行中的后台任务")
                logger.warning("健康检查 - 无后台任务")
            else:
                active_tasks = []
                failed_tasks = []
                for task in bot_state.tasks:
                    if not task.done():
                        active_tasks.append(str(task.get_name()))
                    elif task.exception() and not isinstance(task.exception(), asyncio.CancelledError):
                        failed_tasks.append(f"{task.get_name()}: {task.exception()}")

                if active_tasks:
                    status["background_tasks"] = True
                    status["details"].append(f"运行中的任务: {', '.join(active_tasks)}")
                if failed_tasks:
                    status["details"].append(f"异常的任务: {', '.join(failed_tasks)}")
                    logger.error(f"健康检查 - 存在异常任务: {failed_tasks}")
        except Exception as e:
            status["details"].append(f"任务状态检查失败: {str(e)}")
            logger.error(f"健康检查 - 任务状态检查失败: {e}")

        # 确定响应状态码和消息
        is_healthy = all([status["database"], status["bot"], status["background_tasks"]])
        response_data = {
            "status": "healthy" if is_healthy else "unhealthy",
            "checks": status
        }

        return Response(
            content=json.dumps(response_data, ensure_ascii=False),
            status_code=200 if is_healthy else 503,
            media_type="application/json"
        )

    except Exception as e:
        error_response = {
            "status": "error",
            "message": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        logger.error(f"健康检查执行失败: {e}", exc_info=True)
        return Response(
            content=json.dumps(error_response, ensure_ascii=False),
            status_code=503,
            media_type="application/json"
        )
    
    
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)