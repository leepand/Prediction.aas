"""
Settings for UpdateAlive list schedule.
"""
# redis settings.If you use docker-compose, REDIS_HOST = 'redis'
REDIS_HOST = 'localhost'
REDIS_PORT = 6379
REDIS_PASSWORD = ''
DEFAULT_REDIS_DB = 0
LOCKER_PREFIX = 'heartbeat:lock:'
TIMER_RECORDER = 'heartbeat:scheduler:task'
