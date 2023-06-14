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

/**
 * Options for NL.
 */

import _ from "lodash";
import React from "react";
import { FormGroup, Input, Label } from "reactstrap";

import { NL_URL_PARAMS } from "./nl_constants";

interface NLOptionsPropType {
  indexType: string;
  setIndexType: (idx: string) => void;
  useLLM: boolean;
  setUseLLM: (v: boolean) => void;
}

export function NLOptions(props: NLOptionsPropType): JSX.Element {
  return (
    <div className="nl-options-row">
      <div className="nl-options-label">Detection:</div>
      <div className="nl-options-input-radio">
        <FormGroup>
          <Label>
            <Input
              checked={!props.useLLM}
              id="nl-heuristics"
              type="radio"
              value={0}
              onChange={() => {
                props.setUseLLM(false);
              }}
            />
            Heuristics Based
          </Label>
          <Label>
            <Input
              checked={props.useLLM}
              id="nl-llm"
              type="radio"
              value={1}
              onChange={() => {
                props.setUseLLM(true);
              }}
            />
            LLM Based (experimental)
          </Label>
        </FormGroup>
      </div>
      <div className="nl-options-label">Embeddings:</div>
      <div className="nl-options-input-radio">
        <FormGroup>
          <Label>
            <Input
              checked={props.indexType === NL_URL_PARAMS.SMALL}
              id="nl-small-index"
              type="radio"
              value={NL_URL_PARAMS.SMALL}
              onChange={() => {
                props.setIndexType(NL_URL_PARAMS.SMALL);
              }}
            />
            Small-1K
          </Label>
          <Label>
            <Input
              checked={props.indexType === NL_URL_PARAMS.MEDIUM}
              id="nl-medium-index"
              type="radio"
              value={NL_URL_PARAMS.MEDIUM}
              onChange={() => {
                props.setIndexType(NL_URL_PARAMS.MEDIUM);
              }}
            />
            Medium-5K (experimental)
          </Label>
        </FormGroup>
      </div>
    </div>
  );
}
