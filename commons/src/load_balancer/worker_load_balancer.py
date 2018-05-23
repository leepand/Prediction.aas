# Copyright 2017-2018, the original author or authors.

# Licensed under the Apache License, Version 2.0 (the "License");
# You may not use this file except in compliance
# with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied. See the License for the
# specific language governing permissions and limitations
# under the License.
#

import logging
import random
import json
import yaml

from commons.src.config import config_loader
from commons.src.load_balancer.worker_info import WorkerInfo
from random import randint

import requests
import redis
import ast


#from meta_info_storage import RedisStorage, DictStorage,storage

#import redis
#from meta_info_storage import RedisDict
#from persistentdict import RedisDict
#from dict_db import DictDbFactory, Consts
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

r = redis.StrictRedis(host='localhost')

class UserEncoder(json.JSONEncoder):  
    def default(self, obj):  
        if isinstance(obj, WorkerInfo):  
            return {'host':obj.host,'port':obj.port,'local_worker_id':obj.local_worker_id,'global_worker_id':obj.global_worker_id}
        return json.JSONEncoder.default(self, obj)
class WorkerLoadBalancer:
    """
    A generic worker load balancer which helps in choosing a worker randomly.
    """

    def __init__(self):
        """
        Constructor
        Returns: None

        """
        



        #: dict model type to model to worker list map.

        self.model_type_to_model_to_worker_list = {}
        
        self.session = requests.Session()

        #: dict model type to worker id to worker info map
        self.model_type_to_worker_id_to_worker = {}

        #: dict Model type to model to workers map
        self.model_type_to_model_to_workers_map ={}
        self.model_info={}
        self.model_id_request_count={}
        self.worker_request_count={}
        # Logger instance
        self.logger = logging.getLogger(__name__)

    def update_workers_list(self, model_type_to_model_to_workers_map):
        """
        Updates model type to model to workers list map
        :param model_type_to_model_to_workers_map:
        :return:
        """
        if model_type_to_model_to_workers_map:
            model_type_to_model_to_worker_list = {}
            model_type_to_worker_id_to_worker = {}
            for model_type in model_type_to_model_to_workers_map.keys():
                model_to_worker_list = {}
                worker_id_to_worker = {}
                for model_id in model_type_to_model_to_workers_map[model_type].keys():
                    workers = []
                    worker_ids = []

                    for worker in model_type_to_model_to_workers_map[model_type][model_id]:
                        worker_info = WorkerInfo(worker["host"], worker["port"], worker["local_worker_id"])
                        workers.append(worker_info)
                        worker_ids.append(worker_info.global_worker_id)
                        worker_id_to_worker[worker_info.global_worker_id] = worker_info

                    if model_id in model_to_worker_list.keys():
                        model_to_worker_list[model_id] = list(set(model_to_worker_list[model_id])
                                                            | set(worker_ids))
                    else:
                        model_to_worker_list[model_id] = worker_ids

                model_type_to_model_to_worker_list[model_type] = model_to_worker_list
                model_type_to_worker_id_to_worker[model_type] = json.dumps(worker_id_to_worker,cls=UserEncoder)
            self.model_type_to_worker_id_to_worker = model_type_to_worker_id_to_worker
            dict_to_redis_hset(r, 'model_type_to_worker_id_to_worker', self.model_type_to_worker_id_to_worker)
            self.model_type_to_model_to_worker_list = model_type_to_model_to_worker_list
            
            self.model_info['model_type_to_model_to_worker_list']=self.model_type_to_model_to_worker_list
            self.model_info['model_type_to_worker_id_to_worker']=self.model_type_to_worker_id_to_worker
            self.model_info['model_type_to_model_to_workers_map']=self.model_type_to_model_to_workers_map
        #return json.dumps(self.model_info)

    def remove_workers(self, model_type, model_id, workers):
        """
         Used to remove workers to a model
         :param model_type
         :param model_id:
         :param workers:
         :return: None
         """
        for worker in workers:
            self.model_type_to_worker_id_to_worker[model_type].pop(worker.global_worker_id, None)

        if model_id in self.model_type_to_model_to_worker_list[model_type].keys():
            for worker in workers:
                if worker.global_worker_id in self.model_type_to_model_to_worker_list[model_type][model_id]:
                    self.model_type_to_model_to_worker_list[model_type][model_id].remove(worker.global_worker_id)
                    if not self.model_type_to_model_to_worker_list[model_type][model_id]:
                        self.model_type_to_model_to_worker_list[model_type].pop(model_id, None)
    def isalive(self,model_type,worker_id_list):
        worker_id = random.choice(worker_id_list)    
        while True:   
            try: 
                
                random_worker=json.loads(self.model_type_to_worker_id_to_worker[model_type])[worker_id]
                host_port='http://%s:%d' % (random_worker['host'],random_worker['port'])
                resp = self.session.request('get', url=host_port, params=None, json=None, timeout=3)
                return worker_id
            except requests.exceptions.RequestException:
                worker_id = random.choice(worker_id_list)
                random_worker=self.model_type_to_worker_id_to_worker[model_type][worker_id]
                host_port='http://%s:%d' % (random_worker['host'],random_worker['port'])



    def choose_worker(self, model_type, model_id):
        """
        Picks a worker(random) from available workers

        :param model_type
        :param model_id:
        :return: a randomly chosen worker
        """
        print(model_type, model_id)
        if self.model_type_to_model_to_worker_list.get(model_type):
            if model_id in self.model_type_to_model_to_worker_list[model_type].keys():
                worker_id_list = self.model_type_to_model_to_worker_list[model_type][model_id]
                
                #worker_id = random.choice(worker_id_list)
                #random_worker=self.model_type_to_worker_id_to_worker[model_type][worker_id]
                #keek alive by leepand
                worker_id=self.isalive(model_type,worker_id_list)
                #keek end by leepand
                #count requests by leepand
                if model_id in self.model_id_request_count:
                    #print 'self.model_id_request_count',self.model_id_request_count
                    if worker_id in self.model_id_request_count[model_id]:
                        self.model_id_request_count[model_id][worker_id]+=1
                    else:
                        self.model_id_request_count[model_id][worker_id]=1
                else:
                    self.worker_request_count[worker_id]=1
                    self.model_id_request_count[model_id]=self.worker_request_count
                #end compute count by leepand
                #d = {'a':1, 'b':7, 'foo':'bar'}
                dict_to_redis_hset(r, 'model_id_request_count', json.dumps(self.model_id_request_count))
                
                #s=r.hgetall('test')['fooq']
                #d11 = ast.literal_eval(s)
                #redis_load=yaml.load(r.hgetall('model_type_to_worker_id_to_worker')[model_type])
                #for x in redis_load.keys():
                #    if worker_id==ast.literal_eval(x):
                #        return redis_load[x]
                return  json.loads(r.hgetall('model_type_to_worker_id_to_worker')[model_type])[worker_id]#self.model_type_to_worker_id_to_worker[model_type][worker_id]
            else:
                raise Exception("No worker available for the given model! ")
        else:
            raise Exception("No worker available for the given model type! ")

    def get_all_workers(self, model_type):
        """
        Returns all the workers available for the given model type
        Args:
            model_type: Type of the model

        Returns: all the workers available for the given model type

        """
        return self.model_type_to_worker_id_to_worker.get(model_type)

    def get_model_to_workers_list(self, model_type):
        """
        Returns the list of workers for a given model_id
        Args:
            model_type: Type of the model
        Returns: List of workers for the given model type

        """
        return self.model_type_to_model_to_worker_list.get(model_type)


    def get_worker_info(self, worker_id, model_type):
        """
        Returns worker information of a given worker
        Args:
            worker_id: Global worker id
            model_type: Type of the model

        Returns: Worker information of the given worker

        """
        if self.model_type_to_worker_id_to_worker.get(model_type):
            return self.model_type_to_worker_id_to_worker.get(model_type).get(worker_id)
        else:
            return None

    def check_if_model_to_workers_map_is_empty(self):
        """
        Checks if model to workers map is empty
        Returns: False if model to workers map is empty else True

        """
        return False if self.model_type_to_model_to_worker_list else True


