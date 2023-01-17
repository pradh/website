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

from config import subject_page_pb2
from lib.nl_utterance import Utterance, ChartType
from lib.nl_detection import ClassificationType, NLClassifier, Place, RankingType
from lib import nl_variable, nl_topic
from services import datacommons as dc
import json
import logging
import os

PLACE_TYPE_TO_PLURALS = {
    "place": "places",
    "continent": "continents",
    "country": "countries",
    "state": "states",
    "province": "provinces",
    "county": "counties",
    "city": "cities",
    "censuszipcodetabulationarea": "census zip code tabulation areas",
    "town": "towns",
    "village": "villages",
    "censusdivision": "census divisions",
    "borough": "boroughs",
    "eurostatnuts1": "Eurostat NUTS 1 places",
    "eurostatnuts2": "Eurostat NUTS 2 places",
    "eurostatnuts3": "Eurostat NUTS 3 places",
    "administrativearea1": "administrative area 1 places",
    "administrativearea2": "administrative area 2 places",
    "administrativearea3": "administrative area 3 places",
    "administrativearea4": "administrative area 4 places",
    "administrativearea5": "administrative area 5 places",
}

CHART_TITLE_CONFIG_RELATIVE_PATH = "../config/nl_page/chart_titles_by_sv.json"


def pluralize_place_type(place_type: str) -> str:
  return PLACE_TYPE_TO_PLURALS.get(place_type.lower(),
                                   PLACE_TYPE_TO_PLURALS["place"])


def get_sv_name(svs):
  sv2name_raw = dc.property_values(svs, 'name')
  uncurated_names = {
      sv: names[0] if names else sv for sv, names in sv2name_raw.items()
  }
  basepath = os.path.dirname(__file__)
  title_config_path = os.path.abspath(
      os.path.join(basepath, CHART_TITLE_CONFIG_RELATIVE_PATH))
  title_by_sv_dcid = {}
  with open(title_config_path) as f:
    title_by_sv_dcid = json.load(f)
  sv_name_map = {}
  # If a curated name is found return that,
  # Else return the name property for SV.
  for sv in svs:
    if sv in title_by_sv_dcid:
      sv_name_map[sv] = title_by_sv_dcid[sv]
    else:
      sv_name_map[sv] = uncurated_names[sv]

  return sv_name_map


_SV_PARTIAL_DCID_NO_PC = [
    'Temperature', 'Precipitation', "BarometricPressure", "CloudCover",
    "PrecipitableWater", "Rainfall", "Snowfall", "Visibility", "WindSpeed",
    "ConsecutiveDryDays", "Percent", 'Area_'
]


def _should_add_percapita(sv_dcid: str) -> bool:
  for skip_phrase in _SV_PARTIAL_DCID_NO_PC:
    if skip_phrase in sv_dcid:
      return False
  return True


def _is_sv_percapita(sv_name: str) -> bool:
  # Use names for these since some old prevalence dcid's do not use the new naming scheme.
  if "Percentage" in sv_name or "Prevalence" in sv_name:
    return True
  return False


def _single_place_single_var_timeline_block(sv_dcid, sv2name):
  """A column with two charts, main stat var and per capita"""
  block = subject_page_pb2.Block(title=sv2name[sv_dcid],
                                 columns=[subject_page_pb2.Block.Column()])
  stat_var_spec_map = {}

  # Line chart for the stat var
  sv_key = sv_dcid
  tile = subject_page_pb2.Tile(type=subject_page_pb2.Tile.TileType.LINE,
                               title="Total",
                               stat_var_key=[sv_key])
  stat_var_spec_map[sv_key] = subject_page_pb2.StatVarSpec(
      stat_var=sv_dcid, name=sv2name[sv_dcid])
  block.columns[0].tiles.append(tile)

  # Line chart for the stat var per capita
  if _should_add_percapita(sv_dcid):
    sv_key = sv_dcid + '_pc'
    tile = subject_page_pb2.Tile(type=subject_page_pb2.Tile.TileType.LINE,
                                 title="Per Capita",
                                 stat_var_key=[sv_key])
    stat_var_spec_map[sv_key] = subject_page_pb2.StatVarSpec(
        stat_var=sv_dcid,
        name=sv2name[sv_dcid],
        denom="Count_Person",
        scaling=100,
        unit="%")
    block.columns[0].tiles.append(tile)
  return block, stat_var_spec_map


