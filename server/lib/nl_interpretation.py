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
"""Module for NL query Interpretation structure"""

from dataclasses import dataclass
from lib import nl_detection
from lib import nl_variable
from typing import Dict, List
import logging

# Extended interpretation info, that is only relevant during query processing.
@dataclass
class InterpretationAux:
  pass

# A common Data Structure that captures the interpretation of a query. This
# is minimal data required for chart generation, and serves as context for
# a future query.
@dataclass
class Interpretation:
  # The main place
  main_place: nl_detection.Place

  # Groups of ordered variables.
  variables: nl_variable.VariableStore

  # Various Classifiers
  #
  # Indicates whether the query specified contained-in place type
  contained_in_classification: bool
  # If contained_in_classification==False, then this is inferred from
  # main_place.  Otherwise, user asked for it.  
  contained_in_place_type: nl_detection.ContainedInPlaceType
  # Rank types could be a list (if they ask for best and worst), for now support single.
  ranking_classification: nl_detection.RankingType
  # Correlated StatVar
  correlation_classification: str

  # Any transient data
  aux: InterpretationAux


def interpretation_to_dict(intr: Interpretation) -> Dict:
  return {}

def dict_to_interpretation(intr_dict: Dict) -> Interpretation:
  return Interpretation()
