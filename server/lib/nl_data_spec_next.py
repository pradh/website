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


from lib.nl_detection import ClassificationType, Detection, NLClassifier, Place, ContainedInPlaceType, ContainedInClassificationAttributes
from lib import nl_variable, nl_topic
import services.datacommons as dc


# this needs to be moved into the cookie
gCurrentUtterance = None

QUERY = 1
RESPONSE = 2

# We will ignore SV detections that are below this threshold
SV_THRESHOLD = 0.5

# How far back do we do
CNTXT_LOOKBACK_LIMIT = 3

class Utterance:
  pass

class ChartOriginType(Enum):
  PRIMARY_CHART = 0
  SECONDARY_CHART = 1

class ChartType(Enum):
  TIMELINE_CHART = 0
  MAP_CHART = 1
  RANKING_CHART = 2
  BAR_CHART = 2
  



@dataclass
class Utterance:
  prev_utterance: Utterance
  query: str
  detection: Detection
  query_type: ClassificationType
  places: List[Place]  # change this to be just the dcid
  svs: List[str]
  classifications: List[NLClassifier] 
  chartCandidates: List[str]
  rankedCharts: List[str]
  answerPlaces: List[str]
  

@dataclass
class ChartSpec:
  chart_type: ChartType
  utterance: Utterance
  places: List[str]
  svs: List[str]
  attr: {}

                    

def compute(query_detection: Detection):
  global gCurrentUtterance
  
  uttr = Utterance(prev_utterance=gCurrentUtterance,
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
  gCurrentUtterance = uttr

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
    populateContainedin(uttr)
  elif (uttr.query_type == ClassificationType.RANKING):
    populateRanking(uttr)

  rankCharts(uttr)

# this needs to be written. Right now, the part that does the output 
# is looked for a 'data_spec' instance. Need to rewrite
# nl_page_config.build_page_config from the ranked charts in utterance
#  pb = rankedChartsToPageConfig(uttr)
  
  return None



#Handler for simple charts  
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
  return False


def addSimpleCharts (place, svs, uttr):
  print("Add line chart %s %s" % (place.name, svs))
  found = False
  for sv in svs:
    expanded_svs = svgOrTopicToSVs(sv) 
    for sv in expanded_svs:
      if (svExistsForPlace(place, sv)):
        if (addOneChartToUtterance(ChartType.TIMELINE_CHART, uttr, sv, place, ChartOriginType.PRIMARY_CHART)):
          found = True

  extended_svs = nl_variable.extend_svs(svs)
  if (extended_svs):
    if (addOneChartToUtterance(ChartType.TIMELINE_CHART, uttr, extended_svs, place,  ChartOriginType.SECONDARY_CHART)):
      found = True
  return found

#Handler for Ranking
def populateRanking(uttr):

  classification = classificationOfTypeFromContext(uttr, ClassificationType.CONTAINED_IN)
  place_type = ContainedInPlaceType.COUNTY #poor default. should do this based on main place
  if (classification):
    print(classification)
    if (isinstance(classification.attributes, ContainedInClassificationAttributes)):
      place_type = classification.attributes.contained_in_place_type

  if (len(uttr.places) > 0):
    containing_place = uttr.places[0] # should eventually be able to handle multiple places
  else:
    cntxt_places = placesFromContext(uttr)
    if (len(cntxt_places) > 0):
      containing_place = cntxt_places[0]
    else:
      containing_place = "country/USA" # should be based on place_type

  if (len(uttr.svs) > 0):
    sv = uttr.svs[0]
  else:
    cntxt_svs = svsFromContext(uttr)
    if (len(cntxt_svs) > 0):
      sv = cntxt_svs[0]
    else:
      sv = "Population" # lame

  addOneChartToUtterance(ChartType.RANKING_CHART, uttr, sv, containing_place, ChartOriginType.PRIMARY_CHART, place_type)



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

def classificationOfTypeFromContext(uttr, ctype):
  for cl in uttr.classifications:
    if (cl.type == ctype):
      return cl
  prev_uttr_count = 0
  prev = uttr.prev_utterance
  while (prev and prev_uttr_count < CNTXT_LOOKBACK_LIMIT):
    for cl in uttr.classifications:
      if (cl.type == ctype):
        return cl
  return None

def svgOrTopicToSVs (sv):
  if (not ("svg" in sv or "topic" in sv)):
    return [sv]
  if ("topic" in sv):
    vals = dc.get_property_values([sv], "relevantVariable")
    if (sv in vals):
      return vals[sv]
  if ("svg" in sv) :
    return expand_svg(sv)
  return None
          
      
def rankCharts (utterance):
  for chart in utterance.chartCandidates:
    print("Chart: %s %s\n" % (chart.places, chart.svs))
  utterance.rankedCharts = utterance.chartCandidates


def svExistsForPlace(place, sv):
  # Needs work :)
  return True

def isSV(sv):
  #needs work
  return (not ("svg" in sv or "topic" in sv))

def addOneChartToUtterance(chart_type, utterance, svs, places, primary_vs_secondary, place_type=None):
  ch = ChartSpec(chart_type=chart_type,
                 svs=svs,
                 places=places,
                 utterance=utterance,
                 attr={"class" : primary_vs_secondary, "place_type" : place_type})
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



