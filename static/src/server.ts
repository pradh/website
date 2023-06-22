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

import axios from "axios";
// This import is unused in this file, but needed for draw functions for map and
// scatter.
import * as Canvas from "canvas";
import express, { Request, Response } from "express";
import { JSDOM } from "jsdom";
import _ from "lodash";
import React from "react";
import ReactDOMServer from "react-dom/server";
import * as xmlserializer from "xmlserializer";

import {
  draw as drawBar,
  fetchData as fetchBarData,
  getReplacementStrings as getBarRS,
} from "../../static/js/components/tiles/bar_tile";
import {
  draw as drawDisasterMap,
  fetchChartData as fetchDisasterMapData,
  getReplacementStrings as getDisasterMapRS,
} from "../../static/js/components/tiles/disaster_event_map_tile";
import {
  draw as drawLine,
  fetchData as fetchLineData,
  getReplacementStrings as getLineRS,
} from "../../static/js/components/tiles/line_tile";
import {
  draw as drawMap,
  fetchData as fetchMapData,
  getReplacementStrings as getMapRS,
} from "../../static/js/components/tiles/map_tile";
import { fetchData as fetchRankingData } from "../../static/js/components/tiles/ranking_tile";
import {
  draw as drawScatter,
  fetchData as fetchScatterData,
  getReplacementStrings as getScatterRS,
} from "../../static/js/components/tiles/scatter_tile";
import {
  LEGEND_IMG_WIDTH,
  LEGEND_MARGIN_RIGHT,
  LEGEND_MARGIN_VERTICAL,
  LEGEND_TICK_LABEL_MARGIN,
} from "../js/chart/draw_map_utils";
import { fetchDisasterEventData } from "../js/components/subject_page/disaster_event_block";
import {
  getRankingUnit,
  getRankingUnitTitle,
} from "../js/components/tiles/sv_ranking_units";
import { SELF_PLACE_DCID_PLACEHOLDER } from "../js/constants/subject_page_constants";
import { NamedTypedPlace, StatVarSpec } from "../js/shared/types";
import { urlToDomain } from "../js/shared/util";
import { DisasterEventPointData } from "../js/types/disaster_event_map_types";
import { RankingGroup } from "../js/types/ranking_unit_types";
import {
  BlockConfig,
  EventTypeSpec,
  TileConfig,
} from "../js/types/subject_page_proto_types";
import {
  dataGroupsToCsv,
  mapDataToCsv,
  rankingPointsToCsv,
  scatterDataToCsv,
} from "../js/utils/chart_csv_utils";
import { htmlToSvg } from "../js/utils/svg_utils";
import { getChartTitle, getTileEventTypeSpecs } from "../js/utils/tile_utils";

// TODO (chejennifer): Split up functions into smaller files