def _single_place_multiple_var_timeline_block(svs, sv2name):
  """A column with two chart, all stat vars and per capita"""
  block = subject_page_pb2.Block(columns=[subject_page_pb2.Block.Column()])
  stat_var_spec_map = {}

  # Line chart for the stat var
  tile = subject_page_pb2.Tile(type=subject_page_pb2.Tile.TileType.LINE,
                               title="Total",
                               stat_var_key=[])
  for sv in svs:
    sv_key = sv
    tile.stat_var_key.append(sv_key)
    stat_var_spec_map[sv_key] = subject_page_pb2.StatVarSpec(stat_var=sv,
                                                             name=sv2name[sv])
  block.columns[0].tiles.append(tile)

  # Line chart for the stat var per capita
  svs_pc = list(filter(lambda x: _should_add_percapita(x), svs))
  if len(svs_pc) > 0:
    tile = subject_page_pb2.Tile(type=subject_page_pb2.Tile.TileType.LINE,
                                 title="Per Capita")
    for sv in svs_pc:
      sv_key = sv + '_pc'
      tile.stat_var_key.append(sv_key)
      stat_var_spec_map[sv_key] = subject_page_pb2.StatVarSpec(
          stat_var=sv,
          name=sv2name[sv],
          denom="Count_Person",
          scaling=100,
          unit="%")
    block.columns[0].tiles.append(tile)

  return block, stat_var_spec_map


def _multiple_place_bar_block(places: List[Place], svs: List[str], sv2name):
  """A column with two charts, main stat var and per capita"""
  block = subject_page_pb2.Block(title="")
  column = block.columns.add()
  stat_var_spec_map = {}
  # Total
  tile = subject_page_pb2.Tile(type=subject_page_pb2.Tile.TileType.BAR,
                               title="Total",
                               comparison_places=[x.dcid for x in places])
  for sv in svs:
    sv_key = sv + "_multiple_place_bar_block"
    tile.stat_var_key.append(sv_key)
    stat_var_spec_map[sv_key] = subject_page_pb2.StatVarSpec(stat_var=sv,
                                                             name=sv2name[sv])

  column.tiles.append(tile)
  # Per Capita
  svs_pc = list(filter(lambda x: _should_add_percapita(x), svs))
  if len(svs_pc) > 0:
    tile = subject_page_pb2.Tile(type=subject_page_pb2.Tile.TileType.BAR,
                                 title="Per Capita",
                                 comparison_places=[x.dcid for x in places])
    for sv in svs_pc:
      sv_key = sv + "_multiple_place_bar_block_pc"
      tile.stat_var_key.append(sv_key)
      stat_var_spec_map[sv_key] = subject_page_pb2.StatVarSpec(
          stat_var=sv,
          denom="Count_Person",
          name=sv2name[sv],
          scaling=100,
          unit="%")

    column.tiles.append(tile)
  return block, stat_var_spec_map


def _topic_sv_blocks(category: subject_page_pb2.Category,
                     classification_type: NLClassifier, topic_svs: List[str],
                     extended_sv_map: Dict[str,
                                           List[str]], sv2name, sv_exists_list):
  """Fill in category if there is a topic."""
  main_block = category.blocks.add()
  column = main_block.columns.add()
  for sv in topic_svs:
    if 'dc/svpg/' in sv:
      sub_svs = extended_sv_map[sv]
      if not sub_svs:
        continue
      sub_svs_exist = list(filter(lambda x: x in sv_exists_list, sub_svs))
      if not sub_svs_exist:
        continue
      # add a block for each peer group
      block = category.blocks.add()
      column = block.columns.add()
      for i, sub_sv in enumerate(sub_svs_exist):
        if classification_type == ClassificationType.CONTAINED_IN:
          # always maps for contained_in
          tile = column.tiles.add()
          tile.type = subject_page_pb2.Tile.TileType.MAP
          tile.title = nl_topic.svpg_name(sv)
        else:
          # split up into several line charts
          if i % 5 == 0:
            tile = column.tiles.add()
            tile.type = subject_page_pb2.Tile.TileType.LINE
            tile.title = nl_topic.svpg_name(sv)
        tile.stat_var_key.append(sub_sv)
        category.stat_var_spec[sub_sv].stat_var = sub_sv
        category.stat_var_spec[sub_sv].name = sv2name[sub_sv]
    elif sv in sv_exists_list:
      # add to main line chart
      tile = column.tiles.add()
      if classification_type == ClassificationType.CONTAINED_IN:
        # always maps for contained_in
        tile.type = subject_page_pb2.Tile.TileType.MAP
      else:
        tile.type = subject_page_pb2.Tile.TileType.LINE
      tile.title = sv2name[sv]
      tile.stat_var_key.append(sv)
      category.stat_var_spec[sv].stat_var = sv
      category.stat_var_spec[sv].name = sv2name[sv]


