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

import csv
import glob
import json
from multiprocessing import current_process
from multiprocessing import Pool
import os
import time
from typing import List

import requests

_NPROC = 10
_IN_PATTERN = 'output_urls/shard_*.txt'
_OUT_DIR = 'output_charts'


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
  newf = os.path.join(_OUT_DIR, name)

  # Load from prior checkpoint
  idx = 0
  if os.path.isfile(newf):
    _, idx = _lines(newf, count_only=True)
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
        jsons.append(resp)
      except Exception as e:
        print(f'Exception accessing {urls[idx]}: {e}')
        idx += 1
        continue

      # Checkpoint!
      if idx and idx % 10 == 0:
        end = time.time()
        print(f'{current_process().name}: checkpointing {end - start}')
        for j in jsons:
          fp.write(f'{j}\n')
        jsons = []
        start = end

      idx += 1


def main():
  files = []
  for f in glob.glob(_IN_PATTERN):
    files.append(f)

  pool = Pool(_NPROC)
  pool.map(gen, files)


if __name__ == "__main__":
  os.makedirs(_OUT_DIR, exist_ok=True)
  main()
