from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates


def create_app():
    app = FastAPI(title="Lottery Bot")
    
    # 挂载静态文件
    app.mount("/static", StaticFiles(directory="app/static"), name="static")
    
    # 配置模板
    templates = Jinja2Templates(directory="app/templates")
    
    # 注册路由
    from .routes import router
    app.include_router(router)
    
    # 将 templates 对象添加到 app.state
    app.state.templates = templates
    
    return app