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
from server.lib.nl.detection.types import RankingType
from server.lib.nl.fulfillment.base import add_chart_to_utterance
from server.lib.nl.fulfillment.base import populate_charts
from server.lib.nl.fulfillment.types import ChartVars
from server.lib.nl.fulfillment.types import PopulateState
import server.lib.nl.fulfillment.utils as futils


#
# For ranking across places, we should detect a ranking and contained-in
# classification in the current utterance.  For example, [counties with most rainfall],
# assuming california is in the context.
#
def populate(uttr: Utterance):
  # Get the RANKING classifications from the current utterance. That is what
  # let us infer this is ranking query-type.
  ranking_types = utils.get_ranking_types(uttr)
  place_type = utils.get_contained_in_type(uttr)
  if ranking_types and place_type:
    uttr.has_default_vars = _maybe_add_default_svs(uttr, ranking_types[0],
                                                   place_type)
    ranking_types = _maybe_remap_size(ranking_types)
    if populate_charts(
        PopulateState(uttr=uttr,
                      main_cb=_populate_cb,
                      place_type=place_type,
                      ranking_types=ranking_types)):
      return True
    else:
      uttr.has_default_vars = False
      uttr.counters.err('ranking-across-places_failed_populate_placetype',
                        place_type.value)

  return False


def _populate_cb(state: PopulateState, chart_vars: ChartVars,
                 places: List[Place], chart_origin: ChartOriginType) -> bool:
  logging.info('populate_cb for ranking_across_places')
  if not state.ranking_types:
    state.uttr.counters.err('ranking-across-places_failed_cb_norankingtypes', 1)
    return False
  if len(places) > 1:
    state.uttr.counters.err('ranking-across-places_failed_cb_toomanyplaces',
                            [p.dcid for p in places])
    return False
  if not state.place_type:
    state.uttr.counters.err('ranking-across-places_failed_cb_noplacetype', 1)
    return False
  if not chart_vars.svs and not chart_vars.event:
    state.uttr.counters.err('ranking-across-places_failed_cb_emptyvars', {
        'svs': chart_vars.svs,
        'event': chart_vars.event,
    })
    return False

  if chart_vars.event:
    chart_vars.response_type = "event chart"
    return add_chart_to_utterance(ChartType.EVENT_CHART, state, chart_vars,
                                  places, chart_origin)
  else:
    chart_vars.response_type = "ranking table"
    if not utils.has_map(state.place_type, places):
      chart_vars.skip_map_for_ranking = True
    if (state.uttr.has_default_vars or state.place_type in futils.SCHOOL_TYPES):
      chart_vars.include_percapita = False
    else:
      chart_vars.include_percapita = True
    if state.uttr.has_default_vars:
      # We exactly control the Vars in this case,
      # so line them all up in a single block.
      chart_vars.block_id = 1
    return add_chart_to_utterance(ChartType.RANKING_CHART, state, chart_vars,
                                  places, chart_origin)


def _maybe_add_default_svs(uttr, ranking_type, place_type):
  if uttr.svs:
    #
    # NOTE: The is_non_geo_place_type check is there for non-geo places
    # like schools which are not removed as stop-words for SV query.
    # For example, [how big are high schools] query, since we pass in
    # "high schools", they will indeed often match SVs.  So we let the
    # `BIG` / `SMALL` heuristic override.
    #   TODO: Find a better approach
    #
    if (ranking_type not in [RankingType.BIG, RankingType.SMALL] or
        not utils.is_non_geo_place_type(place_type)):
      return False
    uttr.counters.info('ranking-across-places_override_default_vars', '')
  uttr.svs = futils.get_default_vars(place_type)
  return True


def _maybe_remap_size(ranking_types):
  res = []
  for r in ranking_types:
    if r == RankingType.BIG:
      res.append(RankingType.HIGH)
    elif r == RankingType.SMALL:
      res.append(RankingType.SMALL)
    else:
      res.append(r)
  return res
