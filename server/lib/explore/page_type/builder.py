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

from dataclasses import dataclass
from typing import Dict, List

from server.config.subject_page_pb2 import SubjectPageConfig
from server.lib.explore.params import is_sdg
from server.lib.nl.common import utils
import server.lib.nl.common.variable as var_lib
from server.lib.nl.config_builder import base
import server.lib.nl.detection.types as dtypes
import server.lib.nl.fulfillment.types as ftypes
import server.lib.nl.fulfillment.utils as futils

# Helper class to build chart config for Explore page.


class Builder:

  def __init__(self, state: ftypes.PopulateState, env_config: base.Config,
               sv2thing: ftypes.SV2Thing, num_chart_vars: int):
    self.uttr = state.uttr
    self.page_config = SubjectPageConfig()
    self.env_config = env_config
    self.sv2thing = sv2thing
    self.num_chart_vars = num_chart_vars

    self.is_place_comparison = False
    if futils.classifications_of_type_from_utterance(
        state.uttr, dtypes.ClassificationType.COMPARISON):
      self.is_place_comparison = True

    self.is_var_comparison = False
    if futils.classifications_of_type_from_utterance(
        state.uttr, dtypes.ClassificationType.CORRELATION):
      self.is_var_comparison = True

    metadata = self.page_config.metadata
    main_place = state.uttr.places[0]
    metadata.place_dcid.append(main_place.dcid)
    if state.place_type:
      metadata.contained_place_types[main_place.place_type] = \
        state.place_type.value

    self.plotted_orig_vars = []
    self.category = None
    self.block = None
    self.column = None

  def nopc(self):
    return self.env_config.nopc_vars

  def new_category(self, title, dcid, description=''):
    self.category = self.page_config.categories.add()
    self.category.title = title
    if title and description:
      self.category.description = description
    if dcid:
      self.category.dcid = dcid

  def new_block(self, title='', description='', enable_pc=False, footnote=''):
    self.block = self.category.blocks.add()
    self.block.title = base.decorate_block_title(title=title)
    if enable_pc:
      self.block.denom = 'Count_Person'
    if self.block.title and description:
      self.block.description = description
    if footnote:
      self.block.footnote = footnote

  def new_column(self, cv: ftypes.ChartVars):
    # We are adding a chart for real post existence check.
    # Add all the orig-vars.  We'll use them to define
    # the topic page.
    if cv and cv.orig_sv:
      osv = cv.orig_sv
      if not (self.plotted_orig_vars and
              self.plotted_orig_vars[-1]['dcid'] == osv):
        t = 'StatisticalVariable' if utils.is_sv(osv) else 'Topic'
        self.plotted_orig_vars.append({
            'dcid': osv,
            'name': self.sv2thing.name.get(osv, ''),
            'types': [t],
        })

    self.column = self.block.columns.add()
    return self.column

  def update_sv_spec(self, stat_var_spec_map):
    for sv_key, spec in stat_var_spec_map.items():
      self.category.stat_var_spec[sv_key].CopyFrom(spec)

  def enable_pc(self, cv: ftypes.ChartVars) -> bool:
    return all([
        var_lib.is_percapita_relevant(v, self.env_config.nopc_vars)
        for v in cv.svs
    ])

  # 1. If there are duplicate charts, drops the subsequent tiles.
  # 2. As a result of the dedupe if any column, block or category
  #    is empty, deletes it.
  # 3. Finally, if there is a singleton block in a category and both
  #    the block and category have names, drop the block name.
  def cleanup_config(self):
    base.trim_config(self.page_config)

    # Nothing more to do (like resetting title) if SDG.
    if is_sdg(self.uttr.insight_ctx):
      return

    for cat in self.page_config.categories:
      if self.plotted_orig_vars and self.plotted_orig_vars[0][
          'dcid'] == cat.dcid:
        # The overall topic matches the category, so clear out the title.
        cat.title = ''

      if len(cat.blocks) == 1 and cat.title and cat.blocks[0].title:
        # Note: Category title will be topic name and block title
        # will be SVPG.  The latter is better curated, so for now
        # use that.
        cat.blocks[0].title = ''


@dataclass
class ConfigResp:
  config_pb: SubjectPageConfig
  user_message: str
  plotted_orig_vars: List[Dict]
