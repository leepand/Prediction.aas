# -*- coding:utf-8 -*-
"""
This module schedules all the tasks according to main func.
"""
import time
#from multiprocessing import Pool
from multiprocessing.pool import ThreadPool as Pool
import schedule
from Heartbeat import Heartbeat4LB
import json
from redis_utils import (
    get_redis_conn,dict_to_redis_hset,redis_hget)


class BaseScheduler:
    def __init__(self, name, tasks, task_queues=None):
        """
        init function for schedulers.
        :param name: scheduler name, generally the value is used by the scheduler
        :param tasks: tasks in config.rules
        :param task_queues: for all jobs, the value is task_queue, while for update usable service list, it's task name
        """
        self.name = name
        self.tasks = tasks
        self.task_queues = list() if not task_queues else task_queues

    def schedule_with_delay(self):
        for task in self.tasks:
            interval = task.get('interval')
            job=task.get('job')
            #print task
            schedule.every(interval).minutes.do(self.main_func,task)
        while True:
            schedule.run_pending()
            time.sleep(1)

    def schedule_all_right_now(self):
        pool = Pool()
        #self.schedule_task_with_lock:需要执行的job，self.tasks：参数
        pool.map(self.main_func, self.tasks)
        pool.close() # close后进程池不能在apply任务 
        pool.join()

    def get_lock(self, conn, task):
        if not task.get('enable'):
            return None
        task_queue = task.get('task_queue')
        if task_queue not in self.task_queues:
            return None

        task_name = task.get('name')
        lock_indentifier = acquire_lock(conn, task_name)
        return lock_indentifier

    def main_func(self, task):
        """Update Alive scheduler filters tasks according to task name
        since its task name stands for task type"""
        print('task',task)
        
        task_queue = task.get('task_queue')
        print('task.get',task.get('enable'))
        #if task_queue not in self.task_queues:
        #    return None
        model_type = task.get('model_type')
        key=task.get('model_info_key')
        interval = task.get('interval')
        worker_info=task.get('worker_info')
        
        #if task_queue not in self.task_queues:
        #    return None
        conn = get_redis_conn()
        
        worklist_db=redis_hget(conn,key,model_type)
        print('worklist_db',worklist_db,key)
        heartbeat = Heartbeat4LB()
        new_worker_list_dict={}
        new_list_dict={}
        for model_id,worklist in worklist_db.items():
            new_list=[]
        
            for worker_id in worklist:
                per_worker=redis_hget(conn,worker_info,model_type)[worker_id]
                worker_status=heartbeat.run({'host':per_worker['host'],'port':per_worker['port'],'worker_id':worker_id,'model_id':model_id,'test_type':'tcp'})
                if worker_status=='pass':
                    new_list.append(worker_id)
            new_list_dict[model_id]=new_list
        if 'AI' not in new_worker_list_dict:
            new_worker_list_dict['AI']={}
            new_worker_list_dict['AI']=json.dumps(new_list_dict)
        dict_to_redis_hset(conn, key, new_worker_list_dict)    

UPDATE_TASKS = [
    {
        'name': 'UpdateAliveList',
        'model_type': 'AI',
        'model_info_key': 'model_type_to_model_to_worker_list',
        'worker_info':'model_type_to_worker_id_to_worker',
        'interval': 0.01,  # 20 minutes
        'enable': 1,
        'task_queue':None,
    },
]
SchedulerCls = BaseScheduler
default_tasks=UPDATE_TASKS
scheduler = SchedulerCls('UpdateAliveList',default_tasks)


#scheduler.schedule_all_right_now()
scheduler.schedule_with_delay()