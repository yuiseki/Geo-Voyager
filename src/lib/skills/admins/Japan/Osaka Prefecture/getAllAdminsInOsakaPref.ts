// description: 大阪府のすべての行政区の名前を取得する
// file_path: src/lib/skills/list/Japan/Osaka/getAllAdminsInOsaka.ts

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
 * @returns A list of all admin areas in Osaka Prefecture.
 */
const getAllAdminsInOsakaPref = async (): Promise<string> => {
  const overpassQuery = `
[out:json];
area["name"="大阪府"]->.osakaPref;
(
  relation["admin_level"="7"](area.osakaPref);
);
out tags;

`;
  const response = await fetchOverpassData(overpassQuery);
  const wards = response.elements.map((element: any) => element.tags.name);
  return wards.join("\n");
};

export default getAllAdminsInOsakaPref;
