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
from dataclasses import dataclass
import json
import os
from typing import Dict, List, Set

import datacommons as dc

#
#           |  1-P, 1-V  |  N-P, 1-V  |  1-P, N-V  |  N-P, N-V
# ----------|------------|------------|------------|-------------
#  Map      |            |     x      |            |
#  Gauge    |      x     |            |            |
#  Higlight |      x     |            |            |
#  Pie      |            |            |      x     |
#  Donut    |            |            |      x     |
#  Line     |      x     |     x      |      x     |     x
#  Ranking  |            |     x      |            |
#  V-Bar    |      x     |     x      |      x     |     x
#  H-Bar    |      x     |     x      |      x     |     x
#  V-St-Bar |            |            |      x     |     x
#  H-St-Bar |            |            |      x     |     x
#  V-Lol    |            |     x      |      x     |     x
#  H-Lol    |            |     x      |      x     |     x
#  V-St-Lol |            |            |      x     |     x
#  H-St-Lol |            |            |      x     |     x
#
# Scatter => N-P + 2-V
#

# Topic Cache JSON
_TOPIC_CACHE = '../../server/config/nl_page/topic_cache.json'
_SDG_TOPIC_CACHE = '../../server/config/nl_page/sdg_topic_cache.json'

# Generated charts dir
_OUT_DIR = 'output_urls'

# Existence file
_EXISTENCE_FILE = 'var_existence.csv'

API_ROOT = 'https://dev.datacommons.org/nodejs/chart-info'


def _fname(outdir: str, fno: int) -> str:
  return os.path.join(outdir, f'shard_{fno}.txt')


class UrlMaker:

  def __init__(self, outdir):
    self.next_fno = 1
    self.ncharts = 0
    self.total_charts = 0
    self.fp = None
    self.outdir = outdir
    self._new_file()

  def add(self, place: str, child_type: str, chart_spec: Dict,
          sv_spec: List[Dict]):
    self.fp.write(f'{API_ROOT}?'
                  f'place={place}&'
                  f'config={json.dumps(chart_spec)}&'
                  f'svSpec={json.dumps(sv_spec)}&'
                  f'enclosedPlaceType={child_type}\n')

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


@dataclass
class Context:
  place: str
  child_type: str
  child_places: List[str]
  maker: UrlMaker
  topic_map: Dict[str, Dict]
  var2places: Dict[str, Set[str]]


def _composite(v: str) -> bool:
  return v.startswith('dc/topic/') or v.startswith('dc/svpg/')


def _exists(vars: List[str], ctx: Context, parent: bool) -> List[str]:
  ret = []
  for v in vars:
    pl = ctx.var2places.get(v)
    if not pl:
      continue
    if parent:
      if ctx.place in pl:
        ret.append(v)
    else:
      for c in ctx.child_places:
        if c in pl:
          ret.append(v)
          break
  return ret


def _sv_spec(vars: List[str], ctx: Context):
  sv_spec = []
  for v in vars[:5]:
    sv_spec.append({
        'statVar': v,
        'name': ctx.topic_map.get(v, {}).get('n', v),
    })
  return sv_spec


#
# Helper functions to generate the chart configs.
#
def _map(v: str, title: str, ctx: Context):
  vs = _exists([v], ctx, parent=True)
  if not vs:
    return
  v = vs[0]
  config = {'title': title, 'type': 'MAP'}
  ctx.maker.add(ctx.place, ctx.child_type, config, _sv_spec([v], ctx))


def _line(vars: List[str], title: str, ctx: Context):
  vars2 = _exists(vars, ctx, parent=True)
  if vars2:
    spec = _sv_spec(vars2, ctx)
    config = {
        'title': title,
        'type': 'LINE',
    }
    ctx.maker.add(ctx.place, '', config, spec)

  vars2 = _exists(vars, ctx, parent=False)
  if vars2:
    spec = _sv_spec(vars2, ctx)

    config = {
        'title': title,
        'type': 'LINE',
    }
    ctx.maker.add(ctx.place, ctx.child_type, config, spec)

    config['comparisonPlaces'] = ctx.child_places
    ctx.maker.add(ctx.place, '', config, spec)


def _bar(vars: List[str],
         title: str,
         ctx: Context,
         stacked: bool = False,
         lollipop: bool = False,
         horizontal: bool = False):

  def _opts(config: Dict, desc: bool):
    if stacked:
      config['barTileSpec']['stacked'] = True
    if lollipop:
      config['barTileSpec']['useLollipop'] = True
    if horizontal:
      config['barTileSpec']['horizontal'] = True
    if desc:
      config['barTileSpec']['sort'] = 'DESCENDING'
    else:
      config['barTileSpec']['sort'] = 'ASCENDING'
    return config

  vars2 = _exists(vars, ctx, parent=True)
  if vars2:
    spec = _sv_spec(vars2, ctx)
    config = {
        'title': title,
        'type': 'BAR',
        'comparisonPlaces': [ctx.place],
        'barTileSpec': {},
    }
    ctx.maker.add(ctx.place, '', _opts(config, desc=True), spec)

  vars2 = _exists(vars, ctx, parent=False)
  if vars2:
    spec = _sv_spec(vars2, ctx)
    config = {
        'title': title,
        'type': 'BAR',
        'barTileSpec': {},
    }
    ctx.maker.add(ctx.place, ctx.child_type, _opts(config, desc=True), spec)

  vars2 = _exists(vars, ctx, parent=False)
  if vars2:
    spec = _sv_spec(vars2, ctx)
    config = {
        'title': title,
        'type': 'BAR',
        'comparisonPlaces': ctx.child_places,
        'barTileSpec': {},
    }
    ctx.maker.add(ctx.place, '', _opts(config, desc=False), spec)


