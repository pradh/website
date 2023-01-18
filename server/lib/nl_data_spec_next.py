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

from dataclasses import dataclass
from typing import Dict, List
import logging
from enum import Enum

from lib.nl_detection import ClassificationType, Detection, NLClassifier, Place, ContainedInPlaceType, ContainedInClassificationAttributes, RankingType, RankingClassificationAttributes
from lib import nl_variable, nl_topic
from lib.nl_utterance import Utterance, ChartOriginType, ChartSpec, ChartType, CNTXT_LOOKBACK_LIMIT
import services.datacommons as dc

# We will ignore SV detections that are below this threshold
SV_THRESHOLD = 0.5

# TODO: If we get the SV from context and the places are different, then old code performs
#       comparison.
# 
def compute(query_detection: Detection, currentUtterance: Utterance):
  uttr = Utterance(prev_utterance=currentUtterance,
                   query=query_detection.original_query,
                   query_type=query_detection.query_type,
                   detection=query_detection,
                   places=[],
                   classifications=query_detection.classifications,
                   svs=filterSVs(query_detection.svs_detected.sv_dcids,                                 
                                 query_detection.svs_detected.sv_scores),
                   chartCandidates=[],
                   rankedCharts=[],
                   answerPlaces=[])

  if (uttr.query_type == ClassificationType.UNKNOWN):
    uttr.query_type = queryTypeFromContext(uttr)
    
  if (query_detection.places_detected):
    uttr.places.append(query_detection.places_detected.main_place)


# each of these has its own handler. Each knows what arguments it needs and will
# call on context routines to obtain missing arguments
  if (uttr.query_type == ClassificationType.SIMPLE):
    populateSimple(uttr)
  elif (uttr.query_type == ClassificationType.COMPARE):
    populateCompare(uttr)
  elif (uttr.query_type == ClassificationType.CONTAINED_IN):
    populateContainedIn(uttr)
  elif (uttr.query_type == ClassificationType.RANKING):
    populateRanking(uttr)

  rankCharts(uttr)
  return uttr


# Handler for simple charts  
# TODO: Change this to use generic handlers

def populateSimple(uttr):
  for pl in uttr.places:
    if (populateSimpleInt(uttr, pl)):
        return
        
  for pl in placesFromContext(uttr):
    if (populateSimpleInt(uttr, pl)):
        return


def populateSimpleInt(uttr, place):
  if (len(uttr.svs) > 0):
    foundCharts = addSimpleCharts(place, uttr.svs, uttr)
    if (foundCharts):
      return True
  for svs in svsFromContext(uttr):
    foundCharts = addSimpleCharts(place, svs, uttr)
    if (foundCharts):
        return True
  
  # If NO SVs were found, then this is a OVERVIEW chart.
  addOneChartToUtterance(ChartType.PLACE_OVERVIEW, uttr, [], [place], ChartOriginType.PRIMARY_CHART)
  return False


# TODO: Coalesce all the SV existence calls
def addSimpleCharts (place, svs, uttr):
  print("Add line chart %s %s" % (place.name, svs))
  found = False
  for rank, sv in enumerate(svs):
    expanded_svs_list = svgOrTopicToSVs(sv, rank) 
    for svs in expanded_svs_list:
      svs = svsExistForPlaces([place.dcid], svs)[place.dcid]
      if svs:
        if (addOneChartToUtterance(ChartType.TIMELINE_CHART, uttr, svs, [place], ChartOriginType.PRIMARY_CHART)):
          found = True

  sv2extensions = nl_variable.extend_svs(svs)
  for sv, extended_svs in sv2extensions.items():
    extended_svs = svsExistForPlaces([place.dcid], extended_svs)[place.dcid]
    if extended_svs:
      if (addOneChartToUtterance(ChartType.TIMELINE_CHART, uttr, extended_svs, [place],  ChartOriginType.SECONDARY_CHART)):
        found = True
  return found


# Handlers for containedInPlace 

def populateContainedIn(uttr):
  classifications = classificationsOfTypeFromContext(uttr, ClassificationType.CONTAINED_IN)
  for classification in classifications:
    if not classification or not isinstance(classification.attributes, ContainedInClassificationAttributes):
      continue
    place_type = classification.attributes.contained_in_place_type
    if populateCharts(uttr, populateContainedInCb, fallbackContainedInCb, place_type=place_type):
      return True
  place_type = ContainedInPlaceType.COUNTY  # poor default. should do this based on main place
  return populateCharts(uttr, populateContainedInCb, fallbackContainedInCb, place_type=place_type)


