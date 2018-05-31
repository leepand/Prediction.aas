# -*- coding:utf-8 -*-
import datetime
import hashlib
import json
import time
import yaml
import redis
r = redis.StrictRedis(host='localhost')


DATETIME_FORMAT = '%m/%d %H:%M'


def format_now():
    return datetime.datetime.now().strftime(DATETIME_FORMAT)
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


class Test:
    def __init__(self, owner,config):
        self.owner = owner
        self.config = config
        self.id = hashlib.sha256(json.dumps(config).encode()).hexdigest()
        
        self.down_message = config.setdefault('down_message', '$name is down, since $last_pass_time')
        self.up_message = config.setdefault('up_message', '$name is up')
        self.ignore_fail_count = config.setdefault('ignore_fail_count', 0)
        self.alert_period_hours = config.setdefault('alert_period_hours', 1.0)        
    def get(self, key, default=None):
        if not self.id in self.owner.state:
            self.owner.state[self.id] = {}
        return self.owner.state[self.id].setdefault(key, default)

    def set(self, key, value):
        if not self.id in self.owner.state:
            self.owner.state[self.id] = {}
        self.owner.state[self.id][key] = value

    def expand_message(self, message):
        for key, value in self.config.items():
            message = message.replace('$' + key, str(value))
        if not self.id in self.owner.state:
            self.owner.state[self.id] = {}
        for key, value in self.owner.state[self.id].items():
            message = message.replace('$' + key, str(value))
        return message

    def do_pass(self):
        if self.get('state') != 'passing':
            self.owner.notify(self.expand_message(self.up_message))
            self.set('state', 'passing')
            self.set('first_pass_time', format_now())
            self.set('last_fail_alert_time', 0)
        self.set('last_pass_time', format_now())
        self.set('fail_count', 0)
        self.set('url', 'http://%s:%d' % ( self.config['host'], self.config['port']))
        self.set('global_worker_id', self.config['worker_id'])
        #self.set('model_id', self.config['model_id'])
        dict_to_redis_hset(r, 'server_real_time_state', self.owner.state)
        #with open('heartbeat_ok.json', 'w') as state_file:
        #    json.dump(self.owner.state, state_file)

    def do_fail(self):
        fail_count = self.get('fail_count', 0) + 1
        self.set('fail_count', fail_count)
        if fail_count > self.ignore_fail_count:
            if self.get('state') != 'failing':
                self.set('state', 'failing')
                self.set('first_fail_time', format_now())
            alert_time = time.time()
            last_alert_fail_time = self.get('last_fail_alert_time', 0)
            if alert_time - last_alert_fail_time >= self.alert_period_hours * 60 * 60:
                self.set('last_fail_alert_time', alert_time)
                self.owner.notify(self.expand_message(self.down_message))
        self.set('last_fail_time', format_now())
        self.set('url', 'http://%s:%d' % ( self.config['host'], self.config['port']))
        self.set('global_worker_id', self.config['worker_id'])
        #self.set('model_id', self.config['model_id'])
        dict_to_redis_hset(r, 'server_real_time_state', self.owner.state)
        #with open('heartbeat_down.json', 'w') as state_file:
        #    json.dump(self.owner.state, state_file)



class TCPTest(Test):
    def __init__(self, owner,config):
        Test.__init__(self,owner,config)
        #super().__init__(owner, config)
        import socket
        self.host = config['host']
        self.port = config['port']

    def run(self):
        import socket
        try:
            sock=socket.create_connection((self.host, self.port))
            print('{}:{} OK'.format(self.host, self.port))
            sock.shutdown(socket.SHUT_RDWR)
        except:
            print('{}:{} {}'.format(self.host, self.port, 'err'))
            self.do_fail()
            return 'down'
        else:
            self.do_pass()
            return 'pass'


class HTTPTest(Test):
    def __init__(self, owner, config):
        Test.__init__(self,owner, config)#注意此处参数含self  
        #super().__init__(owner, config)
        import requests
        self.url = 'http://%s:%d' % ( config['host'], config['port'])#'http://%s:%d' % (worker.host,worker.port)#config['url']
        self.headers ={'x-ha-access': 'XXXXXXXX', 'Content-Type': 'application/json'}#config.get('headers', {})
        #print('self.headers',self.headers)
    def run(self):
        import requests
        try:
            r = requests.get(self.url, headers=self.headers)
            print(self.url, r.status_code, r.reason)
            if r.status_code == 200:
                self.do_pass()
                return 'pass'
            else:
                self.do_fail()
                return 'down'
        except requests.ConnectionError as err:
            print('{}:{} {}'.format(self.url, self.headers, err))
            self.do_fail()
            return 'down'


class Heartbeat4LB:
    def __init__(self):
        self.state = {}
        self.tests = []
        self.alerts = []
    def run_heart(self,config):
        if config['test_type']=='tcp':            
            self.tests.append(TCPTest(self,config))
        else:
            self.tests.append(HTTPTest(self,config))
                    
    def notify(self, message):
        for alert in self.alerts:
            alert.send(message)

    def test(self):
        for test in self.tests:
            result=test.run()
        return result

    def run(self,conf):
        self.run_heart(conf)
        result= self.test()
        return result


