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

from absl import app
from absl import flags
import glob
import json
from multiprocessing import current_process
from multiprocessing import Pool
import os
import sys
import time
from typing import List

import requests

_IN_PATTERN = flags.DEFINE_string('in_pattern', 'output/urls/shard_*.txt',
                                  'Input directory')
_OUT_DIR = flags.DEFINE_string('out_dir', 'output/charts',
                               'Output directory')
_INCLUDE_URL = flags.DEFINE_bool('include_url_in_result',
                                 False, '')
_MIN_SKIP = flags.DEFINE_integer('min_to_skip', 30, '')


_NPROC = 30


def _lines(fpath: str, count_only: bool) -> List[str]:
  lines = []
  nlines = 0
  with open(fpath) as fp:
    for ln in fp.readlines():
      ln = ln.strip()
      if not ln:
        continue
      nlines += 1
      if not count_only:
        lines.append(ln)
  return lines, nlines


def gen(fpath: str):
  urls, _ = _lines(fpath, count_only=False)
  name = os.path.basename(fpath)
  name = name.replace('.txt', '.jsonl')
  newf = os.path.join(_OUT_DIR.value, name)

  # Load from prior checkpoint
  idx = 0
  if os.path.isfile(newf):
    _, idx = _lines(newf, count_only=True)

  if len(urls) - idx <= _MIN_SKIP.value:
    # Consider this good enough.
    print(f'Already full')
    return

  with open(newf, 'a') as fp:
    start = time.time()
    jsons = []
    while idx < len(urls):
      try:
        resp = requests.get(urls[idx]).json()
        if not resp:
          print(f'Got empty for {urls[idx]}')
          idx += 1
          continue
        if _INCLUDE_URL.value:
          out_json = {
            'url': urls[idx],
            'result': resp
          }
        else:
          out_json = resp
        jsons.append(out_json)
      except Exception as e:
        print(f'Exception accessing {urls[idx]}: {e}')
        idx += 1
        continue

      # Checkpoint!
      if idx and idx % 50 == 0:
        end = time.time()
        print(f'{current_process().name}: checkpointing {end - start}')
        for j in jsons:
          fp.write(f'{json.dumps(j)}\n')
        jsons = []
        start = end

      idx += 1

    # Final write
    for j in jsons:
      fp.write(f'{json.dumps(j)}\n')


def parse_flags():
  flags.FLAGS(sys.argv)


def main(_):
  os.makedirs(_OUT_DIR.value, exist_ok=True)
  files = []
  for f in glob.glob(_IN_PATTERN.value):
    files.append(f)

  pool = Pool(_NPROC, initializer=parse_flags)
  pool.map(gen, files)


if __name__ == "__main__":
  app.run(main)
