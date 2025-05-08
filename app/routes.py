import aiohttp
from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from typing import Optional
from datetime import datetime
from config import templates
import json
from bot.handlers import send_lottery_info_to_creator
from bot.verification import check_lottery_status
from bot.bot_instance import get_bot
from app.database import DatabaseConnection
from utils import logger, parse_group_input, parse_time
from telegram.error import TelegramError

router = APIRouter()


async def get_templates(request: Request) -> Jinja2Templates:
    """获取模板对象"""
    return templates
async def get_lottery_info(lottery_id):
    """获取抽奖信息"""
    result = {
        "status": "error",
        "error_title": "系统错误",
        "message": "获取抽奖信息时出错",
        "data": None
    }
    try:
        # 查询抽奖设置信息
        with DatabaseConnection() as c:
            # 获取基本设置
            c.execute("""
                SELECT 
                    ls.title,
                    ls.description,
                    ls.media_type,
                    ls.media_url,
                    ls.join_method,
                    ls.keyword_group_id,
                    ls.keyword,
                    ls.message_group_id,
                    ls.message_count,
                    ls.message_check_time,
                    ls.require_username,
                    ls.required_groups,
                    ls.draw_method,
                    ls.participant_count,
                    ls.draw_time,
                    l.status,
                    l.created_at
                FROM lottery_settings ls
                JOIN lotteries l ON l.id = ls.lottery_id
                WHERE ls.lottery_id = ?
            """, (lottery_id,))
            settings = c.fetchone()
            if not settings:
                result = {
                    "status": "error",
                    "error_title": "数据错误",
                    "message": "未找到抽奖设置信息",
                    "data": None
                }
            else:
                title, description, media_type, media_url, join_method, keyword_group_id, keyword, message_group_id, message_count, message_check_time, require_username, required_groups, draw_method, draw_when_full, draw_time, status, created_at = settings
                # 获取奖品信息
                c.execute("""
                    SELECT name, total_count
                    FROM prizes
                    WHERE lottery_id = ?
                """, (lottery_id,))
                prizes = c.fetchall()

                # 获取已参与人数
                c.execute("""
                    SELECT COUNT(*)
                    FROM participants
                    WHERE lottery_id = ?
                """, (lottery_id,))
                participant_count = c.fetchone()[0]
                group_titles = []
                if required_groups:
                    required_groups = required_groups.split(',') if required_groups else []
                    for group_id in required_groups:
                        response = await get_chat_info(group_id)
                        if isinstance(response, JSONResponse):
                            response_data = json.loads(response.body)
                            if response_data.get('status') == 'success':
                                group_title = response_data.get('data').get('title')
                                group_titles.append(f"------ {group_title}") 
                                group_titles.append("\n")
                if group_titles:
                    group_titles = f"--- 需要加入的群组/频道：\n" + "\n ".join(group_titles) + "\n"
                if draw_method == 'draw_at_time':
                    draw_time = parse_time(draw_time)
                elif draw_method == 'draw_when_full':
                    draw_time = f"满{draw_when_full}人后自动开奖"
                if keyword_group_id:
                    response = await get_chat_info(keyword_group_id)
                    if isinstance(response, JSONResponse):
                        response_data = json.loads(response.body)
                        if response_data.get('status') == 'success':
                            keyword_group = response_data.get('data').get('title')
                            keyword = f"--- 在群组  {keyword_group}  中使用关键词  {keyword}  参与抽奖"
                if require_username == 1:
                    require_username = '---  必须设置用户名'
                message_info = ''
                if message_group_id:
                    response = await get_chat_info(message_group_id)
                    if isinstance(response, JSONResponse):
                        response_data = json.loads(response.body)
                        if response_data.get('status') == 'success':
                            message_group = response_data.get('data').get('title')
                            message_info = f"--- {message_check_time}小时内在群组  {message_group}  中发送  {message_count}  条消息"
                join_method =(
                    f"{require_username}\n"
                    f"{keyword}\n"
                    f"{group_titles}\n"
                    f"{message_info}\n"
                )
                # 构建返回数据
                lottery_info = {
                    'lottery_id': lottery_id,
                    'title': title,
                    'description': description,
                    'media_type': media_type,
                    'media_url': media_url,
                    'join_method': join_method,
                    'draw_time': draw_time,
                    'status': status,
                    'created_at': created_at,
                    'current_participants': participant_count,
                    'prizes': [{'name': p[0], 'count': p[1]} for p in prizes]
                }
                result.update({
                "status": "success",
                "error_title": None,
                "message": "获取抽奖信息成功",
                "data": lottery_info
            })
    except Exception as e:
        logger.error(f"获取抽奖信息时出错: {e}", exc_info=True)
        result.update({
            "status": "error",
            "error_title": "系统错误",
            "message": f"获取抽奖信息时出错: {str(e)}"
        })
    finally:
        logger.info(f"获取抽奖信息: {result}")
        return result

