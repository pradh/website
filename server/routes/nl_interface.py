# Copyright 2022 Google LLC
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
"""Data Commons NL Interface routes"""

import os
import logging
import json

import flask
from flask import Blueprint, current_app, render_template, escape, request
from google.protobuf.json_format import MessageToJson, ParseDict
from lib.nl_detection import ClassificationType, ContainedInPlaceType, Detection, NLClassifier, Place, PlaceDetection, SVDetection, SimpleClassificationAttributes
from typing import Dict, Union
import pandas as pd
import re
import requests

import services.datacommons as dc
import lib.nl_data_spec as nl_data_spec
import lib.nl_interpretation as nl_interpretation
import lib.nl_page_config as nl_page_config
import lib.nl_variable as nl_variable
from config import subject_page_pb2

bp = Blueprint('nl', __name__, url_prefix='/nl')

MAPS_API = "https://maps.googleapis.com/maps/api/place/textsearch/json?"
FIXED_PREFIXES = ['md=', 'mq=', 'st=', 'mp=', 'pt=']
FIXED_PROPS = set([p[:-1] for p in FIXED_PREFIXES])

COSINE_SIMILARITY_CUTOFF = 0.4


def _clean(input):
  return str(escape(input))


def _get_preferred_type(types):
  for t in ['Country', 'State', 'County', 'City']:
    if t in types:
      return t
  return sorted(types)[0]


def _maps_place(place_str):
  api_key = current_app.config["MAPS_API_KEY"]
  url_formatted = f"{MAPS_API}input={place_str}&key={api_key}"
  r = requests.get(url_formatted)
  resp = r.json()

  # Return the first "political" place found.
  if "results" in resp:
    for res in resp["results"]:
      if "political" in res["types"]:
        return res
  return {}


def _dc_recon(place_ids):
  resp = dc.resolve_id(place_ids, "placeId", "dcid")
  if "entities" not in resp:
    return {}

  d_return = {}
  for ent in resp["entities"]:
    for out in ent["outIds"]:
      d_return[ent["inId"]] = out
      break

  return d_return


def _remove_punctuations(s):
  s = s.replace('\'s', '')
  s = re.sub(r'[^\w\s]', ' ', s)
  return s


def _remove_places(query, places_found):
  for p_str in places_found:
    # See if the word "in" precedes the place. If so, best to remove it too.
    needle = "in " + p_str
    if needle not in query:
      needle = p_str
    query = query.replace(needle, "")

  # Remove any extra spaces and return.
  return ' '.join(query.split())


def _infer_place_dcid(places_found):
  if not places_found:
    return ""

  place_dcid = ""
  place = _maps_place(places_found[0])
  # If maps API returned a valid place, use the place_id to
  # get the dcid.
  if place and ("place_id" in place):
    place_id = place["place_id"]
    logging.info(f"MAPS API found place with place_id: {place_id}")
    place_ids_map = _dc_recon([place_id])

    if place_id in place_ids_map:
      place_dcid = place_ids_map[place_id]

  logging.info(f"DC API found DCID: {place_dcid}")
  return place_dcid


def _empty_svs_score_dict():
  return {"SV": [], "CosineScore": [], "SV_to_Sentences": {}}


