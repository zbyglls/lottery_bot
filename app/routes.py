
from bson import Int64
from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from typing import Optional
from datetime import datetime, timezone
from config import templates
import json
from bot.handlers import send_lottery_info_to_creator
from bot.verification import check_lottery_status
from bot.bot_instance import get_bot
from app.database import MongoDBConnection 
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
        db = await MongoDBConnection.get_database()
        
        # 获取抽奖设置
        pipeline = [
            {
                '$match': {
                    'lottery_id': lottery_id
                }
            },
            {
                '$lookup': {
                    'from': 'lotteries',
                    'localField': 'lottery_id',
                    'foreignField': 'id',
                    'as': 'lottery'
                }
            },
            {
                '$unwind': '$lottery'
            }
        ]
        
        settings = await db.lottery_settings.aggregate(pipeline).to_list(1)
        if not settings:
            result.update({
                "status": "error",
                "error_title": "数据错误",
                "message": "未找到抽奖设置信息"
            })
            return result
            
        setting = settings[0]
        
        # 获取奖品信息
        prizes = await db.prizes.find({'lottery_id': lottery_id}).to_list(None)
        
        # 获取参与人数
        participant_count = await db.participants.count_documents({'lottery_id': lottery_id})
        
        # 处理群组信息
        group_titles = []
        if setting.get('required_groups'):
            for group_id in setting['required_groups']:
                response = await get_chat_info(group_id)
                if isinstance(response, JSONResponse):
                    response_data = json.loads(response.body)
                    if response_data.get('status') == 'success':
                        group_title = response_data.get('data').get('title')
                        group_titles.append(f"------ {group_title}")
            
        # 处理开奖时间
        draw_time = setting.get('draw_time')
        if setting.get('draw_method') == 'draw_at_time':
            draw_time = draw_time.strftime('%Y-%m-%d %H:%M:%S')
        elif setting.get('draw_method') == 'draw_when_full':
            draw_time = f"满{setting.get('participant_count')}人后自动开奖"
            
        # 处理参与方式信息
        join_method_parts = []
        if setting.get('require_username'):
            join_method_parts.append('---  必须设置用户名')
            
        if setting.get('keyword_group_id'):
            response = await get_chat_info(setting['keyword_group_id'])
            if isinstance(response, JSONResponse):
                response_data = json.loads(response.body)
                if response_data.get('status') == 'success':
                    group_title = response_data.get('data').get('title')
                    join_method_parts.append(
                        f"--- 在群组 {group_title} 中使用关键词 {setting.get('keyword')} 参与抽奖"
                    )
                    
        if setting.get('message_group_id'):
            response = await get_chat_info(setting['message_group_id'])
            if isinstance(response, JSONResponse):
                response_data = json.loads(response.body)
                if response_data.get('status') == 'success':
                    group_title = response_data.get('data').get('title')
                    join_method_parts.append(
                        f"--- {setting.get('message_check_time')}小时内在群组 {group_title} "
                        f"中发送 {setting.get('message_count')} 条消息"
                    )
                    
        if group_titles:
            join_method_parts.append(
                "--- 需要加入的群组/频道：\n" + "\n ".join(group_titles)
            )
            
        join_method = "\n".join(join_method_parts)
        
        # 构建返回数据
        lottery_info = {
            'lottery_id': lottery_id,
            'title': setting.get('title'),
            'description': setting.get('description'),
            'media_type': setting.get('media_type'),
            'media_url': setting.get('media_url'),
            'join_method': join_method,
            'draw_time': draw_time,
            'status': setting['lottery']['status'],
            'created_at': setting['lottery']['created_at'],
            'current_participants': participant_count,
            'prizes': [{'name': p['name'], 'count': p['total_count']} for p in prizes]
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
    """创建抽奖活动"""
    try:
        # 1. 验证必填字段
        required_fields = {
            'title': title,
            'creator_id': creator_id,
            'join_method': join_method,
            'draw_method': draw_method,
            'description': description,
            'prize_name': prize_name,
            'prize_count': prize_count
        }
        for field, value in required_fields.items():
            if not value:
                logger.error(f'缺少必填字段: {field}')
                return JSONResponse({'status': 'error', 'message': f'缺少必填字段: {field}'})

        # 2. 获取数据库连接
        db = await MongoDBConnection.get_database()
        
        # 3. 验证抽奖是否存在
        lottery = await db.lotteries.find_one({'id': lottery_id})
        if not lottery:
            return JSONResponse({
                'status': 'error',
                'message': '未找到该抽奖活动'
            })
            
        # 4. 更新抽奖状态

        now = datetime.now(timezone.utc)
        await db.lotteries.update_one(
            {'id': lottery_id, 'creator_id': Int64(creator_id)},
            {
                '$set': {
                    'status': 'active',
                    'updated_at': now
                }
            }
        )


        logger.info(await db.lotteries.find_one({'id': lottery_id}))
        # 5. 创建抽奖设置
        lottery_settings = {
            'lottery_id': lottery_id,
            'title': title,
            'media_type': media_type if media_type else None,
            'media_url': media_url if media_url else None,
            'description': description,
            'join_method': join_method,
            'keyword_group_id': keyword_group_id if keyword_group_id else None,
            'keyword': keyword if keyword else None,
            'message_group_id': message_group_id if message_group_id else None,
            'message_count': message_count if message_count else None,
            'message_check_time': message_check_time if message_check_time else None,
            'require_username': require_username.lower() in ('true', '1', 'yes') if require_username else False,
            'required_groups': group_ids if group_ids else None,
            'draw_method': draw_method,
            'participant_count': participant_count if participant_count else None,
            'draw_time': parse_time(draw_time) if draw_time else None,
            'created_at': now,
            'updated_at': now
        }
        
        await db.lottery_settings.insert_one(lottery_settings)
        
        # 6. 创建奖品记录
        if len(prize_name) != len(prize_count):
            return JSONResponse({'status': 'error', 'message': '奖品名称和数量不匹配'})
            
        prizes = []
        for name, count in zip(prize_name, prize_count):
            try:
                count = int(count)
                if count <= 0:
                    raise ValueError(f"奖品 {name} 数量必须大于0")
                    
                prizes.append({
                    'lottery_id': lottery_id,
                    'name': name,
                    'total_count': count
                })
                
            except ValueError as e:
                logger.error(f'无效的奖品数量: {e}')
                return JSONResponse({'status': 'error', 'message': str(e)})
                
        if prizes:
            await db.prizes.insert_many(prizes)
        
        # 7. 组装返回数据
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
            'require_username': lottery_settings['require_username'],
            'required_groups': group_ids,
            'draw_method': draw_method,
            'participant_count': participant_count,
            'draw_time': lottery_settings['draw_time'],
            'prize_names': prize_name,
            'prize_counts': prize_count
        }
        
        # 8. 发送通知给创建者
        notify_success = await send_lottery_info_to_creator(creator_id, lottery_data)
        if not notify_success:
            logger.warning(f"发送抽奖信息给创建者 {creator_id} 失败")
        
        # 9. 返回成功响应
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
    """获取抽奖参与者列表"""
    try:
        # 构建查询条件
        query = {'lottery_id': lottery_id}
        if keyword:
            query['$or'] = [
                {'nickname': {'$regex': keyword, '$options': 'i'}},
                {'user_id': {'$regex': keyword, '$options': 'i'}}
            ]
            
        # 获取数据库连接
        db = await MongoDBConnection.get_database()
        
        # 执行查询
        cursor = db.participants.find(
            query,
            {
                'nickname': 1, 
                'user_id': 1, 
                'username': 1, 
                'join_time': 1,
                '_id': 0
            }
        ).sort('join_time', -1)
        
        # 获取结果
        participants = await cursor.to_list(length=None)
        
        # 处理时间格式
        for p in participants:
            if 'join_time' in p:
                p['join_time'] = p['join_time'].strftime('%Y-%m-%d %H:%M:%S')
                
        return JSONResponse({'participants': participants})
        
    except Exception as e:
        logger.error(f"获取参与者信息时出错: {e}", exc_info=True)
        return JSONResponse({
            'status': 'error',
            'message': '获取参与者信息时出错，请稍后重试'
        })

