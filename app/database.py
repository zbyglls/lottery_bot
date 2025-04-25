import sqlite3
from utils import mark_initialized, logger
from config import DB_PATH

class DatabaseConnection:
    """数据库连接上下文管理器"""
    
    def __init__(self, db_path=None):
        """初始化数据库连接"""
        self.db_path = db_path or DB_PATH
        self.conn = None
        self.cursor = None

    def __enter__(self):
        """进入上下文时建立连接"""
        try:
            self.conn = sqlite3.connect(self.db_path)
            self.cursor = self.conn.cursor()
            return self.cursor
        except sqlite3.Error as e:
            logger.error(f"数据库连接失败: {e}", exc_info=True)
            raise

    def __exit__(self, exc_type, exc_val, exc_tb):
        """退出上下文时提交或回滚并关闭连接"""
        try:
            if exc_type is None:
                self.conn.commit()
            else:
                self.conn.rollback()
        finally:
            if self.cursor:
                self.cursor.close()
            if self.conn:
                self.conn.close()

def init_db():
    """初始化数据库表结构"""
    if mark_initialized('database'):
        return
        
    with DatabaseConnection() as c:
        
        # 抽奖表
        c.execute('''CREATE TABLE IF NOT EXISTS lotteries
                     (id INTEGER PRIMARY KEY ,
                     creator_id INTEGER NOT NULL,
                     creator_name TEXT NOT NULL,
                     status TEXT NOT NULL,  -- draft, creating, active, completed, cancelled
                     type TEXT NOT NULL,  -- 'normal' 或 'invite'
                     created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                     updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
        # 抽奖设置表
        c.execute('''CREATE TABLE IF NOT EXISTS lottery_settings
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                     lottery_id INTEGER,
                     title TEXT NOT NULL,
                     media_type TEXT DEFAULT NULL,     -- 图片或视频类型，'image' 或 'video'
                     media_url TEXT,             -- 图片或视频链接字段
                     description TEXT NOT NULL,
                     join_method TEXT NOT NULL,  -- 'private_chat' 或 'group_keyword'
                     keyword_group_id TEXT,
                     keyword TEXT,
                     require_username BOOLEAN DEFAULT 0,
                     required_groups TEXT,        -- 需要加入的群组/频道ID，多个用逗号分隔
                     draw_method TEXT NOT NULL,  -- 'draw_when_full' 或 'draw_at_time'
                     participant_count INTEGER DEFAULT 1,
                     draw_time TIMESTAMP,
                     FOREIGN KEY (lottery_id) REFERENCES lotteries(id) ON DELETE CASCADE
                     ) ''')
        # 奖品表
        c.execute('''CREATE TABLE IF NOT EXISTS prizes
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                     lottery_id INTEGER NOT NULL,
                     name TEXT NOT NULL,          -- 奖品名称
                     total_count INTEGER NOT NULL, -- 奖品总数量
                     FOREIGN KEY (lottery_id) REFERENCES lotteries(id) ON DELETE CASCADE
                     )''')
        # 创建中奖记录表
        c.execute('''CREATE TABLE IF NOT EXISTS prize_winners
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                     prize_id INTEGER NOT NULL,
                     participant_id INTEGER NOT NULL,
                     lottery_id INTEGER NOT NULL,
                     win_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                     status TEXT DEFAULT 'pending',  -- pending, claimed, expired
                     FOREIGN KEY (prize_id) REFERENCES prizes(id)  ON DELETE CASCADE,
                     FOREIGN KEY (participant_id) REFERENCES participants(id) ON DELETE CASCADE,
                     FOREIGN KEY (lottery_id) REFERENCES lotteries(id) ON DELETE CASCADE
                     )''')
        
        # 参与者表
        c.execute('''CREATE TABLE IF NOT EXISTS participants
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                     lottery_id INTEGER,
                     nickname TEXT,
                     user_id TEXT,
                     username TEXT,
                     status TEXT,
                     join_time DATETIME,
                     FOREIGN KEY (lottery_id) REFERENCES lotteries(id) ON DELETE CASCADE
                     )''')
        # 创建索引
        c.execute('CREATE INDEX IF NOT EXISTS idx_lotteries_creator ON lotteries(creator_id)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_lotteries_status ON lotteries(status)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_participants_lottery ON participants(lottery_id)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_participants_user ON participants(user_id)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_prize_winners_lottery ON prize_winners(lottery_id)')

        #创建触发器自动更新时间
        c.execute('''CREATE TRIGGER IF NOT EXISTS update_lottery_timestamp
                     AFTER UPDATE ON lotteries
                     BEGIN
                        UPDATE lotteries SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
                     END;''')

        logger.info("数据库表结构初始化完成")

def check_db():
    """检查数据库表是否存在并验证结构完整性"""
    with DatabaseConnection() as c:
        try:
            # 检查所需的表是否都存在
            required_tables = ['lotteries', 'lottery_settings', 'prizes', 'prize_winners', 'participants']
            c.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name IN ({})
            """.format(','.join('?' * len(required_tables))), required_tables)
            
            existing_tables = set(row[0] for row in c.fetchall())
            missing_tables = set(required_tables) - existing_tables
            
            if missing_tables:
                logger.info(f"缺少以下表，开始初始化: {', '.join(missing_tables)}")
                init_db()
            else:
                logger.info("数据库表结构完整，无需初始化")
                
        except sqlite3.Error as e:
            logger.error(f"检查数据库时出错: {e}", exc_info=True)
            raise