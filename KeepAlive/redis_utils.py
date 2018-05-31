import uuid
import time
import redis
import json

from settings import (
    REDIS_HOST, REDIS_PORT, DEFAULT_REDIS_DB,
    REDIS_PASSWORD, LOCKER_PREFIX,TIMER_RECORDER)


def get_redis_conn(**kwargs):
    host = kwargs.get('host', REDIS_HOST)
    port = kwargs.get('port', REDIS_PORT)
    db = kwargs.get('db', DEFAULT_REDIS_DB)
    password = kwargs.get('password', REDIS_PASSWORD)
    return redis.StrictRedis(host, port, db, password)


def dict_to_redis_hset(r, hkey, dict_to_store):
    """
    Saves `dict_to_store` dict into Redis hash, where `hkey` is key of hash.
    >>> import redis
    >>> r = redis.StrictRedis(host='localhost')
    >>> d = {'a':1, 'b':7, 'foo':'bar'}
    >>> dict_to_redis_hset(r, 'test', d)
    True
    >>> r.hgetall('test')
    {'a':1, 'b':7, 'foo':'bar'}
    """
    return all([r.hset(hkey, k, v) for k, v in dict_to_store.items()])



def redis_hget(conn,key,model_type):
    return json.loads(conn.hgetall(key)[model_type])
    
def acquire_lock(conn, lock_name, acquire_timeout=10, lock_timeout=10):
    """inspired by the book 'redis in action' """
    identifier = str(uuid.uuid4())
    lock_name = LOCKER_PREFIX + lock_name
    end = time.time() + acquire_timeout

    while time.time() < end:
        if conn.set(lock_name, identifier, lock_timeout, nx=True):
            return identifier
        elif not conn.ttl(lock_name) or conn.ttl(lock_name) == -1:
            conn.expire(lock_name, lock_timeout)
        time.sleep(0.1)

        return False