@router.get("/get_prizes", response_class=JSONResponse)
async def get_prizes(request: Request, lottery_id: str):
    """获取抽奖奖品列表"""
    try:
        # 获取数据库连接
        db = await MongoDBConnection.get_database()
        
        # 执行查询
        cursor = db.prizes.find(
            {'lottery_id': lottery_id},
            {
                'name': 1,
                'total_count': 1,
                '_id': 1
            }
        )
        
        # 获取结果
        prizes = await cursor.to_list(length=None)
        
        # 格式化结果
        result = [{
            'id': str(prize['_id']),
            'name': prize['name'],
            'total_count': prize['total_count']
        } for prize in prizes]
        
        return JSONResponse({'prizes': result})
        
    except Exception as e:
        logger.error(f"获取奖品信息时出错: {e}", exc_info=True)
        return JSONResponse({
            'status': 'error',
            'message': '获取奖品信息时出错，请稍后重试'
        })


@router.get("/cancel_lottery", response_class=JSONResponse)
async def cancel_lottery(request: Request, lottery_id: str):
    """取消抽奖活动"""
    try:
        # 获取数据库连接
        db = await MongoDBConnection.get_database()
        
        # 检查抽奖是否存在
        lottery = await db.lotteries.find_one({'id': lottery_id})
        if not lottery:
            return templates.TemplateResponse(
                "error.html",
                {
                    "request": request,
                    "error_title": "抽奖不存在",
                    "error_message": "未找到该抽奖活动"
                }
            )
            
        # 更新抽奖状态
        result = await db.lotteries.update_one(
            {'id': lottery_id},
            {
                '$set': {
                    'status': 'cancelled',
                    'updated_at': datetime.now(timezone.utc)
                }
            }
        )
        
        if result.modified_count > 0:
            return JSONResponse({'status': 'success'})
        else:
            return templates.TemplateResponse(
                "error.html",
                {
                    "request": request,
                    "error_title": "更新失败",
                    "error_message": "取消抽奖失败，请稍后重试"
                }
            )
            
    except Exception as e:
        logger.error(f"取消抽奖时出错: {e}", exc_info=True)
        return JSONResponse({
            'status': 'error',
            'message': '取消抽奖时出错，请稍后重试'
        })


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

