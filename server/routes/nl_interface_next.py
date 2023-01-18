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
"""Data Commons NL Interface routes"""

import os
import logging
import json

import flask
from flask import Blueprint, current_app, render_template, escape, request
from google.protobuf.json_format import MessageToJson, ParseDict
from lib.nl_detection import ClassificationType, ContainedInPlaceType, Detection, NLClassifier, Place, PlaceDetection, SVDetection, SimpleClassificationAttributes
from typing import Dict, List, Union
import pandas as pd
import re
import requests

import services.datacommons as dc
import lib.nl_data_spec_next as nl_data_spec
import lib.nl_page_config_next as nl_page_config
import lib.nl_utterance as nl_utterance

bp = Blueprint('nl_next', __name__, url_prefix='/nlnext')

MAPS_API = "https://maps.googleapis.com/maps/api/place/textsearch/json?"
FIXED_PREFIXES = ['md=', 'mq=', 'st=', 'mp=', 'pt=']
FIXED_PROPS = set([p[:-1] for p in FIXED_PREFIXES])

COSINE_SIMILARITY_CUTOFF = 0.4


def _get_preferred_type(types):
  for t in ['Country', 'State', 'County', 'City']:
    if t in types:
      return t
  return sorted(types)[0]


def _sv_definition_name_maps(svgs_info, svs_list):
  sv2definition = {}
  sv2name = {}
  for svgi in svgs_info:
    if 'info' not in svgi:
      continue
    if 'childStatVars' not in svgi['info']:
      continue
    child_svs = svgi['info']['childStatVars']
    for svi in child_svs:
      if 'id' not in svi:
        continue
      if 'definition' in svi:
        sv2definition[svi['id']] = svi['definition']
      if 'displayName' in svi:
        sv2name[svi['id']] = svi['displayName']

  # Get any missing SV Names
  sv_names_api = dc.property_values(svs_list, 'name')
  sv2name.update({p: v[0] for p, v in sv_names_api.items()})

  return {"sv2definition": sv2definition, "sv2name": sv2name}


def _caps(e):
  return e[0].upper() + e[1:]


def _caps_list(list):
  return [_caps(e) for e in list]


def _bucket_to_name(key):
  parts = key.split(',')
  # Drilldown by <P> for <PopType> [<statType>] <MeasuredProp>: <V1>, <V2>, ...
  pv = {part.split('=')[0]: part.split('=')[1] for part in parts}

  end_parts = []
  prefix = ""
  for p, v in pv.items():
    if p in FIXED_PROPS:
      continue
    if not v:
      prefix = "Drilldown by " + _caps(p) + " for '"
    else:
      end_parts.append(v)

  mid_parts = [pv['pt']]
  if 'st' in pv:
    mid_parts.append(pv['st'].replace('Value', ''))
  mid_parts.append(pv['mp'])

  result = prefix + " ".join(_caps_list(mid_parts))
  if end_parts:
    result += ': ' + ', '.join(sorted(_caps_list(end_parts)))
  result += "'"

  # Some fixups
  return result.replace('Person Count', 'Population')


# Returns a map of buckets.  The key is SV definition without V, and value is
# the missing V.
def _get_buckets(defn):
  parts = defn.split(',')
  fixed_parts = []
  cpv_parts = []
  for part in parts:
    if any([part.startswith(p) for p in FIXED_PREFIXES]):
      fixed_parts.append(part)
    else:
      cpv_parts.append(part)
  fixed_prefix = ','.join(fixed_parts)
  if not cpv_parts:
    return {fixed_prefix: ""}

  buckets = {}
  for rpv in cpv_parts:
    parts = [fixed_prefix]
    v_only = ""
    for opv in cpv_parts:
      if rpv == opv:
        # P only
        p_only, v_only = rpv.split('=')
        parts.append(p_only + '=')
      else:
        parts.append(opv)
    buckets[','.join(parts)] = v_only
  return buckets


