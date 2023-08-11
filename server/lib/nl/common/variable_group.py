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

from typing import Dict, List

import server.services.datacommons as dc
from server.lib.nl.common import variable


def open_svgs(svgs: List[str], places: List[str]) -> Dict[str, variable.SV]:
  result = {}
  processed = set()
  _get_svg_info(svgs, places, processed, result)
  return result


def _get_svg_info(svgs, places, processed, result):
  resp = dc.get_variable_group_info(svgs, places, numEntitiesExistence=len(places))
  recurse_nodes = set()
  for data in resp.get('data', []):
    svg_id = data.get('node', '')
    if not svg_id:
      continue

    info = data.get('info', '')
    if not info:
      continue

    if svg_id in processed:
      continue
    processed.add(svg_id)

    for csv in info.get('childStatVars', []):
      if not csv.get('id'):
        continue
      result[csv['id']] = variable.parse_sv(csv['id'], csv.get('definition', ''))

    for csvg in info.get('childStatVarGroups', []):
      if not csvg.get('id'):
        continue
      recurse_nodes.add(csvg['id'])

  if recurse_nodes:
    _get_svg_info(list(recurse_nodes), places, processed, result)