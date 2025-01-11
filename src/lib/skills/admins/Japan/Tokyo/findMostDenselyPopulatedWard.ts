// description: 東京都において、人口密度が最も高い行政区を探す。
// file_path: src/lib/skills/admins/Japan/Tokyo/findMostDenselyPopulatedWard.ts

import * as turf from "@turf/turf";
import osmtogeojson from "osmtogeojson";
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

/**
 * Fetches the population of a specified ward using Overpass API.
 * @param wardName - The name of the ward to query.
 * @returns The population of the ward.
 */
async function getPopulationOfWard(wardName: string): Promise<number> {
  const overpassQuery = `
[out:json];
area["name"="東京都"]->.tokyo;
(
  relation["admin_level"="7"]["name"="${wardName}"](area.tokyo);
);
out tags;
`;
  const response = await fetchOverpassData(overpassQuery);
  let population = parseInt(response.elements[0].tags.population);
  if (isNaN(population)) {
    population = 0;
  }
  return population;
}

/**
 * Get the population density of a ward in Tokyo.
 * @param wardName - The name of the ward to calculate the population density.
 * @returns The population density of the ward.
 */
async function getPopulationDensityOfWards(wardName: string): Promise<number> {
  const population = await getPopulationOfWard(wardName);
  const areaKm2 = await getAreaOfWard(wardName);
  return population / areaKm2;
}

const findMostDenselyPopulatedWard = async (): Promise<string> => {
  const wards = await getAllWardsInTokyo();
  let maxPopulationDensity = 0;
  let mostDenselyPopulatedWard = "";
  for (const ward of wards) {
    const populationDensity = await getPopulationDensityOfWards(ward);
    console.info(
      `findMostDenselyPopulatedWard: ${ward} has ${populationDensity} people / km^2`
    );
    if (populationDensity > maxPopulationDensity) {
      maxPopulationDensity = populationDensity;
      mostDenselyPopulatedWard = ward;
    }
  }
  return mostDenselyPopulatedWard;
};

export default findMostDenselyPopulatedWard;