const app = express();
const APP_CONFIGS = {
  local: {
    port: 3030,
    apiRoot: "http://127.0.0.1:8080",
  },
  gke: {
    port: 8080,
    apiRoot: process.env.API_ROOT,
  },
};
const NODE_ENV = process.env.NODE_ENV || "local";
const CONFIG = APP_CONFIGS[NODE_ENV];
const HOST = "0.0.0.0";
// Each value in the array is the width of the character with ascii code of
// array index + 32 for 10px Roboto font.
// This was generated by rendering the array of characters in the correct font
// and size on the website and reading the bounding box width of each of those
// characters.
// To generate the list of characters:
// Array.from(Array(96).keys()).map((idx) => String.fromCharCode(idx + 32))
const CHAR_WIDTHS = [
  0, 2.578125, 3.203125, 6.1640625, 5.6171875, 7.328125, 6.21875, 1.75,
  3.421875, 3.4765625, 4.3125, 5.671875, 1.96875, 2.765625, 2.6328125, 4.125,
  5.6171875, 5.6171875, 5.6171875, 5.6171875, 5.6171875, 5.6171875, 5.6171875,
  5.6171875, 5.6171875, 5.6171875, 2.421875, 2.1171875, 5.0859375, 5.4921875,
  5.2265625, 4.7265625, 8.984375, 6.5234375, 6.2265625, 6.515625, 6.5625,
  5.6875, 5.53125, 6.8125, 7.1328125, 2.7265625, 5.5234375, 6.2734375,
  5.3828125, 8.734375, 7.1328125, 6.875, 6.3125, 6.875, 6.1640625, 5.9375,
  5.96875, 6.484375, 6.3671875, 8.875, 6.2734375, 6.0078125, 5.9921875, 2.65625,
  4.1015625, 2.65625, 4.1796875, 4.515625, 3.09375, 5.4453125, 5.6171875,
  5.234375, 5.640625, 5.3046875, 3.359375, 5.6171875, 5.5078125, 2.4296875,
  2.390625, 5.0703125, 2.4296875, 8.765625, 5.5234375, 5.703125, 5.6171875,
  5.6875, 3.390625, 5.15625, 3.2734375, 5.515625, 4.84375, 7.515625, 4.9609375,
  4.734375, 4.9609375, 3.390625, 2.4375, 3.390625, 6.8046875, 0,
];
// Average width of a 10px Roboto character.
// This was generated by calculating the average from CHAR_WIDTHS.
const CHAR_AVG_WIDTH = 5.0341796875;
// Height of a 10px Roboto character.
const CHAR_HEIGHT = 13;
// Height of the svg to render.
const SVG_HEIGHT = 300;
// Width of the svg to render.
const SVG_WIDTH = 500;
// Font family to use for all the text on the charts. If this is updated, need
// to also update CHAR_WIDTHS and CHAR_AVG_WIDTHS.
const FONT_FAMILY = "Roboto";
// Font size to use for all the text on the charts. If this is updated, need to
// also update CHAR_WIDTHS, CHAR_AVG_WIDTHS, and CHAR_HEIGHT.
const FONT_SIZE = "10px";
// Width of the constant sized part of the map legend
const MAP_LEGEND_CONSTANT_WIDTH =
  LEGEND_IMG_WIDTH + LEGEND_MARGIN_RIGHT + LEGEND_TICK_LABEL_MARGIN;
const DOM_ID = "dom-id";

const dom = new JSDOM(
  `<html><body><div id="dom-id" style="width:500px"></div></body></html>`,
  {
    pretendToBeVisual: true,
  }
);

globalThis.datacommons = {
  root: "",
};

const window = dom.window;
global.document = dom.window.document;

// The result for a single tile
interface TileResult {
  // The svg for the chart in the tile as an xml string
  svg: string;
  // List of sources of the data in the chart
  srcs: { name: string; url: string }[];
  // The title of the tile
  title: string;
  // The type of the tile
  type: string;
  // List of legend labels
  legend?: string[];
  // The data for the chart in the tile as a csv string
  data_csv?: string;
}

// Gets the length in pixels of a string
function getTextLength(text: string): number {
  if (!text) {
    return 0;
  }
  let length = 0;
  Array.from(text).forEach((c) => {
    const charCode = c.codePointAt(0);
    const arrIdx = charCode - 32;
    if (arrIdx > 0 && arrIdx < CHAR_WIDTHS.length) {
      length += CHAR_WIDTHS[arrIdx];
    } else {
      length += CHAR_AVG_WIDTH;
    }
  });
  return length;
}

(window.Text as any).prototype.getComputedTextLength = function (): number {
  return getTextLength(this.textContent);
};

(window.SVGElement as any).prototype.getComputedTextLength =
  function (): number {
    return getTextLength(this.textContent);
  };

// JSDom does not define SVGTSpanElements, and use SVGElement instead. Defines
// a shim for getBBox which returns width and height of the element.
// This assumes each child text node is a separate line of text rendered
// vertically one after another.
(window.Element as any).prototype.getBBox = function (): DOMRect {
  let width = 0;
  let height = 0;
  const children = this.childNodes;
  for (const child of children) {
    // Width is the max width of all the child nodes.
    width = Math.max(child.getComputedTextLength(), width);
    // Height is the total combined height of all the child nodes.
    height += CHAR_HEIGHT;
  }
  return {
    width,
    height,
    x: 0,
    y: 0,
    bottom: 0,
    left: 0,
    right: 0,
    top: 0,
    toJSON: { ...this },
  };
};

// Gets a list of source objects with name and url from a set of source urls.
function getSources(sources: Set<string>): { name: string; url: string }[] {
  return Array.from(sources).map((src) => {
    return {
      name: urlToDomain(src),
      url: src,
    };
  });
}

// Processes and serializes a svg for a chart.
function getProcessedSvg(chartSvg: SVGSVGElement): string {
  if (!chartSvg) {
    return "";
  }
  // Set the font for all the text in the svg to match the font family and size
  // used for getBBox calculations.
  chartSvg.querySelectorAll("text").forEach((node) => {
    node.setAttribute("font-family", FONT_FAMILY);
    node.setAttribute("font-size", FONT_SIZE);
  });
  // Get and return the svg as an xml string
  const svgXml = xmlserializer.serializeToString(chartSvg);
  return "data:image/svg+xml," + encodeURIComponent(svgXml);
}

