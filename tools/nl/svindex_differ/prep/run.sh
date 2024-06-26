#!/bin/bash
# Copyright 2020 Google LLC
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

cd ../../../..
python3 -m venv .env
source .env/bin/activate
pip3 install -r tools/nl/svindex_differ/prep/requirements.txt

strip_stopwords=${1:=true}

python3 -m tools.nl.svindex_differ.prep.to_vars \
  --queryset=tools/nl/svindex_differ/queryset.csv \
  --queryset_vars=tools/nl/svindex_differ/queryset_vars.csv \
  --strip_stopwords=$1
