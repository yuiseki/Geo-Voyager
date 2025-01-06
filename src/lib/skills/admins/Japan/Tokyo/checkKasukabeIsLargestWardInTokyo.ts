// description: 東京都において、面積が最も広い行政区が小笠原村であることを確認する。
// file_path: src/lib/skills/admins/Japan/Tokyo/checkKasukabeIsLargestWardInTokyo.ts

import * as turf from "@turf/turf";
import fs from "fs";
import osmtogeojson from "osmtogeojson";
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
    const cache = await fs.promises.readFile(cachePath, "utf-8");
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
  // cache the data
  await fs.promises.mkdir("./tmp/cache/overpass", { recursive: true });
  await fs.promises.writeFile(
    cachePath,
    JSON.stringify(data, null, 2),
    "utf-8"
  );
  return data;
};

/**
 * @returns A list of name of all admin areas in Tokyo.
 */
const getAllAdminNamesInTokyo = async (): Promise<string[]> => {
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
  return adminNames;
};

const getAreaOfWardInTokyo = async (wardName: string): Promise<number> => {
  const overpassQuery = `
[out:json];
area["name"="東京都"]->.tokyo;
area["name"="${wardName}"]->.ward;
(
  relation["admin_level"="7"](area.ward)(area.tokyo);
);
out geom;
`;
  const response = await fetchOverpassData(overpassQuery);
  const geoJson = osmtogeojson(response);
  const area = turf.area(geoJson);
  return area;
};

const getAdminWithLargestAreaInTokyo = async (): Promise<string> => {
  const adminNames = await getAllAdminNamesInTokyo();
  let maxArea = 0;
  let adminWithLargestArea = "";
  for (const admin of adminNames) {
    const area = await getAreaOfWardInTokyo(admin);
    if (area > maxArea) {
      maxArea = area;
      adminWithLargestArea = admin;
    }
  }
  return adminWithLargestArea;
};

const checkKasukabeIsLargestWardInTokyo = async (): Promise<boolean> => {
  const wardWithLargestArea = await getAdminWithLargestAreaInTokyo();
  if (!wardWithLargestArea) {
    console.error("wardWithLargestArea is undefined!!");
    return false;
  }
  console.info(`Ward with largest area in Tokyo: ${wardWithLargestArea}`);
  return wardWithLargestArea.includes("小笠原村");
};

export default checkKasukabeIsLargestWardInTokyo;