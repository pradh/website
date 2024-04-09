# Copyright 2024 Google LLC
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
"""Build the embeddings index by concatenating various inputs."""

# TODO: Consider adding the model name to the embeddings file for downstream
# validation.

import csv
import datetime as datetime
import glob
import json
import logging
import os
from typing import Dict, List

from absl import app
from absl import flags
from google.cloud import aiplatform
from google.cloud import storage
import lancedb
import pandas as pd
from sentence_transformers import SentenceTransformer
import utils

VERTEX_AI_PROJECT = 'datcom-website-dev'
VERTEX_AI_PROJECT_LOCATION = 'us-central1'

FLAGS = flags.FLAGS

# TODO: use only one flag from the two below and "gcs://" prefix to differentiate
# between local and GCS path.
flags.DEFINE_string('finetuned_model_gcs', '',
                    'Existing finetuned model folder name on GCS')
flags.DEFINE_string('existing_model_path', '',
                    'Path to an existing model (local)')
flags.DEFINE_string(
    'vertex_ai_prediction_endpoint_id', '',
    'The ID of vertex AI prediction endpoint.' +
    ' Not set for local Sentence Transformers based index, must be set for API-based index'
)
flags.DEFINE_string(
    'lancedb_output_path', '', 'The output path to produce LanceDB index. ' +
    'Currently always uses SentenceTransformer model.')
flags.DEFINE_string('model_name_v2', 'all-MiniLM-L6-v2', 'Model name')
flags.DEFINE_string('bucket_name_v2', 'datcom-nl-models', 'Storage bucket')
flags.DEFINE_string('embeddings_size', '', 'Embeddings size')

flags.DEFINE_list('curated_input_paths',
                  ['data/curated_input/main/sheets_svs.csv'],
                  'Curated input csv (relative) file path')

flags.DEFINE_string(
    'autogen_input_basedir', 'data/autogen_input',
    'Base path for CSVs with autogenerated SVs with name and description. '
    'The actual path is `{--autogen_input_base}/{--embeddings_size}/*.csv`.')

flags.DEFINE_string('alternatives_filepattern', 'data/alternatives/main/*.csv',
                    'File pattern (relative) for CSVs with alternatives')

flags.DEFINE_bool('dry_run', False, 'Dry run')

#
# curated_input/ + autogen_input/ + alternatives/ => preindex/ => embeddings
#

# Setting to a very high number right for now.
MAX_ALTERNATIVES_LIMIT = 50

_LANCEDB_TABLE = 'datacommons'


def _make_gcs_embeddings_filename(embeddings_size: str,
                                  model_version: str) -> str:
  now = datetime.datetime.now()
  formatted_date_string = now.strftime("%Y_%m_%d_%H_%M_%S")
  return f"embeddings_{embeddings_size}_{formatted_date_string}.{model_version}.csv"


def _make_embeddings_index_filename(embeddings_size: str,
                                    model_endpoint_id: str) -> str:
  now = datetime.datetime.now()
  formatted_date_string = now.strftime("%Y_%m_%d_%H_%M_%S")
  return f"embeddings_{embeddings_size}_{formatted_date_string}.{model_endpoint_id}.json"


def _write_intermediate_output(name2sv_dict: Dict[str, str],
                               dup_sv_rows: List[List[str]],
                               local_merged_filepath: str,
                               dup_names_filepath: str) -> None:
  sv2names = {}
  for name, sv in name2sv_dict.items():
    if sv not in sv2names:
      sv2names[sv] = []
    sv2names[sv].append(name)

  sv_list = sorted(list(sv2names.keys()))
  name_list = [';'.join(sorted(sv2names[v])) for v in sv_list]

  # Write to local_merged_filepath.
  print(
      f"Writing the concatenated dataframe after merging alternates to local file: {local_merged_filepath}"
  )
  df_svs = pd.DataFrame({'dcid': sv_list, 'sentence': name_list})
  df_svs.to_csv(local_merged_filepath, index=False)

  if dup_names_filepath:
    print(f"Writing duplicate names file: {dup_names_filepath}")
    with open(dup_names_filepath, 'w') as f:
      csv.writer(f).writerows(dup_sv_rows)


