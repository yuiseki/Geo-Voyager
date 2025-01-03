// description: 文京区の学校の数が新宿区よりも多いことを確認する。
// file_path: src/lib/skills/populationDensity/ShinjukuHigherThanBunkyo.ts

import * as turf from "@turf/turf";
import osmtogeojson from "osmtogeojson";

/**
 * Fetches data from the Overpass API.
 * @param query - The Overpass QL query to execute.
 * @returns The JSON response from the Overpass API.
 */
const fetchOverpassData = async (query: string): Promise<any> => {
  const endpoint = "https://overpass-api.de/api/interpreter";
  const res = await fetch(endpoint, {
    method: "POST",
    headers: {
      "Content-Type": "application/x-www-form-urlencoded",
    },
    body: `data=${encodeURIComponent(query)}`,
  });
  return await res.json();
};

/**
 * Counts the number of schools in a given area.
 * @param areaName - The name of the area to count schools in.
 * @returns The number of schools in the specified area.
 */
const countSchoolsInArea = async (areaName: string): Promise<number> => {
  const query = `
    [out:json];
    area[name="${areaName}"]->.searchArea;
    (
      node["amenity"="school"](area.searchArea);
      way["amenity"="school"](area.searchArea);
      relation["amenity"="school"](area.searchArea);
    );
    out count;
  `;
  const data = await fetchOverpassData(query);
  return data.elements.length;
};

/**
 * Compares the number of schools in Shinjuku and Bunkyo.
 * @returns True if Shinjuku has more schools than Bunkyo, false otherwise.
 */
const isShinjukuHigherThanBunkyo = async (): Promise<boolean> => {
  const shinjukuSchoolCount = await countSchoolsInArea("Shinjuku");
  const bunkyoSchoolCount = await countSchoolsInArea("Bunkyo");

  return shinjukuSchoolCount > bunkyoSchoolCount;
};

export default isShinjukuHigherThanBunkyo;