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

from typing import List, Dict

from dataclasses import dataclass
from enum import Enum
from lib.nl_detection import ClassificationType, Detection, NLClassifier, Place

class ChartOriginType(Enum):
  PRIMARY_CHART = 0
  SECONDARY_CHART = 1

# TODO: Distinguish between multi-place bar vs. multi-var bar?
class ChartType(Enum):
  TIMELINE_CHART = 0
  MAP_CHART = 1
  RANKING_CHART = 2
  BAR_CHART = 3
  PLACE_OVERVIEW = 4

class Utterance:
  pass

@dataclass
class ChartSpec:
  chart_type: ChartType
  utterance: Utterance
  # TODO: change this to be just the dcid
  places: List[Place]
  svs: List[str]
  attr: Dict

@dataclass
class Utterance:
  prev_utterance: Utterance
  query: str
  detection: Detection
  query_type: ClassificationType
  # TODO: change this to be just the dcid
  places: List[Place]
  svs: List[str]
  classifications: List[NLClassifier] 
  chartCandidates: List[ChartSpec]
  rankedCharts: List[ChartSpec]
  answerPlaces: List[str]
  