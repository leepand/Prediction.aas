#
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

import sys
import os

import common_client

from commons.src.logging.setup_logging import setup_logging
import logging



from commons.src.load_balancer.worker_load_balancer import WorkerLoadBalancer
from commons.src.load_balancer.worker_load_balancer import WorkerInfo
from commons.src.config import config_loader
from commons.src.load_balancer.worker_info import WorkerInfo

import random


class AIflyError(Exception):
    pass

class AIWorkerClient:
    def __init__(self, load_balancer):
        setup_logging()
        self.logger = logging.getLogger(__name__)
        self.load_balancer = load_balancer
        self.logger.info("load balancer inited...")
        self.worker_connections = {}
        self.logger.info("AIWorkerClient Inited...")
        # self.load_balancer = WorkerLoadBalancer(model_to_worker_config_path)
        self.worker_to_AI_client_map = {}

        worker_id_to_worker_map = self.load_balancer.get_all_workers("AI")

        # Build model to AI client map
        #worker_id_to_worker_map:"{u'localhost-9091-1': <commons.src.load_balancer.worker_info.WorkerInfo instance at 0x1106af908>, u'localhost-9092-2': }"
        if worker_id_to_worker_map:
            for worker_id, worker in worker_id_to_worker_map.iteritems():               
                self.worker_to_AI_client_map[worker_id] = self.make_clients(worker)

    def make_clients(self, worker):
        """

        Args:
            host:
            port:

        Returns: http client for the worker at the given host and port

        """
        try:
            aiurl='http://%s:%d' % (worker.host,worker.port)
            client = common_client.Client(aiurl)
            return client
        except ConnectionError:
            raise AIflyError('Unable to connect to the server, please try again later.')

    def predict(self, prediction_input):
        """
        AI prediction
        Args:
            prediction_input: PredictionInput
        Returns: PredictionOutput
        """
        self.logger.info("Caffe predict has been called..")
        worker = self.load_balancer.choose_worker("AI", prediction_input.model_id)

        self.logger.debug('Chosen worker_id: %s for predict ', str(worker.global_worker_id))

        if worker.global_worker_id in self.worker_to_AI_client_map:
            client= self.worker_to_AI_client_map[worker.global_worker_id]
        else:
            client = make_clients(worker)
            self.worker_to_AI_client_map[worker.global_worker_id] = client

        po = None
        retry_count = 3
        trial_number = 0
        while trial_number < retry_count:
            trial_number += 1
            try:
                predict=prediction_input.model_id
                po = client.predict(prediction_input.data)
            except Exception as e:
                po = 'None'
                po.bo.status = 'Failure'
                self.logger.error('Predict has failed.. ', exc_info=True)
            else:
                break
            finally:
                self.logger.error('Predict has failed.. ', exc_info=True)

        return po