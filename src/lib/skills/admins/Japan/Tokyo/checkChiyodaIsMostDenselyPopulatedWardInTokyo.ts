// description: 東京都において、人口密度が最も高い行政区が千代田区であることを確認する。
// file_path: src/lib/skills/admins/Japan/Tokyo/checkChiyodaIsMostDenselyPopulatedWardInTokyo.ts

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
 * @returns A list of name of all admin areas in Tokyo.
 */
const getAllAdminNamesInTokyo = async (): Promise<string> => {
  const overpassQuery = `
[out:json];
area["name"="東京都"]->.tokyo;
(
  relation["admin_level"="7"](area.tokyo);
);
out tags;
`;
  const response = await fetchOverpassData(overpassQuery);
  const adminNames = response.elements.map((element: any) => element.tags.name);
  return adminNames.join("\n");
};

/**
 * Fetches the number of schools in a specified admin area using Overpass API.
 * @param adminName - The name of the admin area to query.
 * @returns The total count of schools in the admin area.
 */
async function getPopulationDensityOfAdminInsideTokyo(
  adminName: string
): Promise<number> {
  const overpassQuery = `
[out:json];
area["name"="東京都"]->.tokyo;
(
  relation["name"="${adminName}"]["admin_level"="7"](area.tokyo);
);
out geom;
`;
  const response = await fetchOverpassData(overpassQuery);
  const geojson = osmtogeojson(response);
  // area in square meters
  const area = turf.area(geojson.features[0]);
  const areaKm2 = area / 1000000;
  let population = parseInt(response.elements[0].tags.population);
  if (isNaN(population)) {
    population = 0;
  }
  return population / areaKm2;
}

const getMostDenselyPopulatedAdminInTokyo = async (): Promise<string> => {
  const adminAreas = await getAllAdminNamesInTokyo();
  let maxPopulationDensity = 0;
  let mostDenselyPopulatedAdmin = "";
  for (const admin of adminAreas.split("\n")) {
    const populationDensity = await getPopulationDensityOfAdminInsideTokyo(
      admin
    );
    if (populationDensity > maxPopulationDensity) {
      maxPopulationDensity = populationDensity;
      mostDenselyPopulatedAdmin = admin;
    }
  }
  return mostDenselyPopulatedAdmin;
};

const checkChiyodaIsMostDenselyPopulatedWardInTokyo =
  async (): Promise<boolean> => {
    const mostDenselyPopulatedAdmin =
      await getMostDenselyPopulatedAdminInTokyo();
    console.info(
      "Most densely populated admin in Tokyo:",
      mostDenselyPopulatedAdmin
    );
    return mostDenselyPopulatedAdmin.includes("千代田区");
  };

export default checkChiyodaIsMostDenselyPopulatedWardInTokyo;
