// description: 日本で人口密度が最も高い都道府県を探す。
// file_path: src/lib/skills/admins/Japan/findMostDenselyPopulatedPref.ts

import * as turf from "@turf/turf";
import osmtogeojson from "osmtogeojson";
import {
  Feature,
  FeatureCollection,
  MultiPolygon,
  Polygon,
  Position,
  GeoJsonProperties,
} from "geojson";
import fs from "fs";
import { Md5 } from "ts-md5";

/**
 * Fetches data from the Overpass API.
 * @param query - The Overpass QL query string.
 * @returns Promise resolving to JSON data from the Overpass API.
 */
const fetchOverpassData = async (query: string): Promise<any> => {
  const md5 = new Md5();
  md5.appendStr(query);
  const hash = md5.end();
  const cachePath = `./tmp/cache/overpass/query_${hash}.json`;
  try {
    const cache = await fs.readFileSync(cachePath, "utf-8");
    return JSON.parse(cache);
  } catch (e) {
    console.debug("Cache not found. Call Overpass API...");
  }
  const endpoint = "https://overpass-api.de/api/interpreter";
  const res = await fetch(endpoint, {
    method: "POST",
    headers: {
      "Content-Type": "application/x-www-form-urlencoded",
    },
    body: `data=${encodeURIComponent(query)}`,
  });
  if (!res.ok) {
    throw new Error(`HTTP error! status: ${res.status}`);
  }
  const data = await res.json();
  // cache the data
  await fs.mkdirSync("./tmp/cache/overpass", { recursive: true });
  await fs.writeFileSync(cachePath, JSON.stringify(data, null, 2), "utf-8");
  if (!data.elements || data.elements.length === 0) {
    throw new Error(
      `Overpass API returned no data without errors. Try to fix this query:\n${query}`
    );
  }
  return data;
};

/**
 * Fetches the land mask data of a specified admin area and region.
 * @param prefName - The name of the admin area to query.
 * @param regionName - The name of the region to query.
 * @returns The land mask GeoJSON data of the specified admin area and region.
 */
const fetchLandMaskGeoJson = async (
  prefName: string,
  regionName: string
): Promise<FeatureCollection<Polygon | MultiPolygon, GeoJsonProperties>> => {
  // 全世界の道州・都道府県レベルのGeoJSONデータを取得
  const geoJsonUrl =
    "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_10m_admin_1_states_provinces.geojson";
  const cachePath = `./tmp/cache/ne_10m_admin_1_states_provinces.geojson`;
  let data;
  try {
    const cache = await fs.readFileSync(cachePath, "utf-8");
    data = JSON.parse(cache);
  } catch (e) {
    console.debug("Cache not found. Fetching data from GitHub...");
    const res = await fetch(geoJsonUrl);
    if (!res.ok) {
      throw new Error(`HTTP error! status: ${res.status}`);
    }
    data = await res.json();
    // cache the data
    await fs.mkdirSync("./tmp/cache", { recursive: true });
    await fs.writeFileSync(cachePath, JSON.stringify(data, null, 2), "utf-8");
  }

  // 日本の都道府県かつregionに部分一致するfeatureだけを抽出
  const landMask = {
    type: "FeatureCollection",
    features: data.features
      .filter(
        (feature: Feature) =>
          feature.properties?.admin === prefName &&
          (regionName.includes(feature.properties["name"]) ||
            regionName.includes(feature.properties["name_en"]) ||
            regionName.includes(feature.properties["name_ja"]))
      )
      .filter(
        (feature: Feature) =>
          feature.geometry.type === "Polygon" ||
          feature.geometry.type === "MultiPolygon"
      ),
  } as FeatureCollection<Polygon | MultiPolygon, GeoJsonProperties>;
  return landMask;
};

/**
 * Fetches the number of population density in a specified pref area using Overpass API.
 * @param prefName - The name of the pref area to query.
 * @param population - The population of the pref area.
 * @returns The population density of the pref area.
 */
