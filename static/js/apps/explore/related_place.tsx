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

import _ from "lodash";
import React from "react";

import { NamedTypedNode } from "../../shared/types";
import { Item, ItemList } from "./item_list";

interface RelatedPlacePropsType {
  relatedPlaces: NamedTypedNode[];
  topic: NamedTypedNode;
  cmpPlace: string;
  dc: string;
  exploreMore: string;
  nlFulfillment: string;
  titleSuffix: string;
}

const buildPlaceList = (
  relatedPlaces: NamedTypedNode[],
  topic: NamedTypedNode,
  cmpPlace: string,
  dc: string,
  exploreMore: string,
  nlFulfillment: string
): Item[] => {
  if (_.isEmpty(relatedPlaces)) {
    return [];
  }
  const result: Item[] = [];
  for (const relatedPlace of relatedPlaces) {
    result.push({
      text: relatedPlace.name,
      url: `/explore/#t=${topic.dcid}&p=${relatedPlace.dcid}&pcmp=${cmpPlace}&dc=${dc}&em=${exploreMore}&nl=${nlFulfillment}`,
    });
  }
  return result;
};

export function RelatedPlace(props: RelatedPlacePropsType): JSX.Element {
  const placeList = buildPlaceList(
    props.relatedPlaces,
    props.topic,
    props.cmpPlace,
    props.dc,
    props.exploreMore,
    props.nlFulfillment
  );
  return (
    <div className="related-places">
      <div className="related-places-callout">
        <span>See </span>
        {props.topic.name && <span>{props.topic.name.toLowerCase()} of </span>}
        {props.titleSuffix}
      </div>
      <ItemList items={placeList}></ItemList>
    </div>
  );
}
