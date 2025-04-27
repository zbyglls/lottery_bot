import psycopg2
from psycopg2 import pool
from utils import mark_initialized, logger
from config import DB_CONFIG

class DatabaseConnection:
    """PostgreSQL 数据库连接池管理器"""
    _pool = None

    @classmethod
    def init_pool(cls):
        """初始化连接池"""
        if not cls._pool:
            try:
                cls._pool = pool.SimpleConnectionPool(
                    minconn=1,
                    maxconn=10,
                    **DB_CONFIG
                )
                logger.info("数据库连接池初始化成功")
            except Exception as e:
                logger.error(f"数据库连接池初始化失败: {e}", exc_info=True)
                raise
    
    def __init__(self):
        """初始化数据库连接"""
        self.conn = None
        self.cursor = None

    def __enter__(self):
        """进入上下文时获取连接"""
        if not self._pool:
            self.init_pool()
        try:
            self.conn = self._pool.getconn()
            self.cursor = self.conn.cursor()
            return self.cursor
        except Exception as e:
            logger.error(f"数据库连接失败: {e}", exc_info=True)
            raise

    def __exit__(self, exc_type, exc_val, exc_tb):
        """退出上下文时释放连接"""
        try:
            if exc_type is None:
                self.conn.commit()
            else:
                self.conn.rollback()
        finally:
            if self.cursor:
                self.cursor.close()
            if self.conn:
                self._pool.putconn(self.conn)

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
        # 抽奖设置表 - 使用 PostgreSQL 特性
        c.execute('''CREATE TABLE IF NOT EXISTS lottery_settings
                     (id SERIAL PRIMARY KEY,
                     lottery_id INTEGER REFERENCES lotteries(id) ON DELETE CASCADE,
                     title TEXT NOT NULL,
                     media_type TEXT,
                     media_url TEXT,
                     description TEXT NOT NULL,
                     join_method TEXT NOT NULL,
                     keyword_group_id TEXT,
                     keyword TEXT,
                     require_username BOOLEAN DEFAULT FALSE,
                     required_groups TEXT,
                     draw_method TEXT NOT NULL,
                     participant_count INTEGER DEFAULT 1,
                     draw_time TIMESTAMP)''')
        # 奖品表
        c.execute('''CREATE TABLE IF NOT EXISTS prizes
                     (id SERIAL PRIMARY KEY,
                     lottery_id INTEGER REFERENCES lotteries(id) ON DELETE CASCADE,
                     name TEXT NOT NULL,          
                     total_count INTEGER NOT NULL)''')
        # 创建中奖记录表
        c.execute('''CREATE TABLE IF NOT EXISTS prize_winners
                     (id SERIAL PRIMARY KEY,
                     prize_id INTEGER REFERENCES prizes(id)  ON DELETE CASCADE,
                     participant_id INTEGER REFERENCES participants(id) ON DELETE CASCADE,
                     lottery_id INTEGER REFERENCES lotteries(id) ON DELETE CASCADE,
                     win_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                     status TEXT DEFAULT 'pending',  -- pending, claimed, expired)''')
        
        # 参与者表
        c.execute('''CREATE TABLE IF NOT EXISTS participants
                     (id SERIAL PRIMARY KEY,
                     lottery_id INTEGER REFERENCES lotteries(id) ON DELETE CASCADE,
                     nickname TEXT,
                     user_id TEXT,
                     username TEXT,
                     status TEXT,
                     join_time DATETIME)''')
        
        # 创建触发器 - PostgreSQL 语法
        c.execute('''CREATE OR REPLACE FUNCTION update_updated_at()
                    RETURNS TRIGGER AS $$
                    BEGIN
                        NEW.updated_at = CURRENT_TIMESTAMP;
                        RETURN NEW;
                    END;
                    $$ LANGUAGE plpgsql;''')

        c.execute('''DROP TRIGGER IF EXISTS update_lottery_timestamp ON lotteries;''')
        c.execute('''CREATE TRIGGER update_lottery_timestamp
                    BEFORE UPDATE ON lotteries
                    FOR EACH ROW
                    EXECUTE FUNCTION update_updated_at();''')
        # 创建索引
        c.execute('CREATE INDEX IF NOT EXISTS idx_lotteries_creator ON lotteries(creator_id);')
        c.execute('CREATE INDEX IF NOT EXISTS idx_lotteries_status ON lotteries(status);')
        c.execute('CREATE INDEX IF NOT EXISTS idx_participants_lottery ON participants(lottery_id);')
        c.execute('CREATE INDEX IF NOT EXISTS idx_participants_user ON participants(user_id);')
        c.execute('CREATE INDEX IF NOT EXISTS idx_prize_winners_lottery ON prize_winners(lottery_id);')

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
                
        except Exception as e:
            logger.error(f"检查数据库时出错: {e}", exc_info=True)
            raise