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

from server.config.subject_page_pb2 import StatVarSpec
from server.config.subject_page_pb2 import Tile
from server.lib.nl.config_builder import base


def gauge_block_for_percent(column, place, sv, sv2thing: base.SV2Thing):
  chart_title = base.decorate_chart_title(title=sv2thing.name[sv], place=place)

  tile = Tile(type=Tile.TileType.GAUGE, title=chart_title, stat_var_key=[sv])
  tile.gauge_tile_spec.range.min = 0.0001
  tile.gauge_tile_spec.range.max = 100
  tile.gauge_tile_spec.colors.append('blue')
  # TODO: Drop this once the tile bug necessitating this is fixed
  tile.gauge_tile_spec.colors.append('blue')
  stat_var_spec_map = {}
  stat_var_spec_map[sv] = StatVarSpec(stat_var=sv,
                                      name=sv2thing.name[sv],
                                      unit=sv2thing.unit[sv])
  column.tiles.append(tile)
  return stat_var_spec_map
