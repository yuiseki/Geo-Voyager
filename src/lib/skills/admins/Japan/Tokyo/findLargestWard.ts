// description: 東京都において、面積が最も広い行政区を探す。
// file_path: src/lib/skills/admins/Japan/Tokyo/findLargestWard.ts

import * as turf from "@turf/turf";
import fs from "fs";
import osmtogeojson from "osmtogeojson";
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
    const cache = await fs.promises.readFile(cachePath, "utf-8");
    return JSON.parse(cache);
  } catch (e) {
    console.debug("Cache not found. Calling Overpass API...");
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
  await fs.promises.mkdir("./tmp/cache/overpass", { recursive: true });
  await fs.promises.writeFile(
    cachePath,
    JSON.stringify(data, null, 2),
    "utf-8"
  );
  return data;
};

/**
 * @returns A list of name of all wards in Tokyo.
 */
const getAllWardsInTokyo = async (): Promise<string[]> => {
  const overpassQuery = `
[out:json];
area["name"="東京都"]->.tokyo;
(
  relation["admin_level"="7"](area.tokyo);
);
out tags;
`;
  const response = await fetchOverpassData(overpassQuery);
  const wards = response.elements.map((element: any) => element.tags.name);
  return wards;
};

/**
 * Fetches the area of a specified ward using Overpass API.
 * @param wardName - The name of the ward to query.
 * @returns The area of the ward in square kilometers.
 */
const getAreaOfWard = async (wardName: string): Promise<number> => {
  const overpassQuery = `
[out:json];
area["name"="東京都"]->.tokyo;
(
  relation["admin_level"="7"]["name"="${wardName}"](area.tokyo);
);
out geom;
`;
  const response = await fetchOverpassData(overpassQuery);
  const geoJson = osmtogeojson(response);
  const area = turf.area(geoJson);
  const areaInKm2 = area / 1000000;
  return areaInKm2;
};

const findLargestWard = async (): Promise<string> => {
  const wards = await getAllWardsInTokyo();
  let maxArea = 0;
  let wardWithLargestArea = "";
  for (const ward of wards) {
    const area = await getAreaOfWard(ward);
    console.log(`findLargestWard: ${ward} has an area of ${area} km²`);
    if (area > maxArea) {
      maxArea = area;
      wardWithLargestArea = ward;
    }
  }
  return wardWithLargestArea;
};

export default findLargestWard;
