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
"""Module for NL page data spec"""

import logging
from typing import List

from server.lib.nl import utils
from server.lib.nl.detection import Detection
from server.lib.nl.detection import Place
from server.lib.nl.fulfillment import context
import server.lib.nl.fulfillment.handlers as handlers
from server.lib.nl.utterance import ChartSpec
from server.lib.nl.utterance import QueryType
from server.lib.nl.utterance import Utterance

# We will ignore SV detections that are below this threshold
_SV_THRESHOLD = 0.5


#
# Compute a new Utterance given the classifications for a user query
# and past utterances.
#
def fulfill(query_detection: Detection,
            currentUtterance: Utterance) -> Utterance:

  filtered_svs = filter_svs(query_detection.svs_detected.sv_dcids,
                            query_detection.svs_detected.sv_scores)

  # Construct Utterance datastructure.
  uttr = Utterance(prev_utterance=currentUtterance,
                   query=query_detection.original_query,
                   query_types=[],
                   detection=query_detection,
                   places=[],
                   classifications=query_detection.classifications,
                   svs=filtered_svs,
                   chartCandidates={},
                   rankedCharts=[],
                   answerPlaces=[])
  uttr.counters['filtered_svs'] = filtered_svs

  # Add detected places.
  if (query_detection.places_detected):
    uttr.places.append(query_detection.places_detected.main_place)

  query_types = [handlers.first_query_type(uttr)]
  while query_types[-1] != None:
    if fulfill_query_type(uttr, query_types[-1]):
      # TODO: Check if we can avoid looping to further query_types
      # if we got charts with current top SV + place.
      pass
    query_types.append(handlers.next_query_type(query_types))

  rank_charts(uttr)
  return uttr


def fulfill_query_type(uttr: Utterance, query_type: QueryType) -> bool:
  logging.info('Handled query_type: %d', query_type.value)
  # Reset previous state
  uttr.query_types.append(query_type)
  uttr.chartCandidates[query_type] = []

  # If we could not detect query_type from user-query, infer from past context.
  if (query_type == QueryType.UNKNOWN):
    uttr.query_types[-1] = context.query_type_from_context(uttr)

  found = False

  # Each query-type has its own handler. Each knows what arguments it needs and
  # will call on the *_from_context() routines to obtain missing arguments.
  handler = handlers.QUERY_HANDLERS.get(query_type, None)
  if handler:
    found = handler.module.populate(uttr)
    utils.update_counter(uttr.counters, 'processed_fulfillment_types',
                         handler.module.__name__.split('.')[-1])

  return found


_MAX_CHARTS = 10


#
# Rank candidate charts in the given Utterance.
#
def rank_charts(uttr: Utterance):
  for query_type, charts in uttr.chartCandidates.items():
    for chart in charts:
      logging.info("Chart[%d]: %s %s\n" %
                   (query_type.value, chart.places, chart.svs))

  s_and_p_candidates = context.get_all_svs_and_places(uttr)
  for scand in s_and_p_candidates:
    if not scand.svs:
      continue
    for pcand in s_and_p_candidates:
      if not pcand.places:
        continue
      # Now we have a pair of SVs + Places
      spcand = context.SVsAndPlaces(svs=scand.svs, places=pcand.places)
      if _rank_charts_for_svs_and_places(uttr, spcand):
        return

  # Not really found anything useful.
  # Just add up to _NUM_MAX_CHARTS charts.
  for query_type in uttr.query_types:
    for candidate in uttr.chartCandidates[query_type]:
      uttr.rankedCharts.append(candidate)
      if len(uttr.rankedCharts) >= _MAX_CHARTS:
        return


def _rank_charts_for_svs_and_places(uttr: Utterance,
                                    s_and_p: context.SVsAndPlaces) -> bool:
  for query_type in uttr.query_types:
    chart_candidates = uttr.chartCandidates[query_type]
    found = False
    for candidate in chart_candidates:
      if (_has_var_overlap(s_and_p.svs, candidate) and
          _has_place_overlap(s_and_p.places, candidate.places)):
        found = True
        uttr.rankedCharts.append(candidate)
    if found:
      return True
  return False


def _has_var_overlap(svs_from_detection: List[str], cspec: ChartSpec) -> bool:
  if cspec.event:
    # We must have already checked event-type classification.
    return True
  if cspec.attr['source_topic']:
    # If there's a source-topic we must match that.
    svs_from_cspec = [cspec.attr['source_topic']]
  else:
    svs_from_cspec = cspec.svs
  for sv1 in svs_from_detection:
    for sv2 in svs_from_cspec:
      if sv1 == sv2:
        return True
  return False


def _has_place_overlap(l1: List[Place], l2: List[Place]):
  for p1 in l1:
    for p2 in l2:
      if p1.dcid == p2.dcid:
        return True
  return False


# Filter out SVs that are below a score.
#
def filter_svs(sv_list: List[str], sv_score: List[float]) -> List[str]:
  # this functionality should be moved to detection.
  i = 0
  ans = []
  while (i < len(sv_list)):
    if (sv_score[i] >= _SV_THRESHOLD):
      ans.append(sv_list[i])
    i = i + 1
  return ans
