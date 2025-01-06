// description: 世界のすべての国の ISO3166-1 Alpha-3 コードを取得する。
// file_path: src/lib/skills/list/getAllCountriesAlpha3Codes.ts

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
 * @returns A list of all ISO3166-1 alpha-3 country codes.
 */
const getAllCountriesAlpha3Codes = async (): Promise<string> => {
  const overpassQuery = `
[out:json];
relation["admin_level"="2"];
out tags;
`;
  const response = await fetchOverpassData(overpassQuery);
  const codes = response.elements.map((element: any) => {
    if ("ISO3166-1:alpha3" in element.tags) {
      return element.tags["ISO3166-1:alpha3"];
    }
  });
  return codes.join("\n");
};

export default getAllCountriesAlpha3Codes;
