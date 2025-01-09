// description: 東京都において、人口あたりの図書館の数が最も多い行政区を探す
// file_path: src/lib/skills/admins/Japan/Tokyo/findWardWithMostLibrariesPerPopulation.ts

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
  await fs.writeFileSync(cachePath, JSON.stringify(data, null, 2));
  return data;
};

/**
 * @returns A list of names of all wards in Tokyo.
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
  return response.elements.map((element: any) => element.tags.name);
};

/**
 * Fetches the number of libraries in a specified ward using Overpass API.
 * @param wardName - The name of the ward to query.
 * @returns The total count of libraries of the ward.
 */
async function getLibrariesCountOfWard(
  wardName: string
): Promise<number> {
  const overpassQuery = `
[out:json];
area["name"="東京都"]->.out;
area["name"="${wardName}"]->.in;
(
  nwr["amenity"="library"](area.in)(area.out);
);
out count;
`;
  const response = await fetchOverpassData(overpassQuery);
  return response.elements[0].tags.total;
}

/**
 * Fetches the population of a specified ward using Overpass API.
 * @param wardName - The name of the ward to query.
 * @returns The population of the ward.
 */
async function getPopulationOfWard(
  wardName: string
): Promise<number> {
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
 * Calculates the number of libraries per population in a specified ward.
 * @param wardName - The name of the ward to query.
 * @returns The number of libraries per population of the ward.
 */
async function getLibrariesPerPopulationOfWard(
  wardName: string
): Promise<number> {
  const libraryCount = await getLibrariesCountOfWard(wardName);
  const population = await getPopulationOfWard(wardName);
  if (population === 0) {
    return 0;
  }
  return libraryCount / population;
}

const findWardWithMostLibrariesPerPopulation = async (): Promise<string> => {
  const wards = await getAllWardsInTokyo();
  let maxLibrariesPerPopulation = 0;
  let mostLibrariesPerPopulationWard = "";

  for (const ward of wards) {
    if (ward === "") continue; // Skip empty lines
    const librariesPerPopulation =
      await getLibrariesPerPopulationOfWard(ward);
    console.log(
      `findWardWithMostLibrariesPerPopulation: ${ward} has ${librariesPerPopulation} libraries per population`
    );
    if (librariesPerPopulation > maxLibrariesPerPopulation) {
      maxLibrariesPerPopulation = librariesPerPopulation;
      mostLibrariesPerPopulationWard = ward;
    }
  }
  console.log(
    `Ward with most libraries per population: ${mostLibrariesPerPopulationWard}`
  );
  return mostLibrariesPerPopulationWard;
};

export default findWardWithMostLibrariesPerPopulation;
