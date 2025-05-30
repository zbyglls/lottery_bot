#本地测试
1.创建.env文件，添加环境变量
  TELEGRAM_BOT_TOKEN=your_token
  YOUR_BOT=your_bot_id
  YOUR_DOMAIN=http://127.0.0.1:8000
  SERVER_URL=http://127.0.0.1:8000
  MONGO_DB=数据库名称
  MONGO_URI=数据库地址
2.本地启动命令 
  python main.py
  
#服务器部署
1.创建环境变量
    TELEGRAM_BOT_TOKEN=your_token
    YOUR_BOT=your_bot_id
    YOUR_DOMAIN=your_domain
    SERVER_URL=your_domain
    MONGO_DB=数据库名称
    MONGO_URI=数据库地址
2.部署启动命令
  uvicorn main:app --host 0.0.0.0 --port $PORT
