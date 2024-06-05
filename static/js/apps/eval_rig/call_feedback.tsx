/**
 * Copyright 2024 Google LLC
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

/* Component to record feedback for a call within a query */

import React, { useContext, useEffect, useState } from "react";
import { Button } from "reactstrap";

import { loadSpinner, removeSpinner } from "../../shared/util";
import {
  DC_CALL_SHEET,
  DC_QUESTION_COL,
  DC_RESPONSE_COL,
  DC_STAT_COL,
  LLM_STAT_COL,
} from "./constants";
import { AppContext, SessionContext } from "./context";
import { getCallData, saveToSheet, saveToStore } from "./data_store";
import { FeedbackNavigation } from "./feedback_navigation";
import { OneQuestion } from "./one_question";
import { EvalInfo, Response } from "./types";

const LOADING_CONTAINER_ID = "form-container";
const EMPTY_RESPONSE = {
  dcResponse: "",
  llmStat: "",
  question: "",
};

export enum FormStatus {
  NotStarted = 1,
  InProgress = 2,
  Completed = 3,
  Submitted = 4,
}

export function CallFeedback(): JSX.Element {
  const { allCall, doc, sheetId, userEmail } = useContext(AppContext);
  const { sessionQueryId, sessionCallId } = useContext(SessionContext);

  const [evalInfo, setEvalInfo] = useState<EvalInfo | null>(null);
  const [response, setResponse] = useState<Response>(EMPTY_RESPONSE);
  const [status, setStatus] = useState<FormStatus>(null);
  const [applyToNext, setApplyToNext] = useState(false);

  useEffect(() => {
    getCallData(sheetId, sessionQueryId, sessionCallId).then((data) => {
      if (data) {
        setResponse(data as Response);
        setStatus(FormStatus.Submitted);
      } else {
        if (applyToNext) {
          setStatus(FormStatus.Completed);
          return;
        }
        setResponse(EMPTY_RESPONSE);
        setStatus(FormStatus.NotStarted);
      }
    });
  }, [sheetId, sessionQueryId, sessionCallId, applyToNext]);

  useEffect(() => {
    const sheet = doc.sheetsByTitle[DC_CALL_SHEET];
    if (!(sessionQueryId in allCall)) {
      setEvalInfo(null);
      return;
    }
    const rowIdx = allCall[sessionQueryId][sessionCallId];
    sheet.getRows({ offset: rowIdx - 1, limit: 1 }).then((rows) => {
      const row = rows[0];
      if (row) {
        setEvalInfo({
          dcResponse: row.get(DC_RESPONSE_COL),
          dcStat: row.get(DC_STAT_COL),
          llmStat: row.get(LLM_STAT_COL),
          question: row.get(DC_QUESTION_COL),
        });
      }
    });
  }, [doc, allCall, sessionQueryId, sessionCallId]);

  const checkAndSubmit = async (): Promise<boolean> => {
    if (status === FormStatus.InProgress) {
      alert("Please fill in all fields");
      return false;
    }
    if (status === FormStatus.Completed) {
      loadSpinner(LOADING_CONTAINER_ID);
      return Promise.all([
        saveToStore(
          userEmail,
          sheetId,
          sessionQueryId,
          sessionCallId,
          response
        ),
        saveToSheet(userEmail, doc, sessionQueryId, sessionCallId, response),
      ])
        .then(() => {
          return true;
        })
        .catch((error) => {
          alert("Error submitting response: " + error);
          return false;
        })
        .finally(() => {
          removeSpinner(LOADING_CONTAINER_ID);
        });
    }
    // Otherwise form status is Submitted or NotStarted. Just proceed with
    // any action.
    return true;
  };

  const handleApplyToNextChange = () => {
    setApplyToNext(!applyToNext);
  };

  const handleChange = (event) => {
    const { name, value } = event.target;
    setResponse((prevState) => {
      const newState = {
        ...prevState,
        [name]: value,
      };
      let tmpStatus = FormStatus.Completed;
      for (const value of Object.values(newState)) {
        if (value === "") {
          tmpStatus = FormStatus.InProgress;
          break;
        }
      }
      setStatus(tmpStatus);
      return newState;
    });
  };

  const enableReeval = () => {
    setResponse(EMPTY_RESPONSE);
    setStatus(FormStatus.NotStarted);
  };

  let dcResponseOptions;
  let dcResponseQuestion;
  if (evalInfo) {
    if (evalInfo.dcStat) {
      dcResponseQuestion = "Response from Data Commons";
      dcResponseOptions = {
        DC_ANSWER_IRRELEVANT: "Doesn't match the question",
        DC_ANSWER_RELEVANT_INACCURATE: "Relevant, but inaccurate",
        DC_ANSWER_RELEVANT_UNSURE: "Relevant, but unsure if it is accurate",
        DC_ANSWER_RELEVANT_ACCURATE: "Relevant and accurate",
      };
    } else {
      dcResponseQuestion = "Reason for empty Data Commons response";
      dcResponseOptions = {
        DC_ANSWER_EMPTY_BADNL: "Data exists, but NL fails to respond",
        DC_ANSWER_EMPTY_NODATA: "Query asks for data that doesn't exist in DC",
        DC_ANSWER_EMPTY_OUTOFSCOPE:
          "Query asks for data that is out-of-scope for DC",
      };
    }
  }

  return (
    <>
      <div className="button-section">
        <Button className="reeval-button" onClick={enableReeval}>
          <div>
            <span className="material-icons-outlined">redo</span>
            Re-Eval
          </div>
        </Button>
      </div>
      <div id={LOADING_CONTAINER_ID}>
        <div>
          <label id="apply-to-next">
            <input
              type="checkbox"
              checked={applyToNext}
              onChange={handleApplyToNextChange}
              disabled={status === FormStatus.Submitted}
            />
            Apply the response to the next question
          </label>
        </div>
        {evalInfo && (
          <form>
            <fieldset>
              <div className="question-section">
                <div className="title">GEMMA MODEL QUESTION EVALUATION</div>
                <div className="subtitle">
                  <span>{evalInfo.question}</span>
                </div>
                <OneQuestion
                  question="Question from the model"
                  name="question"
                  options={{
                    DC_QUESTION_IRRELEVANT:
                      "Irrelevant, vague, requires editing",
                    DC_QUESTION_RELEVANT: "Well formulated & relevant",
                  }}
                  handleChange={handleChange}
                  responseField={response.question}
                  disabled={status === FormStatus.Submitted}
                />
              </div>
              <div className="question-section">
                <div className="title">GEMMA MODEL STAT EVALUATION</div>
                <div className="subtitle">
                  <span className="llm-stat">{evalInfo.llmStat}</span>
                </div>
                <OneQuestion
                  question="Model response quality"
                  name="llmStat"
                  options={{
                    LLM_STAT_ACCURATE: "Stats seem accurate",
                    LLM_STAT_INACCURATE: "Stats seem inaccurate",
                    LLM_STAT_NOTSURE: "Unsure about accuracy",
                  }}
                  handleChange={handleChange}
                  responseField={response.llmStat}
                  disabled={status === FormStatus.Submitted}
                />
              </div>

              <div className="question-section">
                <div className="title">DATA COMMONS EVALUATION</div>
                <div className="subtitle">
                  <span>{evalInfo.dcResponse}</span>
                  <span className="dc-stat">{evalInfo.dcStat}</span>
                </div>
                <OneQuestion
                  question={dcResponseQuestion}
                  name="dcResponse"
                  options={dcResponseOptions}
                  handleChange={handleChange}
                  responseField={response.dcResponse}
                  disabled={status === FormStatus.Submitted}
                />
              </div>
            </fieldset>
          </form>
        )}
      </div>
      <FeedbackNavigation checkAndSubmit={checkAndSubmit} />
      <div id="page-screen" className="screen">
        <div id="spinner"></div>
      </div>
    </>
  );
}
