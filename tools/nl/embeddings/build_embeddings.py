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
"""Build the embeddings index by concatenating various inputs."""

# TODO: Consider adding the model name to the embeddings file for downstream
# validation.

from dataclasses import dataclass
import datetime as datetime
import glob
import os
from typing import Any, Dict, List, Set, Tuple

from absl import app
from absl import flags
from google.cloud import storage
import gspread
import pandas as pd
from sentence_transformers import SentenceTransformer

FLAGS = flags.FLAGS

flags.DEFINE_string('model_name_v2', 'all-MiniLM-L6-v2', 'Model name')
flags.DEFINE_string('bucket_name_v2', 'datcom-nl-models', 'Storage bucket')

flags.DEFINE_string('local_sheets_csv_filepath',
                    'data/curated_input/sheets_svs.csv',
                    'Local Sheets csv (relative) file path')
flags.DEFINE_string(
    'sheets_url',
    'https://docs.google.com/spreadsheets/d/1-QPDWqD131LcDTZ4y_nnqllh66W010HDdows1phyneU',
    'Google Sheets Url for the latest SVs')
flags.DEFINE_string('worksheet_name', 'Demo_SVs',
                    'Worksheet name in the Google Sheets file')

flags.DEFINE_string(
    'autogen_input_filepattern', 'data/autogen_input/*.csv',
    'File pattern (relative) for CSVs with autogenerated '
    'SVs with name and description')

flags.DEFINE_string('alternatives_filepattern', 'data/alternatives/*.csv',
                    'File pattern (relative) for CSVs with alternatives')

#
# curated_input/ + autogen_input/ + alternatives/ => preindex/ => embeddings
#

# Col names in the input files/sheets.
DCID_COL = 'dcid'

SHEETS_NAME_COL = 'Name'
SHEETS_DESCRIPTION_COL = 'Description'
SHEETS_ALTERNATIVES_COL = 'Curated_Alternatives'
SHEETS_OVERRIDE_COL = 'Override_Alternatives'

CSV_ALTERNATIVES_COL = 'Alternatives'

# Col names in the concatenated dataframe.
COL_ALTERNATIVES = 'sentence'

# Setting to a very high number right for now.
MAX_ALTERNATIVES_LIMIT = 50


def _add_sv(name: str, sv: str, text2sv: Dict[str, Set[str]]) -> None:
  if not name:
    return

  if name not in text2sv:
    text2sv[name] = set()

  text2sv[name].add(sv)


def _get_texts_dcids(df: pd.DataFrame) -> Tuple[List[str], List[str]]:
  """Extract an ordered list of alternatives (texts) and the corresponding StatVar dcids."""
  text2sv_dict = {}
  for _, row in df.iterrows():
    sv = row[DCID_COL].strip()

    # All alternative sentences are retrieved from COL_ALTERNATIVES, which
    # are expected to be delimited by ";" (semi-colon).
    if COL_ALTERNATIVES in row:
      alternatives = row[COL_ALTERNATIVES].split(';')

      for alt in alternatives:
        alt = alt.strip()
        _add_sv(alt, sv, text2sv_dict)

  texts = sorted(list(text2sv_dict.keys()))
  dcids = [','.join(sorted(text2sv_dict[k])) for k in texts]

  return (texts, dcids)


def _trim_columns(df: pd.DataFrame) -> pd.DataFrame:
  cols = [DCID_COL, COL_ALTERNATIVES]
  return df[cols]


def _two_digits(number: int) -> str:
  return str(number).zfill(2)


def _make_gcs_embeddings_filename() -> str:
  now = datetime.datetime.now()

  month_str = _two_digits(now.month)
  day_str = _two_digits(now.day)
  hour_str = _two_digits(now.hour)
  minute_str = _two_digits(now.minute)
  second_str = _two_digits(now.second)

  return f"embeddings_{now.year}_{month_str}_{day_str}_{hour_str}_{minute_str}_{second_str}.csv"


def _merge_dataframes(df_1: pd.DataFrame, df_2: pd.DataFrame) -> pd.DataFrame:
  # In case there is a column (besides DCID_COL) which is common, the merged copy
  # will contain two columns (one with a postfix _x and one with a postfix _y.
  # Concatenate the two to produce a final version.
  df_1 = df_1.merge(df_2, how='left', on=DCID_COL,
                    suffixes=("_x", "_y")).fillna("")

  # Determine the columns which were common.
  common_cols = set()
  for col in df_1.columns:
    if col.endswith("_x") or col.endswith("_y"):
      common_cols.add(col.replace("_x", "").replace("_y", ""))

  # Replace the common columns with their concatenation.
  for col in common_cols:
    df_1[col] = df_1[f"{col}_x"].str.cat(df_1[f"{col}_y"], sep=";")
    df_1[col] = df_1[col].replace(to_replace="^;", value="", regex=True)
    df_1 = df_1.drop(columns=[f"{col}_x", f"{col}_y"])

  return df_1


