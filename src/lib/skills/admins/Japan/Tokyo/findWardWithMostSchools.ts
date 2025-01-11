// description: 東京都において、学校の数が最も多い行政区を探す。
// file_path: src/lib/skills/admins/Japan/Tokyo/findWardWithMostSchools.ts

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
 * Fetches the number of schools in a specified ward using Overpass API.
 * @param wardName - The name of the ward to query.
 * @returns The total count of schools in the ward.
 */
async function getSchoolCountByWard(wardName: string): Promise<number> {
  const overpassQuery = `
[out:json];
area["name"="東京都"]->.out;
area["name"="${wardName}"]->.in;
(
  nwr["amenity"="school"](area.in)(area.out);
);
out count;
`;
  const response = await fetchOverpassData(overpassQuery);
  return response.elements[0].tags.total;
}

const findWardWithMostSchools = async (): Promise<string> => {
  const wards = await getAllWardsInTokyo();
  let maxSchools = 0;
  let wardWithMostSchools = "";
  for (const ward of wards) {
    const schoolCount = await getSchoolCountByWard(ward);
    console.log(`findWardWithMostSchools: ${ward} has ${schoolCount} schools`);
    if (schoolCount > maxSchools) {
      maxSchools = schoolCount;
      wardWithMostSchools = ward;
    }
  }
  return wardWithMostSchools;
};

export default findWardWithMostSchools;