def _result_with_debug_info(data_dict,
                            status,
                            embeddings_build,
                            query_detection: Detection,
                            data_spec=None):
  """Using data_dict and query_detection, format the dictionary response."""
  svs_dict = {
      'SV': query_detection.svs_detected.sv_dcids,
      'CosineScore': query_detection.svs_detected.sv_scores,
      'SV_to_Sentences': query_detection.svs_detected.svs_to_sentences
  }
  svs_to_sentences = query_detection.svs_detected.svs_to_sentences

  if svs_dict is None or not svs_dict:
    svs_dict = _empty_svs_score_dict()

  ranking_classification = "<None>"
  temporal_classification = "<None>"
  contained_in_classification = "<None>"
  correlation_classification = "<None>"
  clustering_classification = "<None>"

  for classification in query_detection.classifications:
    if classification.type == ClassificationType.RANKING:
      ranking_classification = str(classification.attributes.ranking_type)
    elif classification.type == ClassificationType.TEMPORAL:
      temporal_classification = str(classification.type)
    elif classification.type == ClassificationType.CONTAINED_IN:
      contained_in_classification = str(classification.type)
      contained_in_classification += \
          str(classification.attributes.contained_in_place_type)
    elif classification.type == ClassificationType.CORRELATION:
      correlation_classification = str(classification.type)
    elif classification.type == ClassificationType.CLUSTERING:
      clustering_classification = str(classification.type)
      clustering_classification += f". Top two SVs: "
      clustering_classification += f"{classification.attributes.sv_dcid_1, classification.attributes.sv_dcid_2,}. "
      clustering_classification += f"Cluster # 0: {str(classification.attributes.cluster_1_svs)}. "
      clustering_classification += f"Cluster # 1: {str(classification.attributes.cluster_2_svs)}."

  debug_info = {
      "debug": {
          'status':
              status,
          'original_query':
              query_detection.original_query,
          'places_detected':
              query_detection.places_detected.places_found,
          'main_place_dcid':
              query_detection.places_detected.main_place.dcid,
          'main_place_name':
              query_detection.places_detected.main_place.name,
          'query_with_places_removed':
              query_detection.places_detected.query_without_place_substr,
          'sv_matching':
              svs_dict,
          'svs_to_sentences':
              svs_to_sentences,
          'embeddings_build':
              embeddings_build,
          'ranking_classification':
              ranking_classification,
          'temporal_classification':
              temporal_classification,
          'contained_in_classification':
              contained_in_classification,
          'clustering_classification':
              clustering_classification,
          'correlation_classification':
              correlation_classification,
          'primary_sv':
              data_spec.primary_sv,
          'primary_sv_siblings':
              data_spec.primary_sv_siblings,
          'data_spec':
              data_spec,
      },
  }
  # Set the context which contains everything except the charts config.
  data_dict.update(debug_info)
  charts_config = data_dict.pop('config', {})
  return {'context': data_dict, 'config': charts_config}


