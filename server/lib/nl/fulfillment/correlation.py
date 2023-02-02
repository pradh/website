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

from lib.nl import utils
from lib.nl.detection import ClassificationType
from lib.nl.detection import ContainedInClassificationAttributes
from lib.nl.detection import Place
from lib.nl.fulfillment.base import add_chart_to_utterance
from lib.nl.fulfillment.base import ChartVars
from lib.nl.fulfillment.base import open_topics_ordered
from lib.nl.fulfillment.base import PopulateState
from lib.nl.fulfillment.context import classifications_of_type_from_context
from lib.nl.fulfillment.context import places_from_context
from lib.nl.fulfillment.context import svs_from_context
from lib.nl.utterance import ChartOriginType
from lib.nl.utterance import ChartType
from lib.nl.utterance import Utterance

#
# Handler for CORRELATION chart.  This does not use the populate_charts() logic
# because it is sufficiently different, requiring identifying pairs of SVs.
#


def populate(uttr: Utterance) -> bool:
  # Get the list of CONTAINED_IN classifications in order from current to past.
  classifications = classifications_of_type_from_context(
      uttr, ClassificationType.CONTAINED_IN)
  logging.info(classifications)
  for classification in classifications:
    if (not classification or not isinstance(
        classification.attributes, ContainedInClassificationAttributes)):
      continue
    place_type = classification.attributes.contained_in_place_type
    if _populate_correlation_for_place_type(
        PopulateState(uttr=uttr,
                      main_cb=None,
                      fallback_cb=None,
                      place_type=place_type)):
      return True
  return False


def _populate_correlation_for_place_type(state: PopulateState) -> bool:
  for pl in state.uttr.places:
    if (_populate_correlation_for_place(state, pl)):
      return True
  for pl in places_from_context(state.uttr):
    if (_populate_correlation_for_place(state, pl)):
      return True
  return False


def _populate_correlation_for_place(state: PopulateState, place: Place) -> bool:
  # Get child place samples for existence check.
  places_to_check = utils.get_sample_child_places(place.dcid,
                                                  state.place_type.value)
  if not places_to_check:
    return False

  # For the main SV of correlation, we expect a variable to
  # be detected in this `uttr`
  main_svs = open_topics_ordered(state)
  main_svs = utils.sv_existence_for_places(places_to_check, main_svs)
  if not main_svs:
    logging.info('Correlation found no Main SV')
    return False

  # For related SV, walk up the chain to find all SVs.
  context_svs = []
  for c_svs in svs_from_context(state.uttr):
    opened_svs = open_topics_ordered(c_svs)
    context_svs = utils.sv_existence_for_places(places_to_check, opened_svs)
    if context_svs:
      break
  if not context_svs:
    logging.info('Correlation found no Context SV')
    return False

  logging.info('Correlation Main SVs: %s', ', '.join(main_svs))
  logging.info('Correlation Context SVs: %s', ', '.join(context_svs))

  # Pick a single context SV for the results
  # TODO: Maybe consider more.
  found = False
  for main_sv in main_svs:
    found |= _populate_correlation_chart(state, place, main_sv, context_svs[0])
  return found


def _populate_correlation_chart(state: PopulateState, place: Place, sv_1: str,
                                sv_2: str) -> bool:
  state.block_id += 1
  chart_vars = ChartVars(svs=[sv_1, sv_2],
                         block_id=state.block_id,
                         include_percapita=False)
  return add_chart_to_utterance(ChartType.SCATTER_CHART, state, chart_vars,
                                [place], ChartOriginType.PRIMARY_CHART)
