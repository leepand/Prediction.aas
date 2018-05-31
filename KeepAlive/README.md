####  服务探活与负载分离

- 周期探活，并将存活服务list更新至redis

- 探测日志信息查看：

  ```
  import redis
  r = redis.StrictRedis(host='localhost')
  r.hgetall('server_real_time_state')
  ```