def populateContainedInCb(uttr, svs, containing_place, chart_origin, place_type, _):
  if not place_type:
    return False
  if len(svs) > 1:
    # We don't handle peer group SVs
    return False
  addOneChartToUtterance(ChartType.MAP_CHART, uttr, svs, [containing_place], chart_origin, place_type)
  return True


def fallbackContainedInCb(uttr, containing_place, chart_origin, place_type, _):
  # TODO: Poor choice, do better.
  sv = "Count_Person"
  return populateContainedInCb(uttr, [sv], containing_place, chart_origin, place_type, _)


# Handlers for Ranking

def populateRanking(uttr):
  # Get all the classifications in the context.
  ranking_classifications = classificationsOfTypeFromContext(uttr, ClassificationType.RANKING)
  contained_classifications = classificationsOfTypeFromContext(uttr, ClassificationType.CONTAINED_IN)

  # Loop in order until we find success.
  for ranking_classification in ranking_classifications:
    if not ranking_classification or not isinstance(ranking_classification.attributes, RankingClassificationAttributes):
      continue
    if not ranking_classification.attributes.ranking_type:
      continue
    ranking_type = ranking_classification.attributes.ranking_type[0]
    for contained_classification in contained_classifications:
      if not contained_classification or not isinstance(contained_classification.attributes, ContainedInClassificationAttributes):
        continue
      place_type = contained_classification.attributes.contained_in_place_type
      if populateCharts(uttr, populateRankingCb, fallbackRankingCb, place_type=place_type, ranking_type=ranking_type):
        return True

  # Fallback
  ranking_type = RankingType.HIGH
  place_type = ContainedInPlaceType.COUNTY
  return populateCharts(uttr, populateRankingCb, fallbackRankingCb, place_type=place_type, ranking_type=ranking_type)


def populateRankingCb(uttr, svs, containing_place, chart_origin, place_type, ranking_type):
  if not place_type or not ranking_type:
    return False

  if len(svs) > 1:
    # We don't handle peer group SVs
    return False
  addOneChartToUtterance(ChartType.RANKING_CHART, uttr, svs, [containing_place], chart_origin, place_type, ranking_type)
  return True


def fallbackRankingCb(uttr, containing_place, chart_origin, place_type, ranking_type):
  # TODO: Poor choice, do better.
  sv = "Count_Person"
  return populateRankingCb(uttr, [sv], containing_place, chart_origin, place_type, ranking_type)


# Generic processors that invoke above callbacks

def populateCharts(uttr, main_cb, fallback_cb, place_type=None, ranking_type=None):
  for pl in uttr.places:
    if (populateChartsForPlace(uttr, pl, main_cb, fallback_cb, place_type, ranking_type)):
        return True
  for pl in placesFromContext(uttr):
    if (populateChartsForPlace(uttr, pl, main_cb, fallback_cb, place_type, ranking_type)):
        return True
  return False


def populateChartsForPlace(uttr, place, main_cb, fallback_cb, place_type, ranking_type):
  if (len(uttr.svs) > 0):
    foundCharts = addCharts(place, uttr.svs, uttr, main_cb, place_type, ranking_type)
    if foundCharts:
      return True
  for svs in svsFromContext(uttr):
    foundCharts = addCharts(place, svs, uttr, main_cb, place_type, ranking_type)
    if foundCharts:
        return True
  return fallback_cb(uttr, place, ChartOriginType.PRIMARY_CHART, place_type, ranking_type)


# TODO: Do existence check for child places
def addCharts(place, svs, uttr, callback, place_type, ranking_type):
  print("Add chart %s %s" % (place.name, svs))

  # If there is a child place_type, use a child place sample.
  place_to_check = place.dcid
  if place_type:
    place_to_check = _sample_child_place(place.dcid, place_type)

  found = False
  for rank, sv in enumerate(svs):
    expanded_svs_list = svgOrTopicToSVs(sv, rank) 
    for svs in expanded_svs_list:
      svs = svsExistForPlaces([place_to_check], svs)[place_to_check]
      if svs:
        if callback(uttr, svs, place, ChartOriginType.PRIMARY_CHART, place_type, ranking_type):
          found = True

  sv2extensions = nl_variable.extend_svs(svs)
  for sv, extended_svs in sv2extensions.items():
    extended_svs = svsExistForPlaces([place_to_check], extended_svs)[place_to_check]
    if extended_svs:
      if callback(uttr, extended_svs, place, ChartOriginType.SECONDARY_CHART, place_type, ranking_type):
        found = True
  return found


# More general utilities

def svsFromContext(uttr):
  ans = []
  prev_uttr_count = 0
  prev = uttr.prev_utterance
  while (prev and prev_uttr_count < CNTXT_LOOKBACK_LIMIT):
    ans.append(prev.svs)
    prev = prev.prev_utterance
    prev_uttr_count = prev_uttr_count + 1
  return ans

