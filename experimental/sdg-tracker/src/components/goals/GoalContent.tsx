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

import { Breadcrumb, Layout } from "antd";
import React, { useMemo } from "react";
import { Link } from "react-router-dom";
import styled from "styled-components";
import { useStoreState } from "../../state";
import { WEB_API_ENDPOINT } from "../../utils/constants";

const InnerContent = styled.div`
  margin: 0;
  padding: 24px;
  background: white;
  border-radius: 1rem;
`;

interface ChartConfig {
  title: string;
  type: "BAR"; // TODO: Add support for additional charts
  variables: string[];
}

const DataCommonsChart: React.FC<{
  config: ChartConfig;
}> = (props) => {
  const { config } = props;
  return (
    <div>
      {/**@ts-ignore */}
      <datacommons-bar
        apiRoot={WEB_API_ENDPOINT}
        childPlaceType="Country"
        sort="descending"
        maxPlaces={10}
        parentPlace="Earth"
        title={`${config.title} (DESCENDING)`}
        variables={config.variables.join(" ")}
        yAxisMargin={150}
      />
    </div>
  );
};

const GoalContent: React.FC<{
  selectedVariableGroupDcid?: string;
}> = (props) => {
  const { selectedVariableGroupDcid } = props;
  const variableGroupsByDcid = useStoreState((s) => s.variableGroups.byDcid);
  const selectedVariableGroup = useStoreState((s) =>
    selectedVariableGroupDcid
      ? s.variableGroups.byDcid[selectedVariableGroupDcid]
      : null
  );
  const chartConfigs = useMemo(() => {
    if (!selectedVariableGroupDcid) {
      return;
    }
    const chartConfigsTraverse = (variableGroupDcid: string): ChartConfig[] => {
      const vg = variableGroupsByDcid[variableGroupDcid];
      const configs: ChartConfig[] = [];
      if (vg.childVariableDcids.length > 0) {
        configs.push({
          title: vg.name,
          type: "BAR",
          variables: vg.childVariableDcids,
        });
      }
      vg.childGroupDcids.forEach((vgDcid) => {
        configs.push(...chartConfigsTraverse(vgDcid));
      });
      return configs;
    };

    return chartConfigsTraverse(selectedVariableGroupDcid);
  }, [selectedVariableGroupDcid]);

  if (!selectedVariableGroup) {
    return (
      <Layout.Content>
        <InnerContent>
          <h2>SDG Goals</h2>
          <p>
            Data Commons has indexed more than 3,000 statistical variables that
            are indicators for SDG progress. Select a goal on the left to view
            the data holdings.
          </p>
        </InnerContent>
      </Layout.Content>
    );
  }
  return (
    <Layout style={{ padding: "0 24px 24px", overflow: "auto" }}>
      <Breadcrumb style={{ margin: "16px 0" }}>
        <Breadcrumb.Item>
          <Link to="/goals">Goals</Link>
        </Breadcrumb.Item>
      </Breadcrumb>
      <Layout.Content>
        <InnerContent>
          <h2>{selectedVariableGroup.name}</h2>
          {chartConfigs &&
            chartConfigs.map((config, i) => (
              <DataCommonsChart config={config} key={i} />
            ))}
        </InnerContent>
      </Layout.Content>
    </Layout>
  );
};

export default GoalContent;