def get_embeddings(ctx, df_svs: pd.DataFrame, local_merged_filepath: str,
                   dup_names_filepath: str) -> pd.DataFrame:
  print(f"Concatenate all alternative sentences for descriptions.")
  alternate_descriptions = []
  for _, row in df_svs.iterrows():
    alternatives = []
    if row[utils.OVERRIDE_COL]:
      # Override takes precendence over everything else.
      alternatives += utils.split_alt_string(row[utils.OVERRIDE_COL])
    else:
      for col_name in [
          utils.NAME_COL,
          utils.DESCRIPTION_COL,
          utils.CURATED_ALTERNATIVES_COL,
          utils.ALTERNATIVES_COL,
      ]:
        # In order of preference, traverse the various alternative descriptions.
        alternatives += utils.split_alt_string(row[col_name])

    alt_str = utils.concat_alternatives(alternatives, MAX_ALTERNATIVES_LIMIT)
    alternate_descriptions.append(alt_str)

  assert len(df_svs) == len(alternate_descriptions)
  df_svs[utils.COL_ALTERNATIVES] = alternate_descriptions
  # Trim df
  df_svs = df_svs[[utils.DCID_COL, utils.COL_ALTERNATIVES]]

  # Dedupe texts
  (text2sv_dict, dup_sv_rows) = utils.dedup_texts(df_svs)

  # Write dcid -> texts and dups to intermediate files.
  _write_intermediate_output(text2sv_dict, dup_sv_rows, local_merged_filepath,
                             dup_names_filepath)

  print("Building embeddings")
  return utils.build_embeddings(ctx, text2sv_dict)


def build(ctx, curated_input_paths: List[str], local_merged_filepath: str,
          dup_names_filepath: str, autogen_input_filepattern: str,
          alternative_filepattern: str) -> pd.DataFrame:
  curated_input_df_list = list()
  # Read curated sv info.
  for file_path in curated_input_paths:
    try:
      print(f"Reading the curated input file: {file_path}")
      file_df = pd.read_csv(file_path, na_filter=False)
      curated_input_df_list.append(file_df)
    except:
      print("Error reading curated input file: {file_path}")

  if curated_input_df_list:
    # Use inner join to only add rows that have the same headings (which all
    # curated inputs should have the same headings)
    df_svs = pd.concat(curated_input_df_list, join="inner")
  else:
    df_svs = pd.DataFrame()

  # Append autogen CSVs if any.
  autogen_dfs = []
  for autogen_csv in sorted(glob.glob(autogen_input_filepattern)):
    print(f'Processing autogen input file: {autogen_csv}')
    autogen_dfs.append(pd.read_csv(autogen_csv).fillna(""))
  if autogen_dfs:
    df_svs = pd.concat([df_svs] + autogen_dfs)
    df_svs = df_svs.drop_duplicates(subset=utils.DCID_COL)

  # Get alternatives and add to the dataframe.
  if alternative_filepattern:
    for alt_fp in sorted(glob.glob(alternative_filepattern)):
      df_alts = utils.get_local_alternatives(
          alt_fp, [utils.DCID_COL, utils.ALTERNATIVES_COL])
      df_svs = utils.merge_dataframes(df_svs, df_alts)

  return get_embeddings(ctx, df_svs, local_merged_filepath, dup_names_filepath)


def write_row_to_jsonl(f, row):
  dcid = row[utils.DCID_COL]  # Get the DCID value
  text = row[utils.COL_ALTERNATIVES]  # Get the text
  embedding = row.drop([utils.DCID_COL, utils.COL_ALTERNATIVES
                       ]).tolist()  # Get the embeddings as a list
  f.write(
      json.dumps({
          'id': text,
          'embedding': embedding,
          'restricts': [{
              'namespace': 'dcid',
              'allow': [dcid]
          }]
      }))
  f.write('\n')


def get_lancedb_records(df) -> List[Dict]:
  dcids = df[utils.DCID_COL].values.tolist()
  sentences = df[utils.COL_ALTERNATIVES].values.tolist()
  df = df.drop(utils.DCID_COL, axis=1)
  df = df.drop(utils.COL_ALTERNATIVES, axis=1)
  vectors = df.to_numpy().tolist()
  records = []
  for d, s, v in zip(dcids, sentences, vectors):
    records.append({'dcid': d, 'sentence': s, 'vector': v})
  return records


