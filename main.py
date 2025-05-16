import asyncio
from contextlib import asynccontextmanager
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
        # 检查数据库连接
        db = await MongoDBConnection.get_database()
        await db.command("ping")
        
        # 检查后台任务
        if not tasks:
            return Response(
                content="No background tasks running", 
                status_code=503
            )
            
        active_tasks = 0
        for task in tasks:
            if not task.done():
                active_tasks += 1
            elif task.exception() and not isinstance(task.exception(), asyncio.CancelledError):
                return Response(
                    content=f"Background task failed: {task.exception()}", 
                    status_code=503
                )
                
        if active_tasks == 0:
            return Response(
                content="No active background tasks", 
                status_code=503
            )
                
        return Response(
            content="OK",
            status_code=200
        )
    except Exception as e:
        logger.error(f"健康检查失败: {e}", exc_info=True)
        return Response(
            content=str(e),
            status_code=503
        )
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)