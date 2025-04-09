from flask import Flask, render_template, request, jsonify
import os
import sqlite3
from datetime import datetime
import logging

app = Flask(__name__)

# 配置日志记录
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 数据库连接上下文管理器
class DatabaseConnection:
    def __init__(self, db_name):
        self.db_name = db_name

    def __enter__(self):
        self.conn = sqlite3.connect(self.db_name)
        return self.conn.cursor()

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            self.conn.commit()
        else:
            self.conn.rollback()
        self.conn.close()

# 初始化数据库
def init_db():
    with DatabaseConnection('lottery.db') as c:
        c.execute('''CREATE TABLE IF NOT EXISTS lotteries
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                     creator_info TEXT,
                     title TEXT,
                     media_type TEXT,
                     description TEXT,
                     join_method TEXT,
                     join_condition TEXT,
                     groups TEXT,
                     draw_method TEXT,
                     participant_count INTEGER,
                     keyword_group TEXT,  
                     lottery_keyword TEXT,  
                     created_at DATETIME)''')
        c.execute('''CREATE TABLE IF NOT EXISTS prizes
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                     lottery_id INTEGER,
                     name TEXT,
                     total_count INTEGER,
                     remaining_count INTEGER,
                     FOREIGN KEY (lottery_id) REFERENCES lotteries(id))''')
        c.execute('''CREATE TABLE IF NOT EXISTS participants
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                     lottery_id INTEGER,
                     nickname TEXT,
                     user_id TEXT,
                     username TEXT,
                     status TEXT,
                     join_time DATETIME,
                     FOREIGN KEY (lottery_id) REFERENCES lotteries(id))''')
        c.execute('''CREATE TABLE IF NOT EXISTS notification_settings
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                     lottery_id INTEGER,
                     winner_private_notice TEXT,
                     creator_private_notice TEXT,
                     group_notice TEXT,
                     FOREIGN KEY (lottery_id) REFERENCES lotteries(id))''')

@app.route('/')
def index():
    creator_info = "创建人信息示例"
    return render_template('index.html', creator_info=creator_info)

# 模拟关键词群组数据
keyword_groups = [
    {'id': 1, 'name': 'Group 1'},
    {'id': 2, 'name': 'Group 2'}
    # 可以添加更多群组数据
]

# 获取关键词群组列表
@app.route('/get_keyword_groups', methods=['GET'])
def get_keyword_groups():
    return jsonify({'groups': keyword_groups})

@app.route('/create_lottery', methods=['POST'])
def create_lottery():
    try:
        data = request.form
        creator_info = data.get('creator_info')
        title = data.get('title')
        media_type = data.get('media_type')
        description = data.get('description')
        join_method = data.get('join_method')
        join_condition = data.get('join_condition')
        groups = data.get('groups')
        draw_method = data.get('draw_method')
        participant_count = int(data.get('participant_count'))
        created_at = datetime.now()

        # 插入抽奖活动信息
        with DatabaseConnection('lottery.db') as c:
            c.execute("INSERT INTO lotteries (creator_info, title, media_type, description, join_method, join_condition, groups, draw_method, participant_count, created_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
                      (creator_info, title, media_type, description, join_method, join_condition, groups, draw_method, participant_count, created_at))
            lottery_id = c.lastrowid

        # 处理奖品设置信息
        prize_names = data.getlist('prize_name')
        prize_counts = data.getlist('prize_count')
        for name, count in zip(prize_names, prize_counts):
            if name and count:
                total_count = int(count)
                remaining_count = total_count
                with DatabaseConnection('lottery.db') as c:
                    c.execute("INSERT INTO prizes (lottery_id, name, total_count, remaining_count) VALUES (?,?,?,?)",
                              (lottery_id, name, total_count, remaining_count))

        # 处理通知设置信息
        winner_private_notice = data.get('winner_private_notice')
        creator_private_notice = data.get('creator_private_notice')
        group_notice = data.get('group_notice')
        with DatabaseConnection('lottery.db') as c:
            c.execute("INSERT INTO notification_settings (lottery_id, winner_private_notice, creator_private_notice, group_notice) VALUES (?,?,?,?)",
                      (lottery_id, winner_private_notice, creator_private_notice, group_notice))

        return jsonify({'status': 'success', 'lottery_id': lottery_id})
    except Exception as e:
        logger.error(f"创建抽奖活动时出错: {e}")
        return jsonify({'status': 'error', 'message': '创建抽奖活动时出错，请稍后重试'})


@app.route('/add_prize', methods=['POST'])
def add_prize():
    try:
        data = request.form
        lottery_id = int(data.get('lottery_id'))
        name = data.get('name')
        total_count = int(data.get('total_count'))
        remaining_count = total_count

        with DatabaseConnection('lottery.db') as c:
            c.execute("INSERT INTO prizes (lottery_id, name, total_count, remaining_count) VALUES (?,?,?,?)",
                      (lottery_id, name, total_count, remaining_count))
        return jsonify({'status': 'success'})
    except Exception as e:
        logger.error(f"添加奖品时出错: {e}")
        return jsonify({'status': 'error', 'message': '添加奖品时出错，请稍后重试'})

