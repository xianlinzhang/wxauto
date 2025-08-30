import os
from dotenv import load_dotenv
import redis

# 加载.env文件
load_dotenv()

# 从.env文件读取配置
redis_host = os.getenv('REDIS_HOST')
redis_port = int(os.getenv('REDIS_PORT'))
redis_db = int(os.getenv('REDIS_DB'))
redis_password = os.getenv('REDIS_PASSWORD')

# 使用配置连接Redis
redisClient = redis.Redis(host=redis_host, port=redis_port, db=redis_db, password=redis_password)