def _chart_config(place_dcid, main_place_type, main_place_name,
                  child_places_type, highlight_svs, sv2name, peer_buckets):
  # TODO: temporarility disable child places charts before they can be handled
  # gracefully. Right now each query incurs hundreds of single place API call,
  # which should be replaced by "withInPlace" API call. This spams the logs and
  # makes the loading slow.
  child_places_type = ""
  #@title
  chart_config = {'metadata': {'place_dcid': [place_dcid]}}

  if child_places_type:
    chart_config['metadata']['contained_place_types'] = {
        main_place_type: child_places_type
    }

  added_buckets = set()
  sv4spec = set()

  blocks = []
  for sv in highlight_svs:
    tiles = []

    tiles.append({
        'title': sv2name[sv] + ': historical',
        'type': 'LINE',
        'stat_var_key': [sv]
    })

    if child_places_type:
      tiles.append({
          'title': sv2name[sv] + ': places within ' + main_place_name,
          'type': 'MAP',
          'stat_var_key': [sv]
      })

      tiles.append({
          'title': sv2name[sv] + ': rankings within ' + main_place_name,
          'type': 'RANKING',
          'stat_var_key': [sv],
          'ranking_tile_spec': {
              'show_highest': True,
              'show_lowest': True
          }
      })

    # If the highlight SV is part of an SV peer-group, add it ahead of others.
    for key, svs in peer_buckets.items():
      if sv not in svs:
        continue
      if key in added_buckets:
        continue

      sv_list = list(svs)
      # Consider if this should be bar or time-series?
      tiles.append({
          'title': _bucket_to_name(key),
          'type': 'LINE',
          'stat_var_key': sv_list
      })
      added_buckets.add(key)
      sv4spec.update(sv_list)
      # TODO: add CLUSTERED_BAR

    blocks.append({'title': sv2name[sv], 'columns': [{'tiles': tiles}]})
    sv4spec.add(sv)

  for key, svs in peer_buckets.items():
    if key in added_buckets:
      continue
    tile = {
        'title': _bucket_to_name(key),
        'type': 'BAR',
        'stat_var_key': list(svs)
    }
    blocks.append({
        'title': _bucket_to_name(key) + ' in ' + main_place_name,
        'columns': [{
            'tiles': [tile]
        }]
    })
    added_buckets.add(key)
    sv4spec.update(list(svs))
    # TODO: add CLUSTERED_BAR when supported

  sv_specs = {}
  for sv in sv4spec:
    sv_specs[sv] = {'stat_var': sv, 'name': sv2name[sv]}

  chart_config['categories'] = [{
      'title': 'Search Results',
      'blocks': blocks,
      'stat_var_spec': sv_specs
  }]

  return chart_config


def _get_svg_info(entities, svg_dcids):
  result = dc.get_variable_group_info(svg_dcids, entities)
  if isinstance(result, dict):
    return result
  return {}


def _related_svgs(svs_list, relevant_places):
  # Using PropertyValues (memberOf) and VariableGroupInfo APIs
  svs_to_svgs = dc.property_values(svs_list, 'memberOf')

  # Get all distinct SVGs and SV under verticals.
  svgs = set()
  sv_under_verticals = set()

  for sv, svg_list in svs_to_svgs.items():
    has_svg = False
    for svg in svg_list:
      svgs.add(svg)
      if '_' in svg:
        has_svg = True
    if not has_svg:
      # This is top-level SV, so we will try getting child SVGs
      sv_under_verticals.add(sv)

  # Get SVG info for all relevant places
  svgs_info = _get_svg_info(relevant_places, list(svgs))
  return svgs_info.get('data', {})


def _peer_buckets(sv2definition, svs_list):
  peer_buckets = {}
  for sv, defn in sv2definition.items():
    keys = _get_buckets(defn)
    for key, cval in keys.items():
      if key not in peer_buckets:
        peer_buckets[key] = {}
      peer_buckets[key][sv] = cval

  # Remove single SV keys and remove groups with result SV
  for bucket_id in list(peer_buckets.keys()):
    if len(peer_buckets[bucket_id]) == 1:
      # With only 1 SV, no point having a bucket
      del peer_buckets[bucket_id]
    elif not any([sv in peer_buckets[bucket_id] for sv in svs_list]):
      # this bucket has no useful SV
      del peer_buckets[bucket_id]

  return peer_buckets


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
                            query_detection: Detection):
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
      contained_in_classification = \
          str(classification.attributes.contained_in_place_type)
    elif classification.type == ClassificationType.CORRELATION:
      correlation_classification = str(classification.type)
    elif classification.type == ClassificationType.CLUSTERING:
      clustering_classification = str(classification.type)
      clustering_classification += f". Top two SVs: "
      clustering_classification += f"{classification.attributes.sv_dcid_1, classification.attributes.sv_dcid_2,}. "
      clustering_classification += f"Cluster # 0: {str(classification.attributes.cluster_1_svs)}. "
      clustering_classification += f"Cluster # 1: {str(classification.attributes.cluster_2_svs)}."

  # TODO: Revisit debug info
  debug_info = {
    'status': status,
    'original_query': query_detection.original_query,
    'sv_matching': svs_dict,
    'svs_to_sentences': svs_to_sentences,
    'embeddings_build': embeddings_build,
    'ranking_classification': ranking_classification,
    'temporal_classification': temporal_classification,
    'contained_in_classification': contained_in_classification,
    'clustering_classification': clustering_classification,
    'correlation_classification': correlation_classification
  }
  if query_detection.places_detected:
    debug_info.update({
          'places_detected':
              query_detection.places_detected.places_found,
          'main_place_dcid':
              query_detection.places_detected.main_place.dcid,
          'main_place_name':
              query_detection.places_detected.main_place.name,
          'query_with_places_removed':
              query_detection.places_detected.query_without_place_substr,
    })
  data_dict['debug'] = debug_info
  return data_dict


