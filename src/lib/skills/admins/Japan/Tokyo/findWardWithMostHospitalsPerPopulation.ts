// description: 東京都において、人口あたりの病院の数が最も多い行政区を探す。
// file_path: src/lib/skills/admins/Japan/Tokyo/findWardWithMostHospitalsPerPopulation.ts

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
 * Fetches the number of hospitals in a specified ward using Overpass API.
 * @param wardName - The name of the ward to query.
 * @returns The total count of hospitals of the ward.
 */
async function getHospitalsCountOfWard(wardName: string): Promise<number> {
  const overpassQuery = `
[out:json];
area["name"="東京都"]->.out;
area["name"="${wardName}"]->.in;
(
  nwr["amenity"="hospital"](area.in)(area.out);
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
 * Calculates the number of hospitals per population in a specified ward.
 * @param wardName - The name of the ward to query.
 * @returns The number of hospitals per population of the ward.
 */
async function getHospitalsPerPopulationOfWard(
  wardName: string
): Promise<number> {
  const hospitalCount = await getHospitalsCountOfWard(wardName);
  const population = await getPopulationOfWard(wardName);
  if (population === 0) {
    return 0;
  }
  return population > 0 ? hospitalCount / population : 0;
}

const findWardWithMostHospitalsPerPopulation = async (): Promise<string> => {
  const wards = await getAllWardsInTokyo();
  let maxHospitalsPerPopulation = 0;
  let mostHospitalsPerPopulationWard = "";
  for (const ward of wards) {
    const hospitalsPerPopulation = await getHospitalsPerPopulationOfWard(ward);
    console.log(
      `findWardWithMostHospitalsPerPopulation: ${ward} has ${hospitalsPerPopulation} hospitals per population`
    );
    if (hospitalsPerPopulation > maxHospitalsPerPopulation) {
      maxHospitalsPerPopulation = hospitalsPerPopulation;
      mostHospitalsPerPopulationWard = ward;
    }
  }
  console.info(
    `Ward with most hospitals per population in Tokyo: ${mostHospitalsPerPopulationWard}`
  );
  return mostHospitalsPerPopulationWard;
};

export default findWardWithMostHospitalsPerPopulation;
