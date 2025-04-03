from flask import Flask, render_template, request, jsonify
import os
import sqlite3
from datetime import datetime

app = Flask(__name__)

# 初始化数据库
def init_db():
    conn = sqlite3.connect('lottery.db')
    c = conn.cursor()
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
    conn.commit()
    conn.close()


@app.route('/')
def index():
    creator_info = "创建人信息示例"
    return render_template('index.html', creator_info=creator_info)


@app.route('/create_lottery', methods=['POST'])
def create_lottery():
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

    conn = sqlite3.connect('lottery.db')
    c = conn.cursor()
    c.execute("INSERT INTO lotteries (creator_info, title, media_type, description, join_method, join_condition, groups, draw_method, participant_count, created_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
              (creator_info, title, media_type, description, join_method, join_condition, groups, draw_method, participant_count, created_at))
    lottery_id = c.lastrowid
    conn.commit()
    conn.close()

    return jsonify({'status': 'success', 'lottery_id': lottery_id})


@app.route('/add_prize', methods=['POST'])
def add_prize():
    data = request.form
    lottery_id = int(data.get('lottery_id'))
    name = data.get('name')
    total_count = int(data.get('total_count'))
    remaining_count = total_count

    conn = sqlite3.connect('lottery.db')
    c = conn.cursor()
    c.execute("INSERT INTO prizes (lottery_id, name, total_count, remaining_count) VALUES (?,?,?,?)",
              (lottery_id, name, total_count, remaining_count))
    conn.commit()
    conn.close()

    return jsonify({'status': 'success'})


@app.route('/get_participants', methods=['GET'])
def get_participants():
    lottery_id = request.args.get('lottery_id')
    status = request.args.get('status')
    keyword = request.args.get('keyword')

    conn = sqlite3.connect('lottery.db')
    c = conn.cursor()
    query = "SELECT nickname, user_id, username, status, join_time FROM participants WHERE lottery_id =? "
    params = [lottery_id]
    if status and status != '全部用户':
        query += "AND status =? "
        params.append(status)
    if keyword:
        query += "AND (nickname LIKE? OR user_id LIKE?)"
        params.extend([f'%{keyword}%', f'%{keyword}%'])
    c.execute(query, params)
    participants = c.fetchall()
    conn.close()

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


@app.route('/get_prizes', methods=['GET'])
def get_prizes():
    lottery_id = request.args.get('lottery_id')
    conn = sqlite3.connect('lottery.db')
    c = conn.cursor()
    c.execute("SELECT id, name, total_count, remaining_count FROM prizes WHERE lottery_id =?", (lottery_id,))
    prizes = c.fetchall()
    conn.close()

    result = []
    for prize in prizes:
        result.append({
            'id': prize[0],
            'name': prize[1],
            'total_count': prize[2],
            'remaining_count': prize[3]
        })
    return jsonify({'prizes': result})


@app.route('/delete_prize', methods=['POST'])
def delete_prize():
    prize_id = int(request.form.get('prize_id'))
    conn = sqlite3.connect('lottery.db')
    c = conn.cursor()
    c.execute("DELETE FROM prizes WHERE id =?", (prize_id,))
    conn.commit()
    conn.close()
    return jsonify({'status': 'success'})


@app.route('/save_notification_settings', methods=['POST'])
def save_notification_settings():
    data = request.form
    lottery_id = int(data.get('lottery_id'))
    winner_private_notice = data.get('winner_private_notice')
    creator_private_notice = data.get('creator_private_notice')
    group_notice = data.get('group_notice')

    conn = sqlite3.connect('lottery.db')
    c = conn.cursor()
    c.execute("INSERT INTO notification_settings (lottery_id, winner_private_notice, creator_private_notice, group_notice) VALUES (?,?,?,?)",
              (lottery_id, winner_private_notice, creator_private_notice, group_notice))
    conn.commit()
    conn.close()

    return jsonify({'status': 'success'})


@app.route('/edit_prize', methods=['POST'])
def edit_prize():
    data = request.form
    prize_id = int(data.get('prize_id'))
    name = data.get('name')
    total_count = int(data.get('total_count'))

    conn = sqlite3.connect('lottery.db')
    c = conn.cursor()
    c.execute("UPDATE prizes SET name =?, total_count =? WHERE id =?", (name, total_count, prize_id))
    conn.commit()
    conn.close()

    return jsonify({'status': 'success'})


# 模拟抽奖数据存储
lotteries = {
    1: {'status': 'active'}
}

@app.route('/cancel_lottery', methods=['GET'])
def cancel_lottery():
    lottery_id = int(request.args.get('lottery_id'))
    if lottery_id in lotteries:
        # 更新抽奖状态为取消
        lotteries[lottery_id]['status'] = 'cancelled'
        return jsonify({'status': 'success'})
    else:
        return jsonify({'status': 'error', 'message': '未找到该抽奖活动'})


if __name__ == '__main__':
    init_db()
    app.run(debug=True)
    