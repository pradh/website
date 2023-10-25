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
import os


# Generated charts dir
_URL_NL_OUT_DIR = 'output/nl/urls'
_URL_STAT_OUT_DIR = 'output/stat/urls'


# Existence file
_EXISTENCE_FILE = 'query_var_existence.csv'

NL_API_ROOT = 'https://dev.datacommons.org/nodejs/query'

DATA_API_ROOT = 'https://api.datacommons.org/v2/observation?key=AIzaSyCTI4Xz-UW_G2Q2RfknhcfdAnTHq5X5XuI&date=LATEST&select=entity&select=variable&select=value&select=date'

def _fname(outdir: str, fno: int) -> str:
  return os.path.join(outdir, f'shard_{fno}.txt')


def _nl_url(var_name: str, place_name: str):
  query = f'{var_name.lower()} in {place_name.lower()}'
  query = query.replace(' ', '+')
  return f'{NL_API_ROOT}?q={query}'


def _stat_url(var: str, place: str):
  return f'{DATA_API_ROOT}&entity.dcids={place}&variable.dcids={var}'
  return 


class UrlMaker:

  def __init__(self, outdir):
    self.next_fno = 1
    self.ncharts = 0
    self.total_charts = 0
    self.fp = None
    self.outdir = outdir
    self._new_file()

  def add(self, url: str):
    self.fp.write(f'{url}\n')
    self.total_charts += 1
    self.ncharts += 1
    if self.ncharts >= 100:
      self._new_file()

  def close(self):
    if self.fp:
      self.fp.close()

  def _new_file(self):
    self.close()
    self.fp = open(_fname(self.outdir, self.next_fno), 'w')
    self.next_fno += 1
    self.ncharts = 0


def urls():
  nl_url_maker = UrlMaker(_URL_NL_OUT_DIR)
  stat_url_maker = UrlMaker(_URL_STAT_OUT_DIR)
  vars = set()
  with open(_EXISTENCE_FILE) as fp:
    for row in csv.DictReader(fp):
      v = row['Var']
      p = row['Place']
      vn = row['VarName']
      pn = row['PlaceName']
      if v.startswith('dc/topic/'):
        continue
      if p not in ['Earth', 'asia', 'country/USA', 'country/IND',
                   'geoId/06', 'geoId/48', 'geoId/06085',
                   'geoId/48009', 'geoId/4819000', 'geoId/0644000']:
        continue
      nl_url_maker.add(_nl_url(vn, pn))
      stat_url_maker.add(_stat_url(v, p))
      vars.add(v)

  nl_url_maker.close()
  stat_url_maker.close()
  print(
      f'Processed {len(vars)} vars and produced {nl_url_maker.total_charts}'
      f' queries in {_URL_NL_OUT_DIR} and {_URL_STAT_OUT_DIR}!'
  )


if __name__ == "__main__":
  os.makedirs(_URL_NL_OUT_DIR, exist_ok=True)
  os.makedirs(_URL_STAT_OUT_DIR, exist_ok=True)
  urls()