@app.route('/get_participants', methods=['GET'])
def get_participants():
    try:
        lottery_id = request.args.get('lottery_id')
        status = request.args.get('status')
        keyword = request.args.get('keyword')

        query = "SELECT nickname, user_id, username, status, join_time FROM participants WHERE lottery_id =? "
        params = [lottery_id]
        if status and status != '全部用户':
            query += "AND status =? "
            params.append(status)
        if keyword:
            query += "AND (nickname LIKE? OR user_id LIKE?)"
            params.extend([f'%{keyword}%', f'%{keyword}%'])

        with DatabaseConnection('lottery.db') as c:
            c.execute(query, params)
            participants = c.fetchall()

        result = []
        for participant in participants:
            result.append({
                'nickname': participant[0],
                'user_id': participant[1],
                'username': participant[2],
                'status': participant[3],
                'join_time': participant[4]
            })
        return jsonify({'participants': result})
    except Exception as e:
        logger.error(f"获取参与者信息时出错: {e}")
        return jsonify({'status': 'error', 'message': '获取参与者信息时出错，请稍后重试'})

@app.route('/get_prizes', methods=['GET'])
def get_prizes():
    try:
        lottery_id = request.args.get('lottery_id')
        with DatabaseConnection('lottery.db') as c:
            c.execute("SELECT id, name, total_count, remaining_count FROM prizes WHERE lottery_id =?", (lottery_id,))
            prizes = c.fetchall()

        result = []
        for prize in prizes:
            result.append({
                'id': prize[0],
                'name': prize[1],
                'total_count': prize[2],
                'remaining_count': prize[3]
            })
        return jsonify({'prizes': result})
    except Exception as e:
        logger.error(f"获取奖品信息时出错: {e}")
        return jsonify({'status': 'error', 'message': '获取奖品信息时出错，请稍后重试'})

@app.route('/delete_prize', methods=['POST'])
def delete_prize():
    try:
        prize_id = int(request.form.get('prize_id'))
        with DatabaseConnection('lottery.db') as c:
            c.execute("DELETE FROM prizes WHERE id =?", (prize_id,))
        return jsonify({'status': 'success'})
    except Exception as e:
        logger.error(f"删除奖品时出错: {e}")
        return jsonify({'status': 'error', 'message': '删除奖品时出错，请稍后重试'})

@app.route('/save_notification_settings', methods=['POST'])
def save_notification_settings():
    try:
        data = request.form
        lottery_id = int(data.get('lottery_id'))
        winner_private_notice = data.get('winner_private_notice')
        creator_private_notice = data.get('creator_private_notice')
        group_notice = data.get('group_notice')

        with DatabaseConnection('lottery.db') as c:
            c.execute("INSERT INTO notification_settings (lottery_id, winner_private_notice, creator_private_notice, group_notice) VALUES (?,?,?,?)",
                      (lottery_id, winner_private_notice, creator_private_notice, group_notice))
        return jsonify({'status': 'success'})
    except Exception as e:
        logger.error(f"保存通知设置时出错: {e}")
        return jsonify({'status': 'error', 'message': '保存通知设置时出错，请稍后重试'})

@app.route('/edit_prize', methods=['POST'])
def edit_prize():
    try:
        data = request.form
        prize_id = int(data.get('prize_id'))
        name = data.get('name')
        total_count = int(data.get('total_count'))

        with DatabaseConnection('lottery.db') as c:
            c.execute("UPDATE prizes SET name =?, total_count =? WHERE id =?", (name, total_count, prize_id))
        return jsonify({'status': 'success'})
    except Exception as e:
        logger.error(f"编辑奖品时出错: {e}")
        return jsonify({'status': 'error', 'message': '编辑奖品时出错，请稍后重试'})

# 模拟抽奖数据存储
lotteries = {
    1: {'status': 'active'}
}

@app.route('/cancel_lottery', methods=['GET'])
def cancel_lottery():
    try:
        lottery_id = int(request.args.get('lottery_id'))
        if lottery_id in lotteries:
            # 更新抽奖状态为取消
            lotteries[lottery_id]['status'] = 'cancelled'
            return jsonify({'status': 'success'})
        else:
            return jsonify({'status': 'error', 'message': '未找到该抽奖活动'})
    except Exception as e:
        logger.error(f"取消抽奖时出错: {e}")
        return jsonify({'status': 'error', 'message': '取消抽奖时出错，请稍后重试'})

if __name__ == '__main__':
    init_db()
    app.run(debug=True)