@router.get("/", response_class=HTMLResponse)
async def index(
    request: Request,
    lottery_id: Optional[str] = None,
    user_id: Optional[str] = None,
    username: Optional[str] = None,
    templates: Jinja2Templates = Depends(get_templates)
):
    """首页路由"""
    try:
        # 基本参数验证
        if not user_id or not lottery_id:
            return templates.TemplateResponse(
                "error.html",
                {
                    "request": request,
                    "error_title": "参数错误",
                    "error_message": "缺少抽奖ID或用户信息"
                }
            )
         # 如果有抽奖ID，检查并更新状态
        if lottery_id:
            validity_check = await check_lottery_status(lottery_id, user_id)
            if not validity_check['valid']:
                return templates.TemplateResponse(
                    "error.html",
                    {
                        "request": request,
                        "error_title": "抽奖创建失败",
                        "error_message": validity_check['message']
                    }
                )
            elif validity_check['status'] == 'active' or validity_check['status'] == 'completed':
                response = await get_lottery_info(lottery_id)
                if response['status'] == 'error':
                    return templates.TemplateResponse(
                        "error.html",
                        {
                            "request": request,
                            "error_title": response['error_title'],
                            "error_message": response['message']
                        }
                    )
                elif response['status'] == 'success':
                    lottery_info = response['data']
                    return templates.TemplateResponse(
                        "read_only.html",
                        {
                            "request": request,
                            "lottery_info": lottery_info,
                            "is_readonly": True  # 标记表单为只读
                        }
                    )
        response = await get_chat_info(user_id)
        if isinstance(response, JSONResponse):
            response_data = json.loads(response.body)
            if response_data.get('status') == 'success':
                creator = response_data.get('data') 
                creator_info = {
                    'lottery_id': lottery_id,
                    'user_id': creator.get('id'),
                    'username': creator.get('username') or username,
                    'nickname': creator.get('title') or None
                }
                lottery_id = lottery_id
            else:
                logger.error(f"获取创建人信息失败: {response_data.get('message')}")
                return templates.TemplateResponse(
                    "error.html",
                    {
                        "request": request,
                        "error_title": "获取创建人信息失败",
                        "error_message": response_data.get('message')
                    }
                )
        else:
            logger.error("get_chat_info 返回了非 JSONResponse 对象")
            return templates.TemplateResponse(
                    "error.html",
                    {
                        "request": request,
                        "error_title": "获取创建人信息出错",
                        "error_message": "获取创建人信息时出错，请稍后重试"
                    }
                )
        
        return templates.TemplateResponse(
            "index.html",
            {"request": request, "creator_info": creator_info}
        )
        
    except Exception as e:
        logger.error(f"处理首页请求时出错: {e}", exc_info=True)
        return templates.TemplateResponse(
            "error.html",
            {
                "request": request,
                "error_title": "系统错误",
                "error_message": "加载页面时出错，请稍后重试"
            }
        )