def _detection(orig_query, cleaned_query, embeddings_build) -> Detection:
  model = current_app.config['NL_MODEL']

  # Step 1: find all relevant places and the name/type of the main place found.
  places_found = model.detect_place(cleaned_query)

  if not places_found:
    logging.info("Place detection failed.")

  logging.info("Found places: {}".format(places_found))
  # If place_dcid was already set by the url, skip inferring it.
  place_dcid = request.args.get('place_dcid', '')
  if not place_dcid and places_found:
    place_dcid = _infer_place_dcid(places_found)

  if place_dcid:
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
                                                      place_type=main_place_type))
  else:
    query = cleaned_query
    place_detection = None

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
  if contained_in_classification is not None:
    classifications.append(contained_in_classification)

  # Correlation classification
  correlation_classification = model.heuristic_correlation_classification(query)
  logging.info(f'Correlation classification: {correlation_classification}')
  if correlation_classification is not None:
    classifications.append(correlation_classification)

  if not classifications:
    # if not classification is found, it should default to UNKNOWN (not SIMPLE)
    classifications.append(
        NLClassifier(type=ClassificationType.UNKNOWN,
                     attributes=SimpleClassificationAttributes()))

  return Detection(original_query=orig_query,
                   cleaned_query=cleaned_query,
                   places_detected=place_detection,
                   svs_detected=sv_detection,
                   query_type = queryTypeFromClassifications(classifications),
                   classifications=classifications)

def queryTypeFromClassifications(classifications):
  ans = ClassificationType.SIMPLE
  for cl in classifications:
    if (classificationToInt(cl.type) > classificationToInt(ans)):
      ans = cl.type
  return ans

def classificationToInt(en):
  if (en == ClassificationType.SIMPLE):
    return 1
  elif (en == ClassificationType.CONTAINED_IN):
    return 3
  elif (en == ClassificationType.RANKING):
    return 4
  else:
    return 0

@bp.route('/', strict_slashes=True)
def page():
  if (os.environ.get('FLASK_ENV') == 'production' or
      not current_app.config['NL_MODEL']):
    flask.abort(404)
  return render_template('/nl_interface.html',
                         maps_api_key=current_app.config['MAPS_API_KEY'])


@bp.route('/data', methods=['GET', 'POST'])
def data():
  """Data handler."""
  if (os.environ.get('FLASK_ENV') == 'production' or
      not current_app.config['NL_MODEL']):
    flask.abort(404)
  original_query = request.args.get('q')
  context_history = request.get_json().get('contextHistory', [])
  logging.info(context_history)

  query = str(escape(_remove_punctuations(original_query)))
  embeddings_build = str(escape(request.args.get('build', "combined_all")))
  default_place = "United States"
  res = {
    'place': {
      'dcid': '',
      'name': '',
      'place_type': '',
    },
    'config': {},
    'context': context_history
  }
  if not query:
    logging.info("Query was empty")
    return _result_with_debug_info(res, "Aborted: Query was Empty.",
                                   embeddings_build,
                                   _detection("", "", embeddings_build))

  # Query detection routine:
  # Returns detection for Place, SVs and Query Classifications.
  query_detection = _detection(str(escape(original_query)), query,
                               embeddings_build)

  # Generate new utterance.
  prev_utterance = nl_utterance.load_utterance(context_history)
  utterance = nl_data_spec.compute(query_detection, prev_utterance)

  if utterance.rankedCharts:
    page_config_pb = nl_page_config.build_page_config(utterance)
    page_config = json.loads(MessageToJson(page_config_pb))
    # Use the first chart's place as main place.
    main_place = utterance.rankedCharts[0].places[0]
  else:
    page_config = {}
    main_place = Place(dcid='', name='', place_type='')

  context_history = nl_utterance.save_utterance(utterance)
  logging.info(context_history)

  data_dict = {
      'place': {
        'dcid': main_place.dcid,
        'name': main_place.name,
        'place_type': main_place.place_type,
      },
      'config': page_config,
      'context': context_history
  }
  status_str = "Successful"
  if utterance.rankedCharts:
    status_str = ""
  else:
    if not utterance.places:
      status_str += f'**No Place Found**. '
    if not utterance.svs:
      status_str += '**No SVs Found**.'

  data_dict = _result_with_debug_info(data_dict, status_str,
                                      embeddings_build, query_detection)
  return data_dict
