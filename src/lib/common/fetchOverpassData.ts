import fs from "fs";
import { Md5 } from "ts-md5";

/**
 * Sleeps for the specified duration in milliseconds.
 * @param ms - The number of milliseconds to sleep.
 * @returns A promise that resolves after the specified time.
 */
const sleep = (ms: number): Promise<void> => new Promise(resolve => setTimeout(resolve, ms));

/**
 * Fetches data from the Overpass API.
 * @param query - The Overpass QL query string.
 * @returns Promise resolving to JSON data from the Overpass API.
 */
export const fetchOverpassData = async (query: string): Promise<any> => {
  const md5 = new Md5();
  md5.appendStr(query);
  const hash = md5.end();
  const cachePath = `./tmp/cache/overpass/query_${hash}.json`;
  try {
    const cache = await fs.promises.readFile(cachePath, "utf-8");
    return JSON.parse(cache);
  } catch (e) {
    console.log("Cache not found. Calling Overpass API...");
  }
  
  // APIリクエスト前に1秒待機
  await sleep(1000);
  
  const endpoint = "https://overpass-api.de/api/interpreter";
  const res = await fetch(endpoint, {
    method: "POST",
    headers: {
      "Content-Type": "application/x-www-form-urlencoded",
    },
    body: `data=${encodeURIComponent(query)}`,
  });
  if (!res.ok) {
    console.log("Error fetching data from Overpass API:", res.status);
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