def _detection(orig_query, cleaned_query, embeddings_build,
               recent_context: Union[Dict, None]) -> Detection:
  default_place = "United States"
  using_default_place = False
  using_from_context = False

  model = current_app.config['NL_MODEL']

  # Step 1: find all relevant places and the name/type of the main place found.
  places_found = model.detect_place(cleaned_query)

  if not places_found:
    logging.info("Place detection failed.")

  logging.info("Found places: {}".format(places_found))
  # If place_dcid was already set by the url, skip inferring it.
  place_dcid = request.args.get('place_dcid', '')
  if not place_dcid:
    place_dcid = _infer_place_dcid(places_found)

  # TODO: move this logic away from detection and to the context inheritance.
  # If a valid DCID was was not found or provided, do not proceed.
  # Use the default place only if there was no previous context.
  if not place_dcid:
    place_name_to_use = default_place
    if recent_context:
      place_name_to_use = recent_context.get('place_name')

    place_dcid = _infer_place_dcid([place_name_to_use])
    if place_name_to_use == default_place:
      using_default_place = True
      logging.info(
          f'Could not find a place dcid and there is no previous context. Using the default place: {default_place}.'
      )
      using_default_place = True
    else:
      logging.info(
          f'Could not find a place dcid but there was previous context. Using: {place_name_to_use}.'
      )
      using_from_context = True

  place_types = dc.property_values([place_dcid], 'typeOf')[place_dcid]
  main_place_type = _get_preferred_type(place_types)
  main_place_name = dc.property_values([place_dcid], 'name')[place_dcid][0]

  # Step 2: replace the places in the query sentence with "".
  query = _remove_places(cleaned_query, places_found)

  # Set PlaceDetection.
  place_detection = PlaceDetection(query_original=orig_query,
                                   query_without_place_substr=query,
                                   places_found=places_found,
                                   main_place=Place(dcid=place_dcid,
                                                    name=main_place_name,
                                                    place_type=main_place_type),
                                   using_default_place=using_default_place,
                                   using_from_context=using_from_context)

  # Step 3: Identify the SV matched based on the query.
  svs_scores_dict = _empty_svs_score_dict()
  try:
    svs_scores_dict = model.detect_svs(query, embeddings_build)
  except ValueError as e:
    logging.info(e)
    logging.info("Using an empty svs_scores_dict")

  # Set the SVDetection.
  sv_detection = SVDetection(
      query=query,
      sv_dcids=svs_scores_dict['SV'],
      sv_scores=svs_scores_dict['CosineScore'],
      svs_to_sentences=svs_scores_dict['SV_to_Sentences'])

  # Step 4: find query classifiers.
  ranking_classification = model.heuristic_ranking_classification(query)
  temporal_classification = model.query_classification("temporal", query)
  contained_in_classification = model.query_classification(
      "contained_in", query)
  logging.info(f'Ranking classification: {ranking_classification}')
  logging.info(f'Temporal classification: {temporal_classification}')
  logging.info(f'ContainedIn classification: {contained_in_classification}')

  # Set the Classifications list.
  classifications = []
  if ranking_classification is not None:
    classifications.append(ranking_classification)
  # TODO: reintroduce temporal classification at some point.
  # if temporal_classification is not None:
  #   classifications.append(temporal_classification)
  if contained_in_classification is not None:
    classifications.append(contained_in_classification)

    # Check if the contained in referred to COUNTRY type. If so,
    # and the default location was chosen, then set it to Earth.
    if (place_detection.using_default_place and
        (contained_in_classification.attributes.contained_in_place_type
         == ContainedInPlaceType.COUNTRY)):
      logging.info(
          "Changing detected place to Earth because no place was detected and contained in is about countries."
      )
      place_detection.main_place.dcid = "Earth"
      place_detection.main_place.name = "Earth"
      place_detection.main_place.place_type = "Place"
      place_detection.using_default_place = False

  # Correlation classification
  correlation_classification = model.heuristic_correlation_classification(query)
  logging.info(f'Correlation classification: {correlation_classification}')
  if correlation_classification is not None:
    classifications.append(correlation_classification)

  # Clustering-based different SV detection is only enabled in LOCAL.
  if os.environ.get('FLASK_ENV') == 'local' and svs_scores_dict:
    # Embeddings Indices.
    sv_index_sorted = []
    if 'EmbeddingIndex' in svs_scores_dict:
      sv_index_sorted = svs_scores_dict['EmbeddingIndex']

    # Clustering classification, currently disabled.
    # clustering_classification = model.query_clustering_detection(
    #     embeddings_build, query, svs_scores_dict['SV'],
    #     svs_scores_dict['CosineScore'], sv_index_sorted,
    #     COSINE_SIMILARITY_CUTOFF)
    # logging.info(f'Clustering classification: {clustering_classification}')
    # logging.info(f'Clustering Classification is currently disabled.')
    # if clustering_classification is not None:
    #   classifications.append(clustering_classification)

  if not classifications:
    # Simple Classification simply means:
    # Use the main place and matched SVs. There are no
    # rankings, temporal, contained_in or correlations.
    classifications.append(
        NLClassifier(type=ClassificationType.SIMPLE,
                     attributes=SimpleClassificationAttributes()))

  return Detection(original_query=orig_query,
                   cleaned_query=cleaned_query,
                   places_detected=place_detection,
                   svs_detected=sv_detection,
                   classifications=classifications)


@bp.route('/', strict_slashes=True)
def page():
  if (os.environ.get('FLASK_ENV') == 'production' or
      not current_app.config['NL_MODEL']):
    flask.abort(404)
  return render_template('/nl_interface.html',
                         maps_api_key=current_app.config['MAPS_API_KEY'])