@router.post('/create_lottery')
async def create_lottery(
    request: Request,
    title: str = Form(...),
    creator_id: str = Form(...),
    lottery_id: str = Form(...),
    join_method: str = Form(...),
    draw_method: str = Form(...),
    description: str = Form(...),
    media_type: Optional[str] = Form(None),
    media_url: Optional[str] = Form(None),
    keyword_group_id: Optional[str] = Form(None),
    keyword: Optional[str] = Form(None),
    message_group_id: Optional[str] = Form(None),
    message_count: Optional[int] = Form(None),
    message_check_time: Optional[int] = Form(None),
    require_username: Optional[str] = Form(None),
    group_ids: list[str] = Form(None),
    participant_count: Optional[int] = Form(None),
    draw_time: Optional[str] = Form(None),
    prize_name: list[str] = Form(...),
    prize_count: list[int] = Form(...)
):
    try:
        # 1. 验证必填字段
        form_data = {
            'title': title,
            'creator_id': creator_id,
            'join_method': join_method,
            'draw_method': draw_method,
            'description': description,
            'prize_name': prize_name,
            'prize_count': prize_count
        }
        required_fields = ['title', 'creator_id', 'join_method', 'draw_method', 'description', 'prize_name', 'prize_count']
        for field in required_fields:
            if not form_data.get(field):
                logger.error(f'缺少必填字段: {field}')
                return JSONResponse({'status': 'error', 'message': f'缺少必填字段: {field}'})

        # 2.处理布尔值
        require_username_bool = require_username.lower() in ('true', '1', 'yes') if require_username else False
        
        # 处理群组 ID 列表
        required_groups_str = ','.join(group_ids) if group_ids else None
        # 处理抽奖时间
        draw_time = parse_time(draw_time) if draw_time else None

        # 3. 创建抽奖活动
        with DatabaseConnection() as c:
            c.execute("""
                SELECT * FROM lotteries WHERE id = ?
                """, (lottery_id,))
            result = c.fetchone()
            if not result:
                return templates.TemplateResponse(
                    "error.html",
                    {
                        "request": request,
                        "error_title": "抽奖活动不存在",
                        "error_message": "未找到该抽奖活动"
                    }
                )
            # 3.1 修改抽奖记录状态
            c.execute("""
                UPDATE lotteries
                SET status = ?, updated_at =?
                WHERE id =? AND creator_id =?
            """, ('active', datetime.now(), lottery_id, creator_id))

            # 3.2 创建抽奖设置记录
            c.execute("""
                INSERT INTO lottery_settings (
                    lottery_id,
                    title,
                    media_type,
                    media_url,
                    description,
                    join_method,
                    keyword_group_id,
                    keyword,
                    message_group_id,
                    message_count,
                    message_check_time,
                    require_username,
                    required_groups,
                    draw_method,
                    participant_count,
                    draw_time
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                lottery_id, 
                title, 
                media_type, 
                media_url, 
                description, 
                join_method,
                keyword_group_id if keyword_group_id else None,
                keyword if keyword else None,
                message_group_id if message_group_id else None,
                message_count if message_count else None,
                message_check_time if message_check_time else None,
                1 if require_username_bool else 0,  # 将布尔值转换为整数
                required_groups_str,                 # 将群组ID列表转换为字符串
                draw_method,
                participant_count if participant_count else None,
                draw_time if draw_time else None
            ))

            # 3.3 添加奖品信息
            if prize_name and prize_count:
                if len(prize_name) != len(prize_count):
                    return JSONResponse({'status': 'error', 'message': '奖品名称和数量不匹配'})
                for name, count in zip(prize_name, prize_count):
                    try:
                        count = int(count)
                        if count <= 0:
                            raise ValueError(f"奖品 {name} 数量必须大于0")
                        c.execute("""
                            INSERT INTO prizes (
                                lottery_id,
                                name,
                                total_count
                            ) VALUES (?, ?, ?)
                        """, (lottery_id, name, count))
                    except ValueError as e:
                        logger.error(f'无效的奖品数量: {e}')
                        return JSONResponse({'status': 'error', 'message': str(e)})

        # 创建成功后组装数据
        lottery_data = {
            'lottery_id': lottery_id,
            'title': title,
            'media_type': media_type,
            'media_url': media_url,
            'description': description,
            'join_method': join_method,
            'keyword_group_id': keyword_group_id,
            'keyword': keyword,
            'message_group_id': message_group_id,
            'message_count': message_count,
            'message_check_time': message_check_time,
            'require_username': require_username_bool,
            'required_groups': required_groups_str,
            'draw_method': draw_method,
            'participant_count': participant_count,
            'draw_time': draw_time,
            'prize_names': prize_name,
            'prize_counts': prize_count
        }

        # 发送通知给创建者
        notify_success = await send_lottery_info_to_creator(creator_id, lottery_data)
        if not notify_success:
            logger.warning(f"发送抽奖信息给创建者 {creator_id} 失败")

        # 返回成功响应
        logger.info(f"成功创建抽奖活动 ID: {lottery_id}")
        return JSONResponse({
            'status': 'success',
            'lottery_id': lottery_id,
            'message': '抽奖活动创建成功'
        })

    except Exception as e:
        logger.error(f"创建抽奖活动时出错: {e}", exc_info=True)
        return JSONResponse({
            'status': 'error',
            'message': '创建抽奖活动时出错，请稍后重试'
        })

@router.get("/get_participants", response_class=JSONResponse)
async def get_participants(
    request: Request,
    lottery_id: str,
    status: Optional[str] = None,
    keyword: Optional[str] = None
):
    try:
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
        return JSONResponse({'participants': result})
    except Exception as e:
        logger.error(f"获取参与者信息时出错: {e}")
        return JSONResponse({'status': 'error', 'message': '获取参与者信息时出错，请稍后重试'})

@router.get("/get_prizes", response_class=JSONResponse)
async def get_prizes(
    request: Request,
    lottery_id: str
):
    try:
        with DatabaseConnection('lottery.db') as c:
            c.execute("SELECT id, name, total_count FROM prizes WHERE lottery_id =?", (lottery_id,))
            prizes = c.fetchall()

        result = []
        for prize in prizes:
            result.append({
                'id': prize[0],
                'name': prize[1],
                'total_count': prize[2]
            })
        return JSONResponse({'prizes': result})
    except Exception as e:
        logger.error(f"获取奖品信息时出错: {e}")
        return JSONResponse({'status': 'error', 'message': '获取奖品信息时出错，请稍后重试'})


@router.get("/cancel_lottery", response_class=JSONResponse)
async def cancel_lottery(
    request: Request,
    lottery_id: int
):
    try:
        with DatabaseConnection('lottery.db') as c:
            c.execute("SELECT id FROM lotteries WHERE id = ?", (lottery_id,))
            lottery = c.fetchone()
            if lottery:
                c.execute("UPDATE lotteries SET status = 'cancelled' WHERE id = ?", (lottery_id,))
                return JSONResponse({'status': 'success'})
            return templates.TemplateResponse(
                "error.html",
                {
                    "request": request,
                    "error_title": "抽奖活动已取消",
                    "error_message": "抽奖活动已取消，如需创建请重新使用 /new 命令。"
                }
            )
    except Exception as e:
        logger.error(f"取消抽奖时出错: {e}")
        return JSONResponse({'status': 'error', 'message': '取消抽奖时出错，请稍后重试'})


@router.get('/get_chat_info')
async def get_chat_info(query: str):
    """获取群组/频道信息"""
    try:
        # 获取机器人实例
        bot = get_bot()
        if not bot:
            return JSONResponse({
                'status': 'error',
                'message': '机器人未初始化'
            })
            
        # 验证输入
        if not query:
            return JSONResponse({
                'status': 'error',
                'message': '请提供群组/频道信息'
            })
            
        try:
            # 解析输入
            chat_id, username = await parse_group_input(query)
            # 获取群组信息
            chat = None
            try:
                if chat_id:
                    chat = await bot.get_chat(chat_id)
                elif username:
                    chat = await bot.get_chat(username)
                    
            except TelegramError as e:
                error_message = str(e).lower()
                if 'chat not found' in error_message:
                    return JSONResponse({
                        'status': 'error',
                        'message': '找不到该群组/频道，请确保：\n1. 群组/频道名称正确\n2. 机器人已被添加为管理员\n3. 群组/频道是公开的'
                    })
                elif 'bot was kicked' in error_message:
                    return JSONResponse({
                        'status': 'error',
                        'message': '机器人已被移出该群组/频道'
                    })
                else:
                    logger.error(f"Telegram API错误: {e}")
                    return JSONResponse({
                        'status': 'error',
                        'message': '获取群组信息失败，请稍后重试'
                    })
                    
            if chat:
                return JSONResponse({
                    'status': 'success',
                    'data': {
                        'id': str(chat.id),
                        'title': chat.title or chat.full_name,
                        'username': chat.username or '',
                        'type': chat.type,
                        'invite_link': getattr(chat, 'invite_link', None)
                    }
                })
            else:
                return JSONResponse({
                    'status': 'error',
                    'message': '无法获取群组信息'
                })
                
        except Exception as e:
            logger.error(f"处理群组信息时出错: {e}", exc_info=True)
            return JSONResponse({
                'status': 'error',
                'message': '处理群组信息时出错'
            })
            
    except Exception as e:
        logger.error(f"获取群组信息时出错: {e}", exc_info=True)
        return JSONResponse({
            'status': 'error',
            'message': '系统错误，请稍后重试'
        })