def _concat_alternatives(alternatives: List[str],
                         max_alternatives,
                         delimiter=";") -> str:
  alts = set(alternatives[0:max_alternatives])
  return f"{delimiter}".join(sorted(alts))


def _split_alt_string(alt_string: str) -> List[str]:
  alts = []
  for alt in alt_string.split(";"):
    if alt:
      alts.append(alt.strip())
  return alts


def _build_embeddings(ctx, texts: List[str], dcids: List[str]) -> pd.DataFrame:
  assert len(texts) == len(dcids)

  embeddings = ctx.model.encode(texts, show_progress_bar=True)
  embeddings = pd.DataFrame(embeddings)
  embeddings[DCID_COL] = dcids
  embeddings[COL_ALTERNATIVES] = texts
  return embeddings


def _extract_sentences(filepath: str, sentences: set):
  dcid_sentence_df = pd.read_csv(filepath).fillna("")
  for alts in dcid_sentence_df["sentence"].values:
    for s in alts.split(";"):
      if not s:
        continue
      sentences.add(s)


def _validateEmbeddings(embeddings_df: pd.DataFrame,
                        output_dcid_sentences_filepath: str,
                        autogen_input_filepattern: str) -> None:
  # Verify that embeddings were created for all DCIDs and Sentences.
  sentences = set()
  _extract_sentences(output_dcid_sentences_filepath, sentences)
  for autogen_file in sorted(glob.glob(autogen_input_filepattern)):
    _extract_sentences(autogen_file, sentences)

  # Verify that each of the texts in the embeddings_df is in the sentences set
  # and that all the sentences in the set are in the embeddings_df. Finally, also
  # verify that embeddings_df has no duplicate sentences.
  embeddings_sentences = embeddings_df['sentence'].values
  embeddings_sentences_unique = set()
  for s in embeddings_sentences:
    assert s in sentences, f"Embeddings sentence not found in processed output file. Sentence: {s}"
    assert s not in embeddings_sentences_unique, f"Found multiple instances of sentence in embeddings. Sentence: {s}."
    embeddings_sentences_unique.add(s)

  for s in sentences:
    assert s in embeddings_sentences_unique, f"Output File sentence not found in Embeddings. Sentence: {s}"

  # Verify that the number of columns = length of the embeddings vector + one each for the
  # dcid and sentence columns.
  assert len(embeddings_df.columns), 384 + 2


def get_sheets_data(ctx, sheets_url: str, worksheet_name: str) -> pd.DataFrame:
  sheet = ctx.gs.open_by_url(sheets_url).worksheet(worksheet_name)
  df = pd.DataFrame(sheet.get_all_records()).fillna("")
  return df


def get_local_alternatives(local_filename: str,
                           local_col_names: List[str]) -> pd.DataFrame:
  df = pd.read_csv(local_filename).fillna("")
  df = df[local_col_names]
  return df


def get_embeddings(ctx, df_svs: pd.DataFrame,
                   local_merged_filepath: str) -> pd.DataFrame:
  print(f"Concatenate all alternative sentences for descriptions.")
  alternate_descriptions = []
  for _, row in df_svs.iterrows():
    alternatives = []
    if row[SHEETS_OVERRIDE_COL]:
      # Override takes precendence over everything else.
      alternatives += _split_alt_string(row[SHEETS_OVERRIDE_COL])
    else:
      for col_name in [
          SHEETS_NAME_COL,
          SHEETS_DESCRIPTION_COL,
          SHEETS_ALTERNATIVES_COL,
          CSV_ALTERNATIVES_COL,
      ]:
        # In order of preference, traverse the various alternative descriptions.
        alternatives += _split_alt_string(row[col_name])

    alt_str = _concat_alternatives(alternatives, MAX_ALTERNATIVES_LIMIT)
    alternate_descriptions.append(alt_str)

  assert len(df_svs) == len(alternate_descriptions)
  df_svs[COL_ALTERNATIVES] = alternate_descriptions

  # Write to local_merged_filepath.
  print(
      f"Writing the concatenated dataframe after merging alternates to local file: {local_merged_filepath}"
  )
  df_svs[[DCID_COL, COL_ALTERNATIVES]].to_csv(local_merged_filepath,
                                              index=False)

  # Build embeddings.
  print("Getting texts, dcids and embeddings.")
  df_svs = _trim_columns(df_svs)
  (texts, dcids) = _get_texts_dcids(df_svs)

  print("Building embeddings")
  return _build_embeddings(ctx, texts, dcids)


