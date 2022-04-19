/**
 * Copyright 2022 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
export const BQ_QUERY_HEADER_COMMENT =
  "#\n"
  "# To use this query, please link Data Commons to your GCP Project (bit.ly/dc-bq-ah).\n"
  "# For more information on querying Data Commons, see bit.ly/dc-bq-doc.\n"
  "#\n";
const BQ_LINK =
  "https://pantheon.corp.google.com/bigquery;create-new-query-tab=";

/**
 * Sets up the bq button if it is in the html.
 * @returns
 */
export function setUpBqButton(getSqlQuery: () => string): HTMLAnchorElement {
  const bqLink = document.getElementById("bq-link") as HTMLAnchorElement;
  if (bqLink) {
    bqLink.onclick = () => {
      const query = getSqlQuery();
      const encodedQuery = encodeURIComponent(query)
        .replace(/\(/g, "%28")
        .replace(/\)/g, "%29");
      const url = BQ_LINK + encodedQuery;
      window.open(url, "_blank", "noreferrer");
    };
  }
  return bqLink;
}
