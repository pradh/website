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

# TODO: Consider including cosine scores in the comparison.

import csv
import difflib
import os
import re

from absl import app
from absl import flags
from jinja2 import Environment
from jinja2 import FileSystemLoader

from nl_server import gcs
from nl_server.embeddings import Embeddings

_SV_THRESHOLD = 0.5
_NUM_SVS = 10

FLAGS = flags.FLAGS

flags.DEFINE_string(
    'base', '', 'Base index. Can be a versioned embeddings file name on GCS '
    'or a local file with absolute path')
flags.DEFINE_string(
    'test', '', 'Test index. Can be a versioned embeddings file name on GCS '
    'or a local file with absolute path')
flags.DEFINE_string('queryset', '', 'Full path to queryset CSV')
flags.DEFINE_string('run_name', '', 'Name of the run')

_TEMPLATE = 'tools/nl/svindex_differ/template.html'
_FILE_PATTERN = r'embeddings_.*_\d{4}_\d{2}_\d{2}_\d{2}_\d{2}_\d{2}\.csv'


def _report():
  return f'/tmp/diff_report_{FLAGS.run_name}.html'


def _diagnosis_csv():
  return f'/tmp/diff_diagnosis_{FLAGS.run_name}.csv'


def _prune(res):
  sv_result = []
  display_result = []
  for i in range(len(res['SV'])):
    if i < _NUM_SVS and res['CosineScore'][i] >= _SV_THRESHOLD:
      sv = res['SV'][i]
      score_str = str(round(res["CosineScore"][i], 3))
      sv_result.append(sv)
      display_result.append(f'{sv}  ({score_str})')
  return sv_result, display_result


def _maybe_copy(file):
  if re.match(_FILE_PATTERN, file):
    lpath = gcs.local_path(file)
    if os.path.exists(lpath):
      return lpath
    return gcs.download_embeddings(file)
  assert file.startswith('/'), \
    f'File should either be {_FILE_PATTERN} or an absolute local path'
  return file


def _diff_table(base, test):
  return difflib.HtmlDiff().make_table(base, test)


def run_diff(base_file, test_file, query_file, report_file, diagnosis_file):
  env = Environment(loader=FileSystemLoader(os.path.dirname(_TEMPLATE)))
  env.filters['diff_table'] = _diff_table
  template = env.get_template(os.path.basename(_TEMPLATE))

  base = Embeddings(base_file)
  test = Embeddings(test_file)

  diffs = []
  csv_output = [['Query', 'Win/Loss', 'Diagnosis']]
  with open(query_file) as f:
    idx = 1
    for row in csv.reader(f):
      if not row:
        continue
      query = row[0].strip()
      if not query or query.startswith('#') or query.startswith('//'):
        continue
      assert ';' not in query, 'Multiple query not yet supported'
      base_svs, base_display = _prune(base.detect_svs(query))
      test_svs, test_display = _prune(test.detect_svs(query))
      if base_svs != test_svs:
        diffs.append((query, base_display, test_display))
        csv_output.append([f'{idx}: {query}', '', ''])
        idx += 1

  with open(report_file, 'w') as f:
    f.write(
        template.render(base_file=FLAGS.base,
                        test_file=FLAGS.test,
                        diff_table=_diff_table,
                        diffs=diffs))

  with open(diagnosis_file, 'w') as f:
    csv.writer(f).writerows(csv_output)

  print('')
  print(f'Report written to {report_file}')
  print(f'Diagnosis file written to {diagnosis_file}')
  print('')


def main(_):
  assert FLAGS.base and FLAGS.test and FLAGS.queryset and FLAGS.run_name
  base_file = _maybe_copy(FLAGS.base)
  test_file = _maybe_copy(FLAGS.test)
  run_diff(base_file, test_file, FLAGS.queryset, _report(), _diagnosis_csv())


if __name__ == "__main__":
  app.run(main)