def build(ctx, sheets_url: str, worksheet_name: str,
          local_sheets_csv_filepath: str, local_merged_filepath: str,
          autogen_input_filepattern: str,
          alternative_filepattern: str) -> pd.DataFrame:
  # First download the latest file from sheets.
  print(
      f"Downloading the latest sheets data from: {sheets_url} (worksheet: {worksheet_name})"
  )
  df_svs = get_sheets_data(ctx, sheets_url, worksheet_name)
  print(f"Downloaded {len(df_svs)} rows and {len(df_svs.columns)} columns.")

  # Write this downloaded file to local.
  print(
      f"Writing the downloaded dataframe to local at: {local_sheets_csv_filepath}"
  )
  df_svs.to_csv(local_sheets_csv_filepath, index=False)

  # Append autogen CSVs if any.
  autogen_dfs = []
  for autogen_csv in sorted(glob.glob(autogen_input_filepattern)):
    print(f'Processing autogen input file: {autogen_csv}')
    autogen_dfs.append(pd.read_csv(autogen_csv).fillna(""))
  if autogen_dfs:
    df_svs = pd.concat([df_svs] + autogen_dfs)
    df_svs = df_svs.drop_duplicates(subset=DCID_COL)

  # Get alternatives and add to the dataframe.
  for alt_fp in sorted(glob.glob(alternative_filepattern)):
    df_alts = get_local_alternatives(alt_fp, [DCID_COL, CSV_ALTERNATIVES_COL])
    df_svs = _merge_dataframes(df_svs, df_alts)

  return get_embeddings(ctx, df_svs, local_merged_filepath)


@dataclass
class Context:
  # gspread client
  gs: Any
  # Model
  model: Any
  # GCS storage bucket
  bucket: Any
  # Temp dir
  tmp: str


def main(_):
  assert FLAGS.model_name_v2 and FLAGS.bucket_name_v2 and FLAGS.local_sheets_csv_filepath and FLAGS.sheets_url and FLAGS.worksheet_name

  assert os.path.exists(os.path.join('data'))

  local_merged_filepath = 'data/preindex/sv_descriptions.csv'

  gs = gspread.oauth()
  sc = storage.Client()
  bucket = sc.bucket(FLAGS.bucket_name_v2)
  model = SentenceTransformer(FLAGS.model_name_v2)

  ctx = Context(gs=gs, model=model, bucket=bucket, tmp='/tmp')

  gcs_embeddings_filename = _make_gcs_embeddings_filename()
  gcs_tmp_out_path = os.path.join(ctx.tmp, gcs_embeddings_filename)

  # Process all the data, produce the final dataframes, build the embeddings and return the embeddings dataframe.
  # During this process, the downloaded latest SVs and Descriptions data and the
  # final dataframe with SVs and Alternates are also written to local_merged_filepath.
  embeddings_df = build(ctx, FLAGS.sheets_url, FLAGS.worksheet_name,
                        FLAGS.local_sheets_csv_filepath, local_merged_filepath,
                        FLAGS.autogen_input_filepattern,
                        FLAGS.alternatives_filepattern)

  print(f"Saving locally to {gcs_tmp_out_path}")
  embeddings_df.to_csv(gcs_tmp_out_path, index=False)

  # Before uploading embeddings to GCS, validate them.
  print("Validating the built embeddings.")
  _validateEmbeddings(embeddings_df, local_merged_filepath,
                      FLAGS.autogen_input_filepattern)
  print("Embeddings DataFrame is validated.")

  # Finally, upload to the NL embeddings server's GCS bucket
  print("Attempting to write to GCS")
  print(f"\t GCS Path: gs://{FLAGS.bucket_name_v2}/{gcs_embeddings_filename}")
  blob = ctx.bucket.blob(gcs_embeddings_filename)
  blob.upload_from_filename(gcs_tmp_out_path)
  print("Done uploading to gcs.")
  print(f"\t Embeddings Filename: {gcs_embeddings_filename}")
  print("\nNOTE: Please update model.yaml with the Embeddings Filename")


if __name__ == "__main__":
  app.run(main)
