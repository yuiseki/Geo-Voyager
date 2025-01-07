// description: 東京都において、人口あたりの図書館の数が最も多い行政区が千代田区であることを確認する。
// file_path: src/lib/skills/admins/Japan/Tokyo/checkChiyodaIsMostLibrariesPerPopulationWardInTokyo.ts

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
  // Cache the response
  await fs.writeFileSync(cachePath, JSON.stringify(data));
  return data;
};

/**
 * @returns A list of names of all admin areas in Tokyo.
 */
const getAllAdminNamesInTokyo = async (): Promise<string[]> => {
  const overpassQuery = `
    [out:json];
    area["name"="東京都"]->.tokyo;
    relation["admin_level"="7"](area.tokyo);
    out tags;
  `;
  const response = await fetchOverpassData(overpassQuery);
  return response.elements.map((element: any) => element.tags.name);
};

/**
 * Fetches the number of libraries in a specified admin area using Overpass API.
 * @param adminName - The name of the admin area to query.
 * @returns The total count of libraries in the admin area.
 */
async function getLibrariesCountInAdminInsideTokyo(
  adminName: string
): Promise<number> {
  const overpassQuery = `
    [out:json];
    area["name"="${adminName}"]->.a;
    nwr["amenity"="library"](area.a);
    out count;
  `;
  const response = await fetchOverpassData(overpassQuery);
  const count = response.elements[0].tags.total;
  return count;
}

/**
 * Fetches the population of a specified admin area using Overpass API.
 * @param adminName - The name of the admin area to query.
 * @returns The population of the admin area.
 */
async function getPopulationInAdminInsideTokyo(
  adminName: string
): Promise<number> {
  const overpassQuery = `
    [out:json];
    area["name"="東京都"]->.tokyo;
    relation["admin_level"="7"]["name"="${adminName}"](area.tokyo);
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
 * Calculates the number of libraries per population in a specified admin area.
 * @param adminName - The name of the admin area to query.
 * @returns The number of libraries per population.
 */
async function getLibrariesPerPopulationInAdminInsideTokyo(
  adminName: string
): Promise<number> {
  const libraryCount = await getLibrariesCountInAdminInsideTokyo(adminName);
  const population = await getPopulationInAdminInsideTokyo(adminName);
  if (population === 0) {
    return 0;
  }
  return libraryCount / population;
}

const getMostLibrariesPerPopulationAdminInTokyo = async (): Promise<string> => {
  const adminAreas = await getAllAdminNamesInTokyo();
  let maxLibrariesPerPopulation = 0;
  let mostLibrariesPerPopulationAdmin = "";

  for (const admin of adminAreas) {
    if (admin === "") continue; // Skip empty lines
    const librariesPerPopulation =
      await getLibrariesPerPopulationInAdminInsideTokyo(admin);
    if (librariesPerPopulation > maxLibrariesPerPopulation) {
      maxLibrariesPerPopulation = librariesPerPopulation;
      mostLibrariesPerPopulationAdmin = admin;
    }
  }

  return mostLibrariesPerPopulationAdmin;
};

const checkChiyodaIsMostLibrariesPerPopulationWardInTokyo =
  async (): Promise<boolean> => {
    const mostLibrariesPerPopulationAdmin =
      await getMostLibrariesPerPopulationAdminInTokyo();
    console.info(
      "Most libraries per population admin in Tokyo:",
      mostLibrariesPerPopulationAdmin
    );
    return mostLibrariesPerPopulationAdmin.includes("千代田区");
  };

export default checkChiyodaIsMostLibrariesPerPopulationWardInTokyo;