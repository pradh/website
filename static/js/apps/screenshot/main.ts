/**
 * Copyright 2023 Google LLC
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

import React from "react";
import ReactDOM from "react-dom";

import { App } from "./app";

window.onload = () => {
  const images1 = JSON.parse(
    document.getElementById("screenshot-data").dataset.images1
  );
  const images2 = JSON.parse(
    document.getElementById("screenshot-data").dataset.images2
  );

  const data = {};
  for (const name in images1) {
    if (name in images2) {
      data[name] = {
        blob1: images1[name],
        blob2: images2[name],
      };
    }
  }

  ReactDOM.render(
    React.createElement(App, { data }),
    document.getElementById("dc-screenshot")
  );
};
