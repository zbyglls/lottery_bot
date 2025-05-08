from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import IndexModel, ASCENDING, DESCENDING
from datetime import datetime, timezone
import pymongo
from config import MONGO_URI, MONGO_DB
from utils import logger, mark_initialized
from typing import Optional, Dict, Any

class MongoDBConnection:
    _instance = None
    _db = None
    
    @classmethod
    async def get_database(cls):
        """获取数据库连接单例"""
        if not cls._instance:
            try:
                client = AsyncIOMotorClient(
                    MONGO_URI,
                    tls=True,
                    tlsAllowInvalidCertificates=True,
                    serverSelectionTimeoutMS=30000,  
                    connectTimeoutMS=30000,
                    socketTimeoutMS=30000,
                    waitQueueTimeoutMS=30000,
                    retryWrites=True,
                    w='majority',
                    server_api=pymongo.server_api.ServerApi(
                        version="1", 
                        strict=True, 
                        deprecation_errors=True))
                cls._db = client[MONGO_DB]
                cls._instance = client
                logger.info("MongoDB 连接成功")
            except Exception as e:
                logger.error(f"MongoDB 连接失败: {e}", exc_info=True)
                raise
        return cls._db

async def init_db():
    """初始化数据库集合和索引"""
    if mark_initialized('database'):
        return
        
    try:
        db = await MongoDBConnection.get_database()
        
        # MongoDB 集合验证规则
        validators = {
            'lotteries': {
                '$jsonSchema': {
                    'bsonType': 'object',
                    'required': ['id', 'creator_id', 'status', 'created_at', 'updated_at'],
                    'properties': {
                        'id': {'bsonType': 'long'},
                        'creator_id': {'bsonType': 'long'},
                        'creator_name': {'bsonType': 'string'},
                        'status': {
                            'enum': ['draft', 'creating', 'active', 'completed', 'cancelled']
                        },
                        'created_at': {'bsonType': 'date'},
                        'updated_at': {'bsonType': 'date'}
                    }
                }
            },
            'lottery_settings': {
                '$jsonSchema': {
                    'bsonType': 'object',
                    'required': ['lottery_id', 'title','description','join_method', 'draw_method'],
                    'properties': {
                        'lottery_id': {'bsonType': 'long'},
                        'title': {'bsonType': 'string'},
                        'description': {'bsonType': 'string'},
                        'media_type': {'enum': ['','image', 'video']},
                        'media_url': {'bsonType': 'string'},
                        'join_method': {
                            'enum': ['private_chat', 'group_keyword', 'group_message']
                        },
                        'keyword_group_id': {'bsonType': 'string'},
                        'keyword': {'bsonType': 'string'},
                        'message_group_id': {'bsonType': 'string'},
                        'message_count': {'bsonType': 'int'},
                        'message_check_time': {'bsonType': 'int'},
                        'require_username': {'bsonType': 'bool'},
                        'required_groups': {'bsonType': 'array'},
                        'draw_method': {
                            'enum': ['draw_when_full', 'draw_at_time']
                        },
                        'participant_count': {'bsonType': 'int'},
                        'draw_time': {'bsonType': 'date'},
                        'message_count_tracked': {'bsonType': 'bool'}
                    }
                }
            },
            'prizes': {
                '$jsonSchema': {
                    'bsonType': 'object',
                    'required': ['lottery_id', 'name', 'total_count'],
                    'properties': {
                        'lottery_id': {'bsonType': 'long'},
                        'name': {'bsonType': 'string'},
                        'total_count': {'bsonType': 'int'}
                    }
                }
            },
            'prize_winners': {
                '$jsonSchema': {
                    'bsonType': 'object',
                    'required': ['prize_id', 'participant_id', 'lottery_id', 'status'],
                    'properties': {
                        'prize_id': {'bsonType': 'objectId'},
                        'participant_id': {'bsonType': 'objectId'},
                        'lottery_id': {'bsonType': 'long'},
                        'status': {
                            'enum': ['pending', 'claimed', 'expired']
                        },
                        'win_time': {'bsonType': 'date'}
                    }
                }
            },
            'participants': {
                '$jsonSchema': {
                    'bsonType': 'object',
                    'required': ['lottery_id', 'user_id', 'nickname'],
                    'properties': {
                        'lottery_id': {'bsonType': 'long'},
                        'user_id': {'bsonType': 'long'},
                        'nickname': {'bsonType': 'string'},
                        'username': {'bsonType': 'string'},
                        'join_time': {'bsonType': 'date'}
                    }
                }
            },
            'message_counts': {
                '$jsonSchema': {
                    'bsonType': 'object',
                    'required': ['lottery_id', 'user_id', 'group_id', 'message_count'],
                    'properties': {
                        'lottery_id': {'bsonType': 'long'},
                        'user_id': {'bsonType': 'long'},
                        'group_id': {'bsonType': 'string'},
                        'message_count': {'bsonType': 'int'},
                        'last_message_time': {'bsonType': 'date'}
                    }
                }
            }
        }
        
        # 创建集合
        collections = {
            # 抽奖表
            'lotteries': [
                IndexModel([('id', ASCENDING)], unique=True),
                IndexModel([('creator_id', ASCENDING)]),
                IndexModel([('status', ASCENDING)]),
                IndexModel([('updated_at', DESCENDING)])
            ],
            # 抽奖设置表
            'lottery_settings': [
                IndexModel([('lottery_id', ASCENDING)], unique=True)
            ],
            # 奖品表
            'prizes': [
                IndexModel([('lottery_id', ASCENDING)])
            ],
            # 中奖记录表
            'prize_winners': [
                IndexModel([('lottery_id', ASCENDING)]),
                IndexModel([('participant_id', ASCENDING)])
            ],
            # 参与者表
            'participants': [
                IndexModel([('lottery_id', ASCENDING)]),
                IndexModel([('user_id', ASCENDING)]),
                IndexModel([('lottery_id', ASCENDING), ('user_id', ASCENDING)], unique=True)
            ],
            # 消息跟踪记录表
            'message_counts': [
                IndexModel([('lottery_id', ASCENDING)]),
                IndexModel([('user_id', ASCENDING)]),
                IndexModel([('group_id', ASCENDING)]),
                IndexModel([('last_message_time', DESCENDING)]),
                IndexModel(
                    [('lottery_id', ASCENDING), 
                     ('user_id', ASCENDING), 
                     ('group_id', ASCENDING)
                    ], 
                    unique=True
                )
            ]
        }
        
        # 创建或更新集合和验证规则
        for collection_name, validator in validators.items():
            try:
                await db.create_collection(collection_name)
            except Exception as e:
                if 'already exists' not in str(e):
                    raise
                    
            # 设置验证规则
            await db.command({
                'collMod': collection_name,
                'validator': validator,
                'validationLevel': 'strict',
                'validationAction': 'error'
            })
            
            # 应用索引
            if collection_name in collections:
                await db[collection_name].create_indexes(collections[collection_name])
                
        logger.info("MongoDB 集合、验证规则和索引初始化完成")
        
    except Exception as e:
        logger.error(f"初始化 MongoDB 时出错: {e}", exc_info=True)
        raise

