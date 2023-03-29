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
"""Managing the embeddings."""
from dataclasses import dataclass
import logging
import os
import re
from typing import Dict, List, Union

from datasets import load_dataset
from google.cloud import storage
from sentence_transformers import SentenceTransformer
from sentence_transformers.util import semantic_search
import torch

from nl_server import query_util
import nl_server.gcs as gcs
from server.lib.nl import utils

TEMP_DIR = '/tmp/'
MODEL_NAME = 'all-MiniLM-L6-v2'

# A value higher than the highest score.
_INIT_SCORE = 1.1

# Scores below this are ignored.
_SV_SCORE_THRESHOLD = 0.5

# If the difference between successive scores exceeds this threshold, then SVs at
# the lower score and below are ignored.
_MULTI_SV_SCORE_DIFFERENTIAL = 0.05

_NUM_CANDIDATES_PER_NSPLIT = 3


@dataclass
class VarCandidates:
  # The below are sorted and parallel lists.
  svs: List[str]
  scores: List[float]
  sv2sentences: Dict[str, List[str]]


@dataclass
class MultiVarCandidatePart:
  query_part: str
  svs: List[str]
  scores: List[float]


@dataclass
class MultiVarCandidate:
  parts: List[MultiVarCandidatePart]
  # Aggregate score
  score: float
  # Is this candidate based on a split computed from delimiters?
  delim_based: bool


@dataclass
class MultiVarCandidates:
  candidates: List[MultiVarCandidate]
  sv2sentences: Dict[str, List[str]]