const getPopulationDensityOfPref = async (
  prefName: string,
  population: number
): Promise<number> => {
  const landMaskGeoJson = await fetchLandMaskGeoJson("Japan", prefName);
  const overpassQuery = `
[out:json];
area["name"="日本"]->.tokyo;
(
  relation["name"="${prefName}"]["admin_level"="4"](area.tokyo);
);
out geom;
`;
  const response = await fetchOverpassData(overpassQuery);
  const geojson = osmtogeojson(response);
  const newGeoJson = {
    type: "FeatureCollection",
    features: geojson.features.filter(
      (feature: Feature) =>
        feature.geometry.type === "Polygon" ||
        feature.geometry.type === "MultiPolygon"
    ),
  } as FeatureCollection<Polygon | MultiPolygon, GeoJsonProperties>;
  // newGeoJson.features[0] を turf で扱える形に変換
  const poly1 =
    newGeoJson.features[0].geometry.type === "Polygon"
      ? turf.polygon(
          newGeoJson.features[0].geometry.coordinates as number[][][]
        )
      : turf.multiPolygon(
          newGeoJson.features[0].geometry.coordinates as Position[][][]
        );
  // landMask.features[0] を turf で扱える形に変換
  const poly2 =
    landMaskGeoJson.features[0].geometry.type === "Polygon"
      ? turf.polygon(
          landMaskGeoJson.features[0].geometry.coordinates as number[][][]
        )
      : turf.multiPolygon(
          landMaskGeoJson.features[0].geometry.coordinates as Position[][][]
        );
  const clipped = turf.intersect(
    // @ts-expect-error poly1とpoly2はPolygon | MultiPolygonである
    turf.featureCollection([poly1, poly2])
  );
  if (!clipped) {
    throw new Error("Failed to clip the land mask.");
  }
  // area in square meters
  const area = turf.area(clipped);
  // area in square kilometers
  const areaInKm2 = area / 1000000;
  if (isNaN(population)) {
    population = 0;
  }
  return population / areaInKm2;
};

type AreaPopulation = {
  [prefName: string]: number;
};

/**
 * Fetches the population of each pref in Japan using e-Stat API.
 * @returns The population of each pref in Japan.
 */
async function getLatestPopulationOfPrefs(): Promise<AreaPopulation> {
  if (!process.env.E_STAT_APP_ID) {
    throw new Error("process.env.E_STAT_APP_ID is not set!");
  }
  // read cache file if exists
  const cachePath = "./tmp/cache/latestPopulationOfPrefsInJapan.json";
  try {
    const cache = await fs.readFileSync(cachePath, "utf-8");
    return JSON.parse(cache);
  } catch (e) {
    console.debug("Cache not found. Call e-Stat API...");
  }
  const endpoint = "https://api.e-stat.go.jp/rest/3.0/app/json/getStatsData";
  const searchParams = new URLSearchParams();
  searchParams.append("appId", process.env.E_STAT_APP_ID);
  searchParams.append("lang", "J");
  searchParams.append("statsDataId", "0000010101");
  searchParams.append("metaGetFlg", "Y");
  searchParams.append("cntGetFlg", "N");
  searchParams.append("explanationGetFlg", "Y");
  searchParams.append("annotationGetFlg", "Y");
  searchParams.append("sectionHeaderFlg", "1");
  searchParams.append("replaceSpChars", "0");

  // fetch data from e-Stat API
  const res = await fetch(`${endpoint}?${searchParams.toString()}`);
  const json = await res.json();
  const keys: {
    "@code": string; // 00000
    "@name": string; // 全国
    "@level": string; // 1
  }[] = json.GET_STATS_DATA.STATISTICAL_DATA.CLASS_INF.CLASS_OBJ[2].CLASS;
  const values: {
    "@tab": string; // 00001
    "@cat01": string; // A1101
    "@area": string; // 00000
    "@time": string; // 1975100000
    "@unit": string; // 人
    $: string; // 111939643
  }[] = json.GET_STATS_DATA.STATISTICAL_DATA.DATA_INF.VALUE;
  // aggregate latest population value by pref name
  const data: AreaPopulation = {};
  for (const pref of keys) {
    const prefName = pref["@name"];
    if (prefName === "全国") {
      continue;
    }
    const prefCode = pref["@code"];
    // filter by pref code
    const populationValues = values.filter(
      (value) => value["@area"] === prefCode
    );
    const populationValuesParsed = populationValues.map((value) => ({
      population: parseInt(value["$"]),
      time: parseInt(value["@time"]),
    }));
    // get the latest population value
    const latestPopulation = populationValuesParsed.sort(
      (a, b) => b.time - a.time
    )[0].population;
    data[prefName] = latestPopulation;
  }
  // cache the data
  await fs.mkdirSync("./tmp/cache", { recursive: true });
  await fs.writeFileSync(cachePath, JSON.stringify(data, null, 2), "utf-8");
  return data;
}

const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

/**
 * Get the name of the most densely populated pref in Japan.
 * @returns The name of the most densely populated pref in Japan.
 */
const findMostDenselyPopulatedPref = async (): Promise<string> => {
  const prefs = await getLatestPopulationOfPrefs();
  let maxPopulationDensity = 0;
  let prefWithMaxPopulationDensity = "";
  for (const prefName of Object.keys(prefs)) {
    await sleep(5000);
    const latestPopulation = prefs[prefName];
    const populationDensity = await getPopulationDensityOfPref(
      prefName,
      latestPopulation
    );
    console.info(
      `${prefName}: ${latestPopulation} people, ${populationDensity} people/km²`
    );
    if (populationDensity > maxPopulationDensity) {
      maxPopulationDensity = populationDensity;
      prefWithMaxPopulationDensity = prefName;
    }
  }
  return prefWithMaxPopulationDensity;
};

export default findMostDenselyPopulatedPref;