def main(_):
  assert FLAGS.vertex_ai_prediction_endpoint_id or (FLAGS.model_name_v2 and
                                                    FLAGS.bucket_name_v2 and
                                                    FLAGS.curated_input_paths)

  assert os.path.exists(os.path.join('data'))

  if FLAGS.existing_model_path:
    assert os.path.exists(FLAGS.existing_model_path)

  use_finetuned_model = False
  use_local_model = False
  if not FLAGS.vertex_ai_prediction_endpoint_id:
    model_version = FLAGS.model_name_v2
    if FLAGS.finetuned_model_gcs:
      use_finetuned_model = True
      model_version = FLAGS.finetuned_model_gcs
    elif FLAGS.existing_model_path:
      use_local_model = True
      model_version = os.path.basename(FLAGS.existing_model_path)

  if not os.path.exists(os.path.join('data', 'preindex',
                                     FLAGS.embeddings_size)):
    os.mkdir(os.path.join('data', 'preindex', FLAGS.embeddings_size))
  local_merged_filepath = f'data/preindex/{FLAGS.embeddings_size}/sv_descriptions.csv'
  dup_names_filepath = f'data/preindex/{FLAGS.embeddings_size}/duplicate_names.csv'

  if not os.path.exists(
      os.path.join(FLAGS.autogen_input_basedir, FLAGS.embeddings_size)):
    os.mkdir(os.path.join(FLAGS.autogen_input_basedir, FLAGS.embeddings_size))
  autogen_input_filepattern = f'{FLAGS.autogen_input_basedir}/{FLAGS.embeddings_size}/*.csv'

  sc = storage.Client()
  bucket = sc.bucket(FLAGS.bucket_name_v2)
  model_endpoint = None

  if use_finetuned_model:
    ctx_no_model = utils.Context(model=None,
                                 model_endpoint=None,
                                 bucket=bucket,
                                 tmp='/tmp')
    model = utils.get_ft_model_from_gcs(ctx_no_model, model_version)
  elif use_local_model:
    logging.info("Use the local model at: %s", FLAGS.existing_model_path)
    logging.info("Extracted model version: %s", model_version)
    model = SentenceTransformer(FLAGS.existing_model_path)
  elif FLAGS.vertex_ai_prediction_endpoint_id:
    model = None
    aiplatform.init(project=VERTEX_AI_PROJECT,
                    location=VERTEX_AI_PROJECT_LOCATION)
    model_endpoint = aiplatform.Endpoint(FLAGS.vertex_ai_prediction_endpoint_id)
  else:
    model = SentenceTransformer(FLAGS.model_name_v2)

  ctx = utils.Context(model=model,
                      model_endpoint=model_endpoint,
                      bucket=bucket,
                      tmp='/tmp')

  if FLAGS.vertex_ai_prediction_endpoint_id:
    model_version = FLAGS.vertex_ai_prediction_endpoint_id
    embeddings_index_json_filename = _make_embeddings_index_filename(
        FLAGS.embeddings_size, FLAGS.vertex_ai_prediction_endpoint_id)
    embeddings_index_tmp_out_path = os.path.join(
        ctx.tmp, embeddings_index_json_filename)

  gcs_embeddings_filename = _make_gcs_embeddings_filename(
      FLAGS.embeddings_size, model_version)
  gcs_tmp_out_path = os.path.join(ctx.tmp, gcs_embeddings_filename)

  # Process all the data, produce the final dataframes, build the embeddings and
  # return the embeddings dataframe.
  # During this process, the downloaded latest SVs and Descriptions data and the
  # final dataframe with SVs and Alternates are also written to local_merged_dir.
  embeddings_df = build(ctx, FLAGS.curated_input_paths, local_merged_filepath,
                        dup_names_filepath, autogen_input_filepattern,
                        FLAGS.alternatives_filepattern)

  print(f"Saving locally to {gcs_tmp_out_path}")
  embeddings_df.to_csv(gcs_tmp_out_path, index=False)

  # Before uploading embeddings to GCS, validate them.
  print("Validating the built embeddings.")
  utils.validate_embeddings(embeddings_df, local_merged_filepath)
  print("Embeddings DataFrame is validated.")

  if not FLAGS.dry_run:
    # Finally, upload to the NL embeddings server's GCS bucket
    print("Attempting to write to GCS")
    print(f"\t GCS Path: gs://{FLAGS.bucket_name_v2}/{gcs_embeddings_filename}")
    blob = ctx.bucket.blob(gcs_embeddings_filename)
    # Since the files can be fairly large, use a 10min timeout to be safe.
    blob.upload_from_filename(gcs_tmp_out_path, timeout=600)
    print("Done uploading to gcs.")
    print(f"\t Embeddings Filename: {gcs_embeddings_filename}")
    print("\nNOTE: Please update embeddings.yaml with the Embeddings Filename")

  if FLAGS.vertex_ai_prediction_endpoint_id:
    with open(embeddings_index_tmp_out_path, 'w') as f:
      for _, row in embeddings_df.iterrows():
        write_row_to_jsonl(f, row)
    if not FLAGS.dry_run:
      # Update the jsonl file to GCS.
      # TODO: figure out which bucket to upload to and maybe include the
      # index building step here.
      pass

  if FLAGS.lancedb_output_path:
    version_dir = f'lancedb_{gcs_embeddings_filename.removesuffix(".csv")}'
    version_path = os.path.join(FLAGS.lancedb_output_path, version_dir)
    db = lancedb.connect(version_path)
    records = get_lancedb_records(embeddings_df)
    if not FLAGS.dry_run:
      # TODO: Upload to GCS
      pass
    db.create_table(_LANCEDB_TABLE, records)
    print(f'Generated LanceDB index in: {version_path}')


if __name__ == "__main__":
  app.run(main)
