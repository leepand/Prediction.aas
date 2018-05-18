import falcon
import os
import sys
import time
import logging

from commons.src.load_balancer.worker_load_balancer import WorkerLoadBalancer
from model_workers_resource import ModelWorkersResource
from AIaas.router.predict import AIModelResource
from AIaas.router.AI_worker_client import AIWorkerClient
from commons.src.logging.setup_logging import setup_logging
from commons.src.elb.elb_resource import ElbResource

def loader():
    setup_logging()
    logger = logging.getLogger(__name__)
    logger.info("Starting Router...")

    start_time = int(time.time())
    load_balancer = WorkerLoadBalancer()


    model_workers_resource = ModelWorkersResource(load_balancer)

    AI_worker_client = AIWorkerClient(load_balancer)
    predict_resource = AIModelResource(AI_worker_client)

    elb_resource = ElbResource(start_time, load_balancer)

    # falcon.API instances are callable WSGI apps
    app = falcon.API()


    app.add_route('/v1/model_workers_map', model_workers_resource)
    app.add_route('/v1/AI_model/predict', predict_resource)
    app.add_route('/elb-healthcheck', elb_resource)

    return app