// Gets the TileResult for a scatter tile.
async function getScatterTileResult(
  id: string,
  tileConfig: TileConfig,
  place: NamedTypedPlace,
  enclosedPlaceType: string,
  statVarSpec: StatVarSpec[]
): Promise<TileResult[]> {
  const tileProp = {
    id,
    title: tileConfig.title,
    place,
    enclosedPlaceType,
    statVarSpec,
    svgChartHeight: SVG_HEIGHT,
    scatterTileSpec: tileConfig.scatterTileSpec,
    apiRoot: CONFIG.apiRoot,
  };

  try {
    const chartData = await fetchScatterData(tileProp);
    const svgContainer = document.createElement("div");
    drawScatter(
      chartData,
      svgContainer,
      SVG_HEIGHT,
      null /* tooltipHtml */,
      tileConfig.scatterTileSpec,
      SVG_WIDTH
    );
    return [
      {
        svg: getProcessedSvg(svgContainer.querySelector("svg")),
        data_csv: scatterDataToCsv(
          chartData.xStatVar.statVar,
          chartData.xStatVar.denom,
          chartData.yStatVar.statVar,
          chartData.yStatVar.denom,
          chartData.points
        ),
        srcs: getSources(chartData.sources),
        title: getChartTitle(
          tileConfig.title,
          getScatterRS(tileProp, chartData)
        ),
        type: "SCATTER",
      },
    ];
  } catch (e) {
    console.log("Failed to get scatter tile result for: " + id);
    return null;
  }
}

// Gets the TileResult for a line tile
async function getLineTileResult(
  id: string,
  tileConfig: TileConfig,
  place: NamedTypedPlace,
  statVarSpec: StatVarSpec[]
): Promise<TileResult[]> {
  const tileProp = {
    apiRoot: CONFIG.apiRoot,
    id,
    place,
    statVarSpec,
    svgChartHeight: SVG_HEIGHT,
    svgChartWidth: SVG_WIDTH,
    title: tileConfig.title,
  };
  try {
    const chartData = await fetchLineData(tileProp);
    const tileContainer = document.createElement("div");
    tileContainer.setAttribute("id", id);
    document.getElementById(DOM_ID).appendChild(tileContainer);
    drawLine(tileProp, chartData, null);
    const svg = getProcessedSvg(tileContainer.querySelector("svg"));
    tileContainer.remove();
    return [
      {
        svg: getProcessedSvg(tileContainer.querySelector("svg")),
        data_csv: dataGroupsToCsv(chartData.dataGroup),
        srcs: getSources(chartData.sources),
        legend: chartData.dataGroup.map((dg) => dg.label || "A"),
        title: getChartTitle(tileConfig.title, getLineRS(tileProp)),
        type: "LINE",
      },
    ];
  } catch (e) {
    console.log("Failed to get line tile result for: " + id);
    return null;
  }
}

// Gets the TileResult for a bar tile
async function getBarTileResult(
  id: string,
  tileConfig: TileConfig,
  place: NamedTypedPlace,
  enclosedPlaceType: string,
  statVarSpec: StatVarSpec[]
): Promise<TileResult[]> {
  const comparisonPlaces = tileConfig.comparisonPlaces
    ? tileConfig.comparisonPlaces.map((p) =>
        p == SELF_PLACE_DCID_PLACEHOLDER ? place.dcid : p
      )
    : undefined;
  const tileProp = {
    id,
    title: tileConfig.title,
    place,
    enclosedPlaceType,
    statVarSpec,
    apiRoot: CONFIG.apiRoot,
    svgChartHeight: SVG_HEIGHT,
    comparisonPlaces,
  };
  try {
    const chartData = await fetchBarData(tileProp);
    const tileContainer = document.createElement("div");
    tileContainer.setAttribute("id", id);
    document.getElementById(DOM_ID).appendChild(tileContainer);
    drawBar(tileProp, chartData, SVG_WIDTH);
    let legend = [];
    if (
      !_.isEmpty(chartData.dataGroup) &&
      !_.isEmpty(chartData.dataGroup[0].value)
    ) {
      legend = chartData.dataGroup[0].value.map((dp) => dp.label);
    }
    const svg = getProcessedSvg(tileContainer.querySelector("svg"));
    tileContainer.remove();
    return [
      {
        svg: getProcessedSvg(tileContainer.querySelector("svg")),
        data_csv: dataGroupsToCsv(chartData.dataGroup),
        srcs: getSources(chartData.sources),
        legend,
        title: getChartTitle(tileConfig.title, getBarRS(tileProp, chartData)),
        type: "BAR",
      },
    ];
  } catch (e) {
    console.log("Failed to get bar tile result for: " + id);
    return null;
  }
}

