import os
from pathlib import Path
from fastapi.templating import Jinja2Templates
from dotenv import load_dotenv

# 获取项目根目录
BASE_DIR = Path(__file__).resolve().parent

# 配置模板目录
TEMPLATES_DIR = BASE_DIR / "app" / "templates"

# 创建模板对象
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# 加载环境变量
env_path = BASE_DIR / '.env'
load_dotenv(env_path)

# Telegram 配置
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
YOUR_BOT = os.getenv('YOUR_BOT')


# 数据库配置
DB_PATH = os.path.join(BASE_DIR, 'lottery.db')

# 媒体文件配置
MEDIA_ROOT = BASE_DIR / 'media'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'mp4'}

# Job Queue 配置
JOB_QUEUE_ENABLED = True
JOB_QUEUE_WORKERS = 4  # 工作线程数

# 域名配置
YOUR_DOMAIN = os.getenv('YOUR_DOMAIN')
SERVICE_URL = os.getenv('SERVICE_URL')
