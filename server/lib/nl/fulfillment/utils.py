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

from server.lib.nl.detection.types import ContainedInPlaceType

# TODO: Add area
PLACE_DEFAULT_VARS = [
    'Count_Person', 'Count_Household',
    'Amount_EconomicActivity_GrossDomesticProduction_RealValue',
    'Amount_EconomicActivity_GrossDomesticProduction_Nominal'
]

SCHOOL_DEFAULT_VARS = [
    'Count_Student',
    'Count_Teacher',
    'Percent_Student_AsAFractionOf_Count_Teacher',
]

SCHOOL_TYPES = frozenset([
    ContainedInPlaceType.SCHOOL,
    ContainedInPlaceType.ELEMENTARY_SCHOOL,
    ContainedInPlaceType.MIDDLE_SCHOOL,
    ContainedInPlaceType.HIGH_SCHOOL,
    ContainedInPlaceType.PRIMARY_SCHOOL,
    ContainedInPlaceType.PRIVATE_SCHOOL,
    ContainedInPlaceType.PUBLIC_SCHOOL,
])


def get_default_vars(pt: ContainedInPlaceType):
  if pt in SCHOOL_TYPES:
    return SCHOOL_DEFAULT_VARS
  return PLACE_DEFAULT_VARS