class Embeddings:
  """Manages the embeddings."""

  def __init__(self, embeddings_file: str) -> None:
    self.embeddings_file = embeddings_file
    self.model = SentenceTransformer(MODEL_NAME)
    self.dataset_embeddings: torch.Tensor = None
    self._download_embeddings()
    self.dcids: List[str] = []
    self.sentences: List[str] = []

    logging.info('Loading embeddings file')
    try:
      ds = load_dataset('csv',
                        data_files=os.path.join(TEMP_DIR,
                                                f'{self.embeddings_file}'))
    except:
      error_str = "No embedding could be loaded."
      logging.error(error_str)
      raise Exception("No embedding could be loaded.")

    self.df = ds["train"].to_pandas()
    self.dcids = self.df['dcid'].values.tolist()
    self.df = self.df.drop('dcid', axis=1)
    # Also get the sentence mappings.
    self.sentences = []
    if 'sentence' in self.df:
      self.sentences = self.df['sentence'].values.tolist()
      self.df = self.df.drop('sentence', axis=1)

    self.dataset_embeddings = torch.from_numpy(self.df.to_numpy()).to(
        torch.float)

  def _download_embeddings(self):
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name=gcs.BUCKET)
    blob = bucket.get_blob(self.embeddings_file)
    # Download
    blob.download_to_filename(os.path.join(TEMP_DIR, self.embeddings_file))

  def get_embedding_at_index(self, index: int) -> List[float]:
    if index < 0 or index >= len(self.df):
      logging.error(
          f"get_embedding_at_index() got an index out of range. index = {index}. len(df) = {len(self.df)}"
      )
      return []

    return self.df.iloc[index].values.tolist()

  def get_embedding(self, query: str) -> List[float]:
    return self.model.encode(query).tolist()

  def detect_svs(self, orig_query: str) -> Dict[str, Union[Dict, List]]:
    query_monovar = utils.remove_stop_words(orig_query,
                                            query_util.ALL_STOP_WORDS)

    # Search embeddings for single SV.
    result_monovar = self._search_embeddings([query_monovar])[query_monovar]

    # Try to detect multiple SVs.  Use the original query.
    result_multivar = self._detect_multiple_svs(orig_query)

    return {
        'SV': result_monovar.svs,
        'CosineScore': result_monovar.scores,
        'SV_to_Sentences': result_monovar.sv2sentences,
        'MultiSV': _multivar_candidates_to_dict(result_multivar)
    }

  # Detects one or more SVs from the query.
  def _detect_multiple_svs(self, query: str) -> MultiVarCandidates:
    querysets = query_util.prepare_multivar_querysets(query)
    result = MultiVarCandidates(candidates=[], sv2sentences={})

    # Make a distinct set of query strings
    all_queries = set()
    for qs in querysets:
      for c in qs.combinations:
        for p in c.parts:
          all_queries.add(p)
    if not all_queries:
      return result

    query2result = self._search_embeddings(list(all_queries))

    #
    # We take the lowest score from the top SV from the query-parts in a
    # queryset (ignoring any queryset with a score below threshold).
    #
    # Pick one candidate with the highest such score for every num-stat-vars
    # (ranging from 1 to 4). An average may let in a poor SV for a word sequence.
    #
    # TODO: Come up with a better ranking function.
    #
    for qs in querysets:
      candidates: List[MultiVarCandidate] = []
      for c in qs.combinations:
        if not c or not c.parts:
          continue

        total = 0
        candidate = MultiVarCandidate(parts=[],
                                      delim_based=qs.delim_based,
                                      score=-1)
        lowest = _INIT_SCORE
        for q in c.parts:
          r = query2result.get(
              q, VarCandidates(svs=[], scores=[], sv2sentences={}))
          part = MultiVarCandidatePart(query_part=q, svs=[], scores=[])
          score = 0  # Lowest score
          if r.svs:
            limit = _pick_top_k(r)
            if limit > 0:
              part.svs = r.svs[:limit]
              part.scores = [round(s, 4) for s in r.scores[:limit]]
              score = r.scores[0]

          if score < lowest:
            lowest = score
          total += score
          candidate.parts.append(part)

        if lowest < _SV_SCORE_THRESHOLD:
          continue

        candidate.score = total / len(c.parts)
        candidates.append(candidate)
      if candidates:
        # Pick the top candidate.
        candidates.sort(key=lambda c: c.score, reverse=True)
        result.candidates.extend(candidates[:_NUM_CANDIDATES_PER_NSPLIT])

    # Sort the results by score.
    result.candidates.sort(key=lambda c: c.score, reverse=True)

    # Get all SVs
    all_svs = set()
    for c in result.candidates:
      for p in c.parts:
        all_svs.update(p.svs)

    # Add sentences
    for _, res in query2result.items():
      for sv, sentences in res.sv2sentences.items():
        if sv in all_svs:
          result.sv2sentences[sv] = sentences

    return result

  def _search_embeddings(self, queries: List[str]) -> Dict[str, VarCandidates]:
    query_embeddings = self.model.encode(queries)
    hits = semantic_search(query_embeddings, self.dataset_embeddings, top_k=20)

    query2sv2sentence2score: Dict[str, Dict[str, Dict[str, float]]] = {}
    query2sv2score: Dict[str, Dict[str, float]] = {}
    for i, hit in enumerate(hits):
      q = queries[i]
      query2sv2score[q] = {}
      query2sv2sentence2score[q] = {}
      for ent in hit:
        score = ent['score']
        for dcid in self.dcids[ent['corpus_id']].split(','):
          # Prefer the top score.
          if dcid not in query2sv2score[q]:
            query2sv2score[q][dcid] = score
            query2sv2sentence2score[q][dcid] = {}

          if ent['corpus_id'] >= len(self.sentences):
            continue
          sentence = self.sentences[ent['corpus_id']]
          query2sv2sentence2score[q][dcid][sentence] = score

    query2result: Dict[str, VarCandidates] = {}

    for q, sv2score in query2sv2score.items():
      sv2score_sorted = [(k, v) for (
          k,
          v) in sorted(sv2score.items(), key=lambda item: item[1], reverse=True)
                        ]
      svs = [k for (k, _) in sv2score_sorted]
      scores = [v for (_, v) in sv2score_sorted]
      query2result[q] = VarCandidates(svs=svs, scores=scores, sv2sentences={})

    for q, sv2sentence2score in query2sv2sentence2score.items():
      query2result[q].sv2sentences = {}
      for sv, sentence2score in sv2sentence2score.items():
        query2result[q].sv2sentences[sv] = []
        for sentence, score in sorted(sentence2score.items(),
                                      key=lambda item: item[1],
                                      reverse=True):
          score = round(score, 4)
          query2result[q].sv2sentences[sv].append(sentence + f' ({score})')

    return query2result


def _pick_top_k(candidates: VarCandidates) -> int:
  k = 0
  first = candidates.scores[0]
  for i in range(len(candidates.scores)):
    if candidates.scores[i] < _SV_SCORE_THRESHOLD:
      break
    if i > 0 and first - candidates.scores[i] > _MULTI_SV_SCORE_DIFFERENTIAL:
      break
    k += 1
  return k


def _multivar_candidates_to_dict(candidates: MultiVarCandidates) -> Dict:
  result = {'Candidates': [], 'SV_to_Sentences': candidates.sv2sentences}
  for c in candidates.candidates:
    c_dict = {
        'Parts': [],
        'AggCosineScore': round(c.score, 4),
        'DelimBased': c.delim_based,
    }
    for p in c.parts:
      p_dict = {'QueryPart': p.query_part, 'SV': p.svs, 'CosineScore': p.scores}
      c_dict['Parts'].append(p_dict)
    result['Candidates'].append(c_dict)
  return result