@bp.route('/data', methods=['GET', 'POST'])
def data():
  if request.args.get('v', '') == '2':
    return _data_v2(request)
  return _data_v1(request)


def _data_v1(request):
  original_query = request.args.get('q')
  context_history = request.get_json().get('contextHistory', [])
  has_context = False
  if context_history:
    has_context = True
  logging.info(context_history)
  query = _clean(_remove_punctuations(original_query))
  embeddings_build = _clean(request.args.get('build', "combined_all"))
  default_place = "United States"
  res = {'place_type': '', 'place_name': '', 'place_dcid': '', 'config': {}}
  if not query:
    logging.info("Query was empty")
    return _result_with_debug_info(res, "Aborted: Query was Empty.",
                                   embeddings_build,
                                   _detection("", "", embeddings_build))

  # Query detection routine:
  # Returns detection for Place, SVs and Query Classifications.
  recent_context = None
  if context_history:
    recent_context = context_history[-1]
  query_detection = _detection(_clean(original_query), query,
                               embeddings_build, recent_context)

  # Get Data Spec
  data_spec = nl_data_spec.compute(query_detection)
  page_config_pb = nl_page_config.build_page_config(query_detection, data_spec,
                                                    context_history)
  page_config = json.loads(MessageToJson(page_config_pb))

  d = {
      'place_type': query_detection.places_detected.main_place.place_type,
      'place_name': query_detection.places_detected.main_place.name,
      'place_dcid': query_detection.places_detected.main_place.dcid,
      'config': page_config,
  }
  status_str = "Successful"
  if query_detection.places_detected.using_default_place or not data_spec.selected_svs:
    status_str = ""

  if query_detection.places_detected.using_default_place:
    status_str += f'**No Place Found** (using default: {default_place}). '
  elif query_detection.places_detected.using_from_context:
    status_str += f'**No Place Found** (using context: {query_detection.places_detected.main_place.name}). '
  if not data_spec.selected_svs:
    status_str += '**No SVs Found**.'

  return _result_with_debug_info(d, status_str, embeddings_build,
                                 query_detection, data_spec)

def _data_v2(request):
  original_query = request.args.get('q')
  prev_interpretation_dict = request.get_json().get('interpretation', [])
  embeddings_build = _clean(request.args.get('build', "combined_all"))

  # Load the previous interpretation if any.
  logging.info(prev_interpretation_dict)
  prev_interpretation = nl_interpretation.dict_to_interpretation(prev_interpretation_dict)

  # Clean up query without punctuations
  query = _clean(_remove_punctuations(original_query))

  if not query:
    logging.info("Query was empty")
    return _interpretation_with_debug_info(None, "Aborted: Query was Empty.",
                                           embeddings_build,
                                           _detection("", "", embeddings_build))

  # Run the query through all the classifiers.
  #
  # TODO: Hack to reuse _detection without modification.
  recent_context = None
  if prev_interpretation:
    recent_context = {'place_name': prev_interpretation.main_place.name}
  query_detection = _detection(_clean(original_query), query,
                               embeddings_build, recent_context)

  # Build the interpretation given the detection results from this query and
  # previous interpretation (if any).
  interpretation = nl_data_spec.compute_v2(query_detection, prev_interpretation)
  page_config_pb = nl_page_config.build_page_config_v2(interpretation)
  page_config = json.loads(MessageToJson(page_config_pb))

  status_str = "Successful"
  if query_detection.places_detected.using_default_place or not interpretation.variables:
    status_str = ""

  if query_detection.places_detected.using_default_place:
    default_place = "United States"
    status_str += f'**No Place Found** (using default: {default_place}). '
  elif query_detection.places_detected.using_from_context:
    status_str += f'**No Place Found** (using context: {query_detection.places_detected.main_place.name}). '
  if not interpretation.variables:
    status_str += '**No SVs Found**.'

  return _interpretation_with_debug_info(interpretation, status_str, embeddings_build,
                                         query_detection, page_config)
