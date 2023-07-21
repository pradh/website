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

import logging
from typing import List

from server.lib.nl.common import utils
from server.lib.nl.common.utterance import ChartOriginType
from server.lib.nl.common.utterance import ChartType
from server.lib.nl.common.utterance import Utterance
from server.lib.nl.detection.types import Place
from server.lib.nl.fulfillment.base import add_chart_to_utterance
from server.lib.nl.fulfillment.base import populate_charts
from server.lib.nl.fulfillment.types import ChartVars
from server.lib.nl.fulfillment.types import PopulateState
import server.lib.nl.fulfillment.utils as futils


def populate(uttr: Utterance) -> bool:
  place_type = utils.get_contained_in_type(uttr)
  if not uttr.svs:
    uttr.svs = futils.get_default_vars(place_type)
    uttr.has_default_vars = True
  if populate_charts(
      PopulateState(uttr=uttr, main_cb=_populate_cb, place_type=place_type)):
    return True
  else:
    uttr.has_default_vars = False
    uttr.counters.err('containedin_failed_populate_placetype', place_type.value)
  return False


def _populate_cb(state: PopulateState, chart_vars: ChartVars,
                 contained_places: List[Place],
                 chart_origin: ChartOriginType) -> bool:
  logging.info('populate_cb for contained-in')

  if chart_vars.event:
    state.uttr.counters.err('containedin_failed_cb_events', 1)
    return False
  if not state.place_type:
    state.uttr.counters.err('containedin_failed_cb_missing_type', 1)
    return False
  if not chart_vars:
    state.uttr.counters.err('containedin_failed_cb_missing_chat_vars', 1)
    return False
  if not chart_vars.svs:
    state.uttr.counters.err('containedin_failed_cb_missing_svs', 1)
    return False
  if len(contained_places) > 1:
    state.uttr.counters.err('containedin_failed_cb_toomanyplaces',
                            contained_places)
    return False

  if (state.uttr.has_default_vars or state.place_type in futils.SCHOOL_TYPES):
    chart_vars.include_percapita = False
  else:
    chart_vars.include_percapita = True

  if (utils.has_map(state.place_type, contained_places) and
      not state.uttr.has_default_vars):
    chart_vars.response_type = "comparison map"
    add_chart_to_utterance(ChartType.MAP_CHART, state, chart_vars,
                           contained_places, chart_origin)
  else:
    if state.uttr.has_default_vars:
      chart_vars.ranking_count = 30
      chart_vars.block_id = 1

    chart_vars.skip_map_for_ranking = True
    add_chart_to_utterance(ChartType.RANKING_CHART, state, chart_vars,
                           contained_places, chart_origin)
  return True
