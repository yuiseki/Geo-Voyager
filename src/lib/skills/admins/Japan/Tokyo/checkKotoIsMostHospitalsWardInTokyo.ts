// description: 東京都において、病院が最も多い行政区が江東区であることを確認する。
// file_path: src/lib/skills/admins/Japan/Tokyo/checkKotoIsMostHospitalsWardInTokyo.ts

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
 * Fetches the number of hospitals in a specified admin area using Overpass API.
 * @param adminName - The name of the admin area to query.
 * @returns The total count of hospitals in the admin area.
 */
async function getHospitalCountByAdminInsideTokyo(
  adminName: string
): Promise<number> {
  const overpassQuery = `
[out:json];
area["name"="東京都"]->.tokyo;
area["name"="${adminName}"]->.ward;
(
  nwr["amenity"="hospital"](area.ward)(area.tokyo);
);
out count;
`;

  const response = await fetchOverpassData(overpassQuery);
  return response.elements[0].tags.total;
}

const getAdminWithMostHospitalsInTokyo = async (): Promise<string> => {
  const adminAreas = await getAllAdminNamesInTokyo();
  let maxHospitals = 0;
  let wardWithMostHospitals = "";
  for (const adminArea of adminAreas.split("\n")) {
    const hospitalCount = await getHospitalCountByAdminInsideTokyo(adminArea);
    if (hospitalCount > maxHospitals) {
      maxHospitals = hospitalCount;
      wardWithMostHospitals = adminArea;
    }
  }
  return wardWithMostHospitals;
};

const checkKotoIsMostHospitalsWardInTokyo = async (): Promise<boolean> => {
  const wardWithMostHospitals = await getAdminWithMostHospitalsInTokyo();
  console.info(`Ward with most hospitals in Tokyo: ${wardWithMostHospitals}`);
  return wardWithMostHospitals.includes("江東区");
};

export default checkKotoIsMostHospitalsWardInTokyo;