#
# Overall logic to pick charts.
#
def generate_charts(vars: List[str], title: str, ctx: Context):
  for v in vars:
    vname = ctx.topic_map.get(v, {}).get('n', '')
    _map(v, vname, ctx)
    if len(vars) > 1:
      _line([v], vname, ctx)
      _bar([v], vname, ctx, horizontal=False)
      _bar([v], vname, ctx, horizontal=True)
      _bar([v], vname, ctx, lollipop=True, horizontal=False)
      _bar([v], vname, ctx, lollipop=True, horizontal=True)

  _line(vars, title, ctx)

  _bar(vars, title, ctx, horizontal=False)
  _bar(vars, title, ctx, horizontal=True)
  _bar(vars, title, ctx, lollipop=True, horizontal=False)
  _bar(vars, title, ctx, lollipop=True, horizontal=True)

  if len(vars) > 1:
    _bar(vars, title, ctx, stacked=True, horizontal=False)
    _bar(vars, title, ctx, stacked=True, horizontal=True)
    _bar(vars, title, ctx, stacked=True, horizontal=False, lollipop=True)
    _bar(vars, title, ctx, stacked=True, horizontal=True, lollipop=True)


def generate(topic: str, ctx: Context):
  vars = []
  for v in ctx.topic_map.get(topic, {}).get('ml', []):
    if not _composite(v):
      vars.append(v)
  if vars:
    generate_charts(vars, ctx.topic_map[topic]['n'], ctx)

  for v in ctx.topic_map.get(topic, {}).get('rl', []):
    if _composite(v):
      continue
    generate_charts([v], ctx.topic_map.get(v, {}).get('n', v), ctx)


def load_topics(topic_cache_file: str):
  with open(topic_cache_file, 'r') as fp:
    cache = json.load(fp)

  all_vars = set()
  out_map = {}
  for node in cache['nodes']:
    dcid = node['dcid'][0]
    name = node['name'][0]
    if 'relevantVariableList' in node:
      vars = node['relevantVariableList']
      out_map[dcid] = {'n': name, 'rl': vars}
    else:
      vars = node['memberList']
      out_map[dcid] = {'n': name, 'ml': vars}
    for v in vars:
      if not _composite(v):
        all_vars.add(v)

  # Get all the names of variables.
  all_vars = sorted(list(all_vars))
  for id, names in dc.get_property_values(all_vars, 'name').items():
    assert id not in out_map, id
    if names:
      out_map[id] = {'n': names[0]}
  with open(os.path.join(_OUT_DIR,
                         os.path.basename(topic_cache_file) + '.csv'),
            'w') as fp:
    fp.write('\n'.join(all_vars) + '\n')
  return out_map


def main():
  var2places = {}
  with open(_EXISTENCE_FILE) as fp:
    for row in csv.DictReader(fp):
      v = row['Var']
      p = row['Place']
      if row['Var'] not in var2places:
        var2places[v] = set()
      var2places[v].add(p)

  url_maker = UrlMaker(_OUT_DIR)
  ntopics = 0

  topic_map = load_topics(_TOPIC_CACHE)
  for pl, ct, cpl in [
      ('country/USA', 'State',
       ['geoId/06', 'geoId/36', 'geoId/08', 'geoId/48', 'geoId/27']),
      ('geoId/06', 'County',
       ['geoId/06085', 'geoId/06061', 'geoId/06029', 'geoId/06025']),
      ('Earth', 'Country', [
          'country/USA', 'country/IND', 'country/IRN', 'country/NGA',
          'country/BRA'
      ]),
  ]:
    for t in sorted(topic_map.keys()):
      if not _composite(t):
        continue
      ntopics += 1
      generate(
          t,
          Context(place=pl,
                  child_type=ct,
                  child_places=cpl,
                  maker=url_maker,
                  topic_map=topic_map,
                  var2places=var2places))

  topic_map = load_topics(_SDG_TOPIC_CACHE)
  for pl, ct, cpl in [
      ('Earth', 'Country', [
          'country/USA', 'country/IND', 'country/IRN', 'country/NGA',
          'country/BRA'
      ]),
  ]:
    for t in sorted(topic_map.keys()):
      if not _composite(t):
        continue
      ntopics += 1
      generate(
          t,
          Context(place=pl,
                  child_type=ct,
                  child_places=cpl,
                  maker=url_maker,
                  topic_map=topic_map,
                  var2places=var2places))

  url_maker.close()
  print(
      f'Processed {ntopics} topics and produced {url_maker.total_charts} charts!'
  )


if __name__ == "__main__":
  os.makedirs(_OUT_DIR, exist_ok=True)
  main()