async def check_db():
    """检查数据库集合是否存在"""
    try:
        db = await MongoDBConnection.get_database()
        collections = await db.list_collection_names()
        required_collections = ['lotteries', 'lottery_settings', 'prizes', 'prize_winners', 'participants']
        
        missing_collections = set(required_collections) - set(collections)
        if missing_collections:
            logger.info(f"缺少以下集合: {', '.join(missing_collections)}")
            await init_db()
        else:
            logger.info("MongoDB 集合结构完整")
            
    except Exception as e:
        logger.error(f"检查 MongoDB 时出错: {e}", exc_info=True)
        raise

# 集合模式定义（用于文档参考）
COLLECTION_SCHEMAS = {
    'lotteries': {
        'id': int,
        'creator_id': int,
        'creator_name': str,
        'status': str,  # draft, creating, active, completed, cancelled
        'created_at': datetime,
        'updated_at': datetime
    },
    'lottery_settings': {
        'lottery_id': int,
        'title': str,
        'media_type': str,  # image or video
        'media_url': str,
        'description': str,
        'join_method': str, # private_chat, group_keyword, group-message
        'keyword_group_id': str,
        'keyword': str,
        'message_group_id': str,
        'message_count': int,
        'message_check_time': int,
        'require_username': bool,
        'required_groups': list,
        'draw_method': str,  # draw_when_full, draw_at_time
        'participant_count': int,
        'draw_time': datetime,
        'message_count_tracked': bool
    },
    'prizes': {
        'lottery_id': int,
        'name': str,
        'total_count': int
    },
    'prize_winners': {
        'prize_id': int,
        'participant_id': int,
        'lottery_id': int,
        'win_time': datetime,
        'status': str  # pending, claimed, expired
    },
    'participants': {
        'lottery_id': int,
        'user_id': str,
        'nickname': str,
        'username': str,
        'join_time': datetime
    },
    'message_counts': {
        'lottery_id': int,
        'user_id': int,
        'group_id': str,
        'message_count': int,
        'last_message_time': datetime
    }
}