// Gets the TileResult for a map tile
async function getMapTileResult(
  id: string,
  tileConfig: TileConfig,
  place: NamedTypedPlace,
  enclosedPlaceType: string,
  statVarSpec: StatVarSpec
): Promise<TileResult[]> {
  const tileProp = {
    id,
    title: tileConfig.title,
    place,
    enclosedPlaceType,
    statVarSpec,
    svgChartHeight: SVG_HEIGHT - LEGEND_MARGIN_VERTICAL * 2,
    apiRoot: CONFIG.apiRoot,
  };
  try {
    const chartData = await fetchMapData(tileProp);
    const legendContainer = document.createElement("div");
    const mapContainer = document.createElement("div");
    drawMap(
      chartData,
      tileProp,
      null,
      legendContainer,
      mapContainer,
      SVG_WIDTH
    );
    // Get the width of the text in the legend
    let legendTextWidth = 0;
    Array.from(legendContainer.querySelectorAll("text")).forEach((node) => {
      legendTextWidth = Math.max(node.getBBox().width, legendTextWidth);
    });
    const legendWidth = legendTextWidth + MAP_LEGEND_CONSTANT_WIDTH;
    // Create a single merged svg to hold both the map and the legend svgs
    const mergedSvg = document.createElementNS(
      "http://www.w3.org/2000/svg",
      "svg"
    );
    mergedSvg.setAttribute("height", String(SVG_HEIGHT));
    mergedSvg.setAttribute("width", String(SVG_WIDTH));
    // Get the map svg and add it to the merged svg
    const mapSvg = mapContainer.querySelector("svg");
    const mapWidth = SVG_WIDTH - legendWidth;
    mapSvg.setAttribute("width", String(mapWidth));
    const mapG = document.createElementNS("http://www.w3.org/2000/svg", "g");
    mapG.appendChild(mapSvg);
    mergedSvg.appendChild(mapG);
    // Get the legend svg and add it to the merged svg
    const legendSvg = legendContainer.querySelector("svg");
    legendSvg.setAttribute("width", String(legendWidth));
    const legendG = document.createElementNS("http://www.w3.org/2000/svg", "g");
    legendG.setAttribute("transform", `translate(${mapWidth})`);
    legendG.appendChild(legendSvg);
    mergedSvg.appendChild(legendG);

    return [
      {
        svg: getProcessedSvg(mergedSvg),
        data_csv: mapDataToCsv(chartData.geoJson, chartData.dataValues),
        srcs: getSources(chartData.sources),
        title: getChartTitle(tileConfig.title, getMapRS(tileProp, chartData)),
        type: "MAP",
      },
    ];
  } catch (e) {
    console.log("Failed to get map tile result for: " + id);
    return null;
  }
}

// Get the result for a single ranking unit
function getRankingUnitResult(
  tileConfig: TileConfig,
  rankingGroup: RankingGroup,
  sv: string,
  isHighest: boolean
): TileResult {
  const rankingHtml = ReactDOMServer.renderToString(
    getRankingUnit(
      tileConfig.title,
      sv,
      rankingGroup,
      tileConfig.rankingTileSpec,
      isHighest
    )
  );
  const style = {
    "font-family": FONT_FAMILY,
    "font-size": FONT_SIZE,
  };
  const svg = htmlToSvg(rankingHtml, SVG_WIDTH, SVG_HEIGHT, "", style);
  const processedSvg = getProcessedSvg(svg);
  return {
    svg: processedSvg,
    data_csv: rankingPointsToCsv(rankingGroup.points, rankingGroup.svName),
    srcs: getSources(rankingGroup.sources),
    title: getRankingUnitTitle(
      tileConfig.title,
      tileConfig.rankingTileSpec,
      rankingGroup,
      false,
      sv
    ),
    type: "TABLE",
  };
}

