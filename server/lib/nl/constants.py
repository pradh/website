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
"""Various constants for NL detection."""

from typing import Dict, List, Set, Union

STOP_WORDS: Set[str] = {
    'ourselves',
    'hers',
    'between',
    'yourself',
    'but',
    'again',
    'there',
    'about',
    'once',
    'during',
    'out',
    'very',
    'having',
    'with',
    'they',
    'own',
    'an',
    'be',
    'some',
    'for',
    'do',
    'its',
    'yours',
    'such',
    'into',
    'of',
    'most',
    'itself',
    'other',
    'off',
    'is',
    's',
    'am',
    'or',
    'who',
    'as',
    'from',
    'him',
    'each',
    'the',
    'themselves',
    'until',
    'below',
    'are',
    'we',
    'these',
    'your',
    'his',
    'through',
    'don',
    'nor',
    'me',
    'were',
    'her',
    'more',
    'himself',
    'this',
    'down',
    'should',
    'our',
    'their',
    'while',
    'above',
    'both',
    'up',
    'to',
    'ours',
    'had',
    'she',
    'all',
    'no',
    'when',
    'at',
    'any',
    'before',
    'them',
    'same',
    'and',
    'been',
    'have',
    'in',
    'will',
    'on',
    'does',
    'yourselves',
    'then',
    'that',
    'because',
    'what',
    'over',
    'why',
    'so',
    'can',
    'did',
    'not',
    'now',
    'under',
    'he',
    'you',
    'herself',
    'has',
    'just',
    'where',
    'too',
    'only',
    'myself',
    'which',
    'those',
    'i',
    'after',
    'few',
    'whom',
    't',
    'being',
    'if',
    'theirs',
    'my',
    'against',
    'a',
    'by',
    'doing',
    'it',
    'how',
    'further',
    'was',
    'here',
    'than',
    'tell',
    'say',
    'something',
    'thing',
    'among',
    'across',
}

# TODO: remove this special casing when a better NER model is identified which
# can always detect these.
SPECIAL_PLACES: Set[str] = {'palo alto', 'mountain view'}

# Note: These heuristics should be revisited if we change
# query preprocessing (e.g. stopwords, stemming)
QUERY_CLASSIFICATION_HEURISTICS: Dict[str, Union[List[str], Dict[
    str, List[str]]]] = {
        "Ranking": {
            "High": [
                "most",
                "top",
                "best",  # leaving here for backwards-compatibility
                "highest",
                "high",
                "smallest",
                "strongest",
                "richest",
                "sickest",
                "illest",
                "descending",
                "top to bottom",
                "highest to lowest",
            ],
            "Low": [
                "least",
                "bottom",
                "worst",  # leaving here for backwards-compatibility
                "lowest",
                "low",
                "largest",
                "weakest",
                "youngest",
                "poorest",
                "ascending",
                "bottom to top",
                "lowest to highest",
            ],
            "Best": ["best",],
            "Worst": ["worst",],
        },
        "Correlation": [
            "correlate",
            "correlated",
            "correlation",
            "relationship to",
            "relationship with",
            "relationship between",
            "related to",
            "related with",
            "related between",
            "vs",
            "versus",
        ],
        "TimeDelta": {
            "Increase": [
                "grow(n|th)",
                "increased?",
            ],
            "Decrease": [
                "decreased?",
                "shr(ink|unk)",
            ],
        },
    }

PLACE_TYPE_TO_PLURALS: Dict[str, str] = {
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
