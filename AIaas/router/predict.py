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

import falcon
import json
import sys
import logging


from AI_worker_client import AIWorkerClient
class prediction_input:
    """
    Contains input details and model_id and data
    """
    def __init__(self, model_id, data,model_type):
        self.model_id = model_id
        self.data = data
        self.local_worker_id = local_worker_id
        self.model_type=model_type


class AIModelResource(object):
    def __init__(self, AI_worker_client):
        self.AI_worker_client=AI_worker_client
        self.logger = logging.getLogger(__name__)
        self.logger.info("Predict Inited...")


    def on_get(self, req, resp):
        """Handles GET requests"""
        resp.status = falcon.HTTP_200  # This is the default status
        resp.body = ('\nFalcon is awesome! \n')

    def on_post(self, req, resp):
        payload = json.loads(req.stream.read())
        if ('data' in payload.keys()) and ('modelId' in payload.keys()):
            prediction_input.data = payload['data']
            prediction_input.model_id = payload['modelId']
            prediction_input.model_type= "AI"
        else:
            resp.status = falcon.HTTP_400
            raise falcon.HTTPBadRequest("Bad Request", "Url and(or) modelId missing in the payload")

        po = self.AI_worker_client.predict(prediction_input)

        if po.status == 'Success':
            resp.status = falcon.HTTP_200
            resp.body = (str(po.result))
        elif po.status == 'Failure':
            resp.body = json.dumps({'status': 'Failure', 'message' : 'Error occurred'})
            resp.status = falcon.HTTP_500
            raise falcon.HTTPInternalServerError('Internal Server Error', 'Predict failed! ')