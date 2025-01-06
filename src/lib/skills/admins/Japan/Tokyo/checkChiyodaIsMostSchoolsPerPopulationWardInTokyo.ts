// description: 東京都において、人口あたりの学校の数が最も多い行政区が千代田区であることを確認する。
// file_path: src/lib/skills/admins/Japan/Tokyo/checkChiyodaIsMostSchoolsPerPopulationWardInTokyo.ts

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
async function getSchoolCountInAdminInsideTokyo(
  adminName: string
): Promise<number> {
  const overpassQuery = `
[out:json];
area["name"="東京都"]->.tokyo;
area["name"="${adminName}"]->.admin;
(
  nwr["amenity"="school"](area.admin)(area.tokyo);
);
out count;
`;
  const response = await fetchOverpassData(overpassQuery);
  return response.elements.length;
}

/**
 * Calculates the number of schools per population in a specified admin area.
 * @param adminName - The name of the admin area to query.
 * @returns The number of schools per population.
 */
async function getSchoolsPerPopulationInAdminInsideTokyo(
  adminName: string
): Promise<number> {
  const schoolCount = await getSchoolCountInAdminInsideTokyo(adminName);
  const overpassQuery = `
[out:json];
area["name"="東京都"]->.tokyo;
(
  relation["admin_level"="7"]["name"="${adminName}"](area.tokyo);
);
out tags;
`;
  const response = await fetchOverpassData(overpassQuery);
  let population = parseInt(response.elements[0].tags.population);
  if (isNaN(population)) {
    population = 0;
  }
  return population > 0 ? schoolCount / population : 0;
}

const getMostSchoolsPerPopulationAdminInTokyo = async (): Promise<string> => {
  const adminAreas = await getAllAdminNamesInTokyo();
  let maxSchoolsPerPopulation = 0;
  let wardWithMaxSchoolsPerPopulation = "";
  for (const adminArea of adminAreas.split("\n")) {
    const schoolsPerPopulation =
      await getSchoolsPerPopulationInAdminInsideTokyo(adminArea);
    if (schoolsPerPopulation > maxSchoolsPerPopulation) {
      maxSchoolsPerPopulation = schoolsPerPopulation;
      wardWithMaxSchoolsPerPopulation = adminArea;
    }
  }
  return wardWithMaxSchoolsPerPopulation;
};

const checkChiyodaIsMostSchoolsPerPopulationWardInTokyo =
  async (): Promise<boolean> => {
    const mostSchoolsPerPopulationAdmin =
      await getMostSchoolsPerPopulationAdminInTokyo();
    console.info(
      `Ward with most schools per population in Tokyo: ${mostSchoolsPerPopulationAdmin}`
    );
    return mostSchoolsPerPopulationAdmin.includes("千代田区");
  };

export default checkChiyodaIsMostSchoolsPerPopulationWardInTokyo;
