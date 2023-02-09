# Copyright 2023 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import json
import logging
import multiprocessing
import os
import sys

from flask_testing import LiveServerTestCase
import requests

from nl_server.__init__ import create_app as create_nl_app
from server.__init__ import create_app as create_web_app
import server.lib.util as libutil

# Explicitly set multiprocessing start method to 'fork' so tests work with
# python3.8+ on MacOS.
# https://docs.python.org/3/library/multiprocessing.html#contexts-and-start-methods
# This code must only be run once per execution.
if sys.version_info >= (3, 8) and sys.platform == "darwin":
  multiprocessing.set_start_method("fork")
  os.environ['no_proxy'] = '*'

_dir = os.path.dirname(os.path.abspath(__file__))

_NL_SERVER_URL = 'http://127.0.0.1:6060'

_TEST_MODE = os.environ['TEST_MODE']

_TEST_DATA = 'test_data'


class IntegrationTest(LiveServerTestCase):

  @classmethod
  def setUpClass(cls):

    def start_nl_server(app):
      app.run(port=6060, debug=False, use_reloader=False, threaded=True)

    nl_app = create_nl_app()
    # Create a thread that will contain our running server
    cls.proc = multiprocessing.Process(target=start_nl_server,
                                       args=(nl_app,),
                                       daemon=True)
    cls.proc.start()
    libutil.check_backend_ready([_NL_SERVER_URL + '/healthz'])

  @classmethod
  def tearDownClass(cls):
    cls.proc.terminate()

  def create_app(self):
    """Returns the Flask Server running Data Commons."""
    return create_web_app()

  # TODO: Validate contexts as well eventually.
  def run_sequence(self, test_dir, queries):
    ctx = {}
    for i, q in enumerate(queries):
      print('Issuing ', test_dir, f'query[{i}]', q)
      resp = requests.post(self.get_server_url() + f'/nlnext/data?q={q}',
                           json={
                               'contextHistory': ctx
                           }).json()

      ctx = resp['context']
      dbg = resp['debug']
      resp['debug'] = {}
      resp['context'] = {}
      json_file = os.path.join(_dir, _TEST_DATA, test_dir, f'query_{i + 1}',
                               'chart_config.json')
      if _TEST_MODE == 'write':
        json_dir = os.path.dirname(json_file)
        if not os.path.isdir(json_dir):
          os.makedirs(json_dir)
        with open(json_file, 'w') as infile:
          infile.write(json.dumps(resp, indent=2))

        dbg_file = os.path.join(json_dir, 'debug_info.json')
        with open(dbg_file, 'w') as infile:
          infile.write(json.dumps(dbg, indent=2))
      else:
        with open(json_file, 'r') as infile:
          expected = json.load(infile)
          expected['debug'] = {}
          expected['context'] = {}
          a, b = (
              json.dumps(resp, sort_keys=True, indent=2),
              json.dumps(expected, sort_keys=True, indent=2),
          )
          self.maxDiff = None
          self.assertEqual(a, b)

  def test_textbox_sample(self):
    # This is the sample advertised in our textbox
    self.run_sequence('textbox_sample', ['family earnings in california'])

  def test_demo_feb2023(self):
    self.run_sequence('demo_feb2023', [
        'What are the projected temperature extremes across California',
        'Where were the major fires in the last year',
        'Tell me about Placer County',
        'What were the most common jobs there',
        'Which jobs have grown the most',
        'What are the most common health issues there',
        'Which counties in california have the highest levels of blood pressure',
        'Which counties in the US have the highest levels of blood pressure',
        'How does this correlate with income',
    ])