def placesFromContext(uttr):
  ans = []
  prev_uttr_count = 0
  prev = uttr.prev_utterance
  while (prev and prev_uttr_count < CNTXT_LOOKBACK_LIMIT):
    for place in prev.places:
      ans.append(place)
    prev = prev.prev_utterance
    prev_uttr_count = prev_uttr_count + 1
  return ans

def queryTypeFromContext(uttr):
  # this needs to be made a lot smarter ...
  prev_uttr_count = 0
  prev = uttr.prev_utterance
  while (prev and prev_uttr_count < CNTXT_LOOKBACK_LIMIT):
    if (not (prev.query_type == ClassificationType.UNKNOWN)):
        return prev.query_type
    prev = prev.prev_utterance
    prev_uttr_count = prev_uttr_count + 1
  return ClassificationType.SIMPLE


def classificationsOfTypeFromContext(uttr, ctype):
  result = []
  for cl in uttr.classifications:
    if (cl.type == ctype):
      result.append(cl)
  prev_uttr_count = 0
  prev = uttr.prev_utterance
  while (prev and prev_uttr_count < CNTXT_LOOKBACK_LIMIT):
    for cl in uttr.classifications:
      if (cl.type == ctype):
        result.append(cl)
    prev = prev.prev_utterance
    prev_uttr_count = prev_uttr_count + 1
  return result


# Returns a list of lists.  Inner list may contain a single SV or a peer-group of SVs.
def svgOrTopicToSVs(sv, rank):
  if isSV(sv):
    return [[sv]]
  if isTopic(sv):
    topic_vars = nl_topic.get_topic_vars(sv, rank)
    peer_groups = nl_topic.get_topic_peers(topic_vars)
    res = []
    for v in topic_vars:
      if v in peer_groups and peer_groups[v]:
        res.append(peer_groups[v])
      else:
        res.append([v])
    return res
  if isSVG(sv):
    svg2sv = nl_variable.expand_svg(sv)
    if sv in svg2sv:
      return svg2sv[sv]
  return []
          
      
def rankCharts (utterance):
  for chart in utterance.chartCandidates:
    print("Chart: %s %s\n" % (chart.places, chart.svs))
  utterance.rankedCharts = utterance.chartCandidates


# Returns a map of place DCID -> existing SVs.  The returned map always has keys for places.
def svsExistForPlaces(places, svs):
  # Initialize return value
  place2sv = {}
  for p in places:
    place2sv[p] = []

  if not svs:
    return place2sv

  sv_existence = dc.observation_existence(svs, places)
  if not sv_existence:
    logging.error("Existence checks for SVs failed.")
    return place2sv

  for sv in svs:
    for place, exist in sv_existence['variable'][sv]['entity'].items():
      if not exist:
        continue
      place2sv[place].append(sv)

  return place2sv


def isTopic(sv):
  return sv.startswith("dc/topic/")


def isSVG(sv):
  return sv.startswith("dc/g/")


def isSV(sv):
  return not (isTopic(sv) or isSVG(sv))


def addOneChartToUtterance(chart_type, utterance, svs, places, primary_vs_secondary, place_type=None, ranking_type=None):
  if place_type:
    place_type = place_type.value
  ch = ChartSpec(chart_type=chart_type,
                 svs=svs,
                 places=places,
                 utterance=utterance,
                 attr={"class" : primary_vs_secondary, "place_type" : place_type, "ranking_type": ranking_type})
  utterance.chartCandidates.append(ch)
  return True



# random util, should go away soon
def filterSVs (sv_list, sv_score):
  # this functionality should be moved to detection.
  i = 0
  ans = []
  while (i < len(sv_list)):
    if (sv_score[i] > SV_THRESHOLD):
      ans.append(sv_list[i])
    i = i + 1
  return ans


# TODO: dedupe with nl_data_spec.py
def _sample_child_place(main_place_dcid, contained_place_type):
  """Find a sampled child place"""
  if not contained_place_type:
    return None
  if contained_place_type == "City":
    return "geoId/0667000"
  child_places = dc.get_places_in([main_place_dcid], contained_place_type)
  if child_places.get(main_place_dcid):
    return child_places[main_place_dcid][0]
  else:
    triples = dc.triples(main_place_dcid, 'in').get('triples')
    if triples:
      for prop, nodes in triples.items():
        if prop != 'containedInPlace' and prop != 'geoOverlaps':
          continue
        for node in nodes['nodes']:
          if contained_place_type in node['types']:
            return node['dcid']
  return main_place_dcid