def build_page_config(uttr: Utterance):
  # Init
  page_config = subject_page_pb2.SubjectPageConfig()
  # Set metadata
  page_config.metadata.place_dcid.append(uttr.places[0].dcid)
  # TODO: Get from ContainedInPlace chart?
  # page_config.metadata.contained_place_types[
  #     main_place_spec.type] = contained_place_spec.contained_place_type

  # Set category data
  category = page_config.categories.add()

  # Get names of all SVs
  all_svs = set()
  for cspec in uttr.rankedCharts:
    all_svs.update(cspec.svs)
  sv2name = get_sv_name(list(all_svs))

  for cspec in uttr.rankedCharts:
    if not cspec.places:
      continue
    block = None
    stat_var_spec_map = {}
    if cspec.chart_type == ChartType.PLACE_OVERVIEW:
      block = subject_page_pb2.Block()
      block.title = cspec.places[0].name
      column = block.columns.add()
      tile = column.tiles.add()
      tile.type = subject_page_pb2.Tile.TileType.PLACE_OVERVIEW
    elif cspec.chart_type == ChartType.TIMELINE_CHART:
      if len(cspec.svs) > 1:
        block, stat_var_spec_map = _single_place_multiple_var_timeline_block(
            cspec.svs, sv2name)
      else:
        block, stat_var_spec_map = _single_place_single_var_timeline_block(cspec.svs[0], sv2name)
    elif cspec.chart_type == ChartType.BAR_CHART:
      block, stat_var_spec_map = _multiple_place_bar_block(cspec.places, cspec.svs, sv2name)
    elif cspec.chart_type == ChartType.MAP_CHART:
      if len(cspec.places) > 1:
        logging.error('Bad Map chart: ', cspec)
        continue
      if len(cspec.svs) > 1:
        logging.error('Bad Map chart: ', cspec)
        continue
      pri_sv = cspec.svs[0]
      pri_place = cspec.places[0]

      # Query for place and sv, draw simple charts
      # The primary stat var
      block = subject_page_pb2.Block()
      block.title = "{} in {}".format(
          pluralize_place_type(
              cspec.attr['place_type']).capitalize(), pri_place.name)
      column = block.columns.add()
      # The main tile
      tile = column.tiles.add()
      tile.stat_var_key.append(pri_sv)
      tile.type = subject_page_pb2.Tile.TileType.MAP
      tile.title = sv2name[pri_sv] + ' (${date})'

      category.stat_var_spec[pri_sv].stat_var = pri_sv
      category.stat_var_spec[pri_sv].name = sv2name[pri_sv]

      # The per capita tile
      if _should_add_percapita(pri_sv):
        tile = column.tiles.add()
        sv_key = pri_sv + "_pc"
        tile.stat_var_key.append(sv_key)
        tile.type = subject_page_pb2.Tile.TileType.MAP
        tile.title = "Per Capita " + sv2name[pri_sv] + ' (${date})'
        category.stat_var_spec[sv_key].stat_var = pri_sv 
        category.stat_var_spec[sv_key].name = sv2name[pri_sv]
        category.stat_var_spec[sv_key].denom = "Count_Person"
        category.stat_var_spec[sv_key].unit = "%"
        category.stat_var_spec[sv_key].scaling = 100

    category.blocks.append(block)
    for sv_key, spec in stat_var_spec_map.items():
      category.stat_var_spec[sv_key].CopyFrom(spec)

  # # Contained place
  logging.info(page_config)
  return page_config