// Get the tile results for a ranking tile.
async function getRankingTileResult(
  id: string,
  tileConfig: TileConfig,
  place: NamedTypedPlace,
  enclosedPlaceType: string,
  statVarSpec: StatVarSpec[]
): Promise<TileResult[]> {
  const tileProp = {
    id,
    title: tileConfig.title,
    place,
    enclosedPlaceType,
    statVarSpec,
    rankingMetadata: tileConfig.rankingTileSpec,
    apiRoot: CONFIG.apiRoot,
  };
  try {
    const rankingData = await fetchRankingData(tileProp);
    const tileResults: TileResult[] = [];
    for (const sv of Object.keys(rankingData)) {
      const rankingGroup = rankingData[sv];
      if (tileConfig.rankingTileSpec.showHighest) {
        tileResults.push(
          getRankingUnitResult(tileConfig, rankingGroup, sv, true)
        );
      }
      if (tileConfig.rankingTileSpec.showLowest) {
        tileResults.push(
          getRankingUnitResult(tileConfig, rankingGroup, sv, false)
        );
      }
    }
    return tileResults;
  } catch (e) {
    console.log("Failed to get ranking tile result for: " + id);
    return null;
  }
}

async function getDisasterMapTileResult(
  id: string,
  tileConfig: TileConfig,
  place: NamedTypedPlace,
  enclosedPlaceType: string,
  eventTypeSpec: Record<string, EventTypeSpec>,
  disasterEventDataPromise: Promise<Record<string, DisasterEventPointData>>
): Promise<TileResult[]> {
  let tileEventData = null;
  try {
    const disasterEventData = await disasterEventDataPromise;
    tileEventData = {};
    Object.keys(eventTypeSpec).forEach((specId) => {
      tileEventData[specId] = disasterEventData[specId];
    });
    const tileProp = {
      id: "test",
      title: tileConfig.title,
      place,
      enclosedPlaceType,
      eventTypeSpec,
      disasterEventData: tileEventData,
      tileSpec: tileConfig.disasterEventMapTileSpec,
      apiRoot: CONFIG.apiRoot,
    };
    const chartData = await fetchDisasterMapData(tileProp);
    const mapContainer = document.createElement("div");
    drawDisasterMap(
      tileProp,
      chartData,
      mapContainer,
      new Set(Object.keys(eventTypeSpec)),
      SVG_HEIGHT,
      SVG_WIDTH
    );
    const svg = mapContainer.querySelector("svg");
    svg.style.background = "#eee";
    return [
      {
        svg: getProcessedSvg(svg),
        legend: Object.values(eventTypeSpec).map((spec) => spec.name),
        srcs: getSources(chartData.sources),
        title: getChartTitle(tileConfig.title, getDisasterMapRS(tileProp)),
        type: "EVENT_MAP",
      },
    ];
  } catch (e) {
    console.log("Failed to get disaster event map tile result for: " + id);
    return null;
  }
}

// Get a list of tile result promises for all the tiles in the block
function getBlockTileResults(
  id: string,
  block: BlockConfig,
  place: NamedTypedPlace,
  enclosedPlaceType: string,
  svSpec: Record<string, StatVarSpec>
): Promise<TileResult[]>[] {
  const tilePromises = [];
  block.columns.forEach((column, colIdx) => {
    column.tiles.forEach((tile, tileIdx) => {
      const tileId = `${id}-col${colIdx}-tile${tileIdx}`;
      let tileSvSpec = null;
      switch (tile.type) {
        case "LINE":
          tileSvSpec = tile.statVarKey.map((s) => svSpec[s]);
          tilePromises.push(getLineTileResult(tileId, tile, place, tileSvSpec));
          break;
        case "SCATTER":
          tileSvSpec = tile.statVarKey.map((s) => svSpec[s]);
          tilePromises.push(
            getScatterTileResult(
              tileId,
              tile,
              place,
              enclosedPlaceType,
              tileSvSpec
            )
          );
          break;
        case "BAR":
          tileSvSpec = tile.statVarKey.map((s) => svSpec[s]);
          tilePromises.push(
            getBarTileResult(tileId, tile, place, enclosedPlaceType, tileSvSpec)
          );
          break;
        case "MAP":
          tileSvSpec = svSpec[tile.statVarKey[0]];
          tilePromises.push(
            getMapTileResult(tileId, tile, place, enclosedPlaceType, tileSvSpec)
          );
          break;
        case "RANKING":
          tileSvSpec = tile.statVarKey.map((s) => svSpec[s]);
          tilePromises.push(
            getRankingTileResult(
              tileId,
              tile,
              place,
              enclosedPlaceType,
              tileSvSpec
            )
          );
          break;
        default:
          break;
      }
    });
  });
  return tilePromises;
}

// Get a list of tile result promises for all the tiles in the disaster block
function getDisasterBlockTileResults(
  id: string,
  block: BlockConfig,
  place: NamedTypedPlace,
  enclosedPlaceType: string,
  eventTypeSpec: Record<string, EventTypeSpec>
): Promise<TileResult[]>[] {
  const blockProp = {
    id,
    place,
    enclosedPlaceType,
    title: block.title,
    description: block.description,
    footnote: block.footnote,
    columns: block.columns,
    eventTypeSpec,
    apiRoot: CONFIG.apiRoot,
  };
  const disasterEventDataPromise = fetchDisasterEventData(blockProp);
  const tilePromises = [];
  block.columns.forEach((column, colIdx) => {
    column.tiles.forEach((tile, tileIdx) => {
      const tileEventTypeSpec = getTileEventTypeSpecs(eventTypeSpec, tile);
      const tileId = `${id}-col${colIdx}-tile${tileIdx}`;
      switch (tile.type) {
        case "DISASTER_EVENT_MAP":
          tilePromises.push(
            getDisasterMapTileResult(
              tileId,
              tile,
              place,
              enclosedPlaceType,
              tileEventTypeSpec,
              disasterEventDataPromise
            )
          );
        default:
          return null;
      }
    });
  });
  return tilePromises;
}

// Prevents returning 304 status if same GET request gets hit multiple times.
// This is needed for health checks to pass which require a 200 status.
app.disable("etag");

app.get("/nodejs/query", (req: Request, res: Response) => {
  const query = req.query.q;
  res.setHeader("Content-Type", "application/json");
  axios
    .post(`${CONFIG.apiRoot}/api/nl/data?q=${query}`, {})
    .then((resp) => {
      const mainPlace = resp.data["place"] || {};
      const place = {
        dcid: mainPlace["dcid"],
        name: mainPlace["name"],
        types: [mainPlace["place_type"]],
      };
      const config = resp.data["config"] || {};
      let enclosedPlaceType = "";
      if (
        config["metadata"] &&
        config["metadata"]["containedPlaceTypes"] &&
        !_.isEmpty(place.types)
      ) {
        enclosedPlaceType =
          config["metadata"]["containedPlaceTypes"][place.types[0]] ||
          enclosedPlaceType;
      }

      // If no place, return here
      if (!place.dcid) {
        res.status(200).send({ charts: [] });
        return;
      }

      // Get a list of tile result promises
      const tilePromises: Array<Promise<TileResult[]>> = [];
      const categories = config["categories"] || [];
      categories.forEach((category, catIdx) => {
        const svSpec = {};
        for (const sv in category["statVarSpec"]) {
          svSpec[sv] = category["statVarSpec"][sv];
        }
        category.blocks.forEach((block, blkIdx) => {
          const blockId = `cat${catIdx}-blk${blkIdx}`;
          let blockTilePromises = [];
          switch (block.type) {
            case "DISASTER_EVENT":
              blockTilePromises = getDisasterBlockTileResults(
                blockId,
                block,
                place,
                enclosedPlaceType,
                config["metadata"]["eventTypeSpec"]
              );
              break;
            default:
              blockTilePromises = getBlockTileResults(
                blockId,
                block,
                place,
                enclosedPlaceType,
                svSpec
              );
          }
          tilePromises.push(...blockTilePromises);
        });
      });

      // If no tiles return here.
      if (tilePromises.length < 1) {
        res.status(200).send({ charts: [] });
        return;
      }

      Promise.all(tilePromises)
        .then((tileResults) => {
          const filteredResults = tileResults
            .flat(1)
            .filter((result) => result !== null);
          res.status(200).send(JSON.stringify({ charts: filteredResults }));
        })
        .catch(() => {
          res.status(500).send({ err: "Error fetching data." });
        });
    })
    .catch((error) => {
      console.error("Error making request:\n", error.message);
      res.status(500).send({ err: "Error fetching data." });
    });
});

app.get("/nodejs/healthz", (_, res: Response) => {
  res.status(200).send("Node Server Ready");
});

app.listen(Number(CONFIG.port), HOST, () => {
  console.log(`Server is listening on http://${HOST}:${CONFIG.port}`);
});
