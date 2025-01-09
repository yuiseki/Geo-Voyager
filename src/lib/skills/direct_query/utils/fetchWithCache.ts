import { Md5 } from "ts-md5";
import * as fs from "fs";

interface CacheConfig {
  ttlSeconds?: number;
  directory: string;
}

/**
 * Fetches data with caching support
 * @param url - The URL to fetch data from
 * @param config - Cache configuration
 * @returns Promise resolving to the fetched data
 */
export const fetchWithCache = async (
  url: string,
  config: CacheConfig
): Promise<any> => {
  const md5 = new Md5();
  md5.appendStr(url);
  const hash = md5.end() as string;
  const cachePath = `./tmp/cache/${config.directory}/query_${hash}.json`;

  // Check cache if TTL hasn't expired
  try {
    const stats = await fs.promises.stat(cachePath);
    const age = (Date.now() - stats.mtimeMs) / 1000;
    if (!config.ttlSeconds || age < config.ttlSeconds) {
      const cached = await fs.promises.readFile(cachePath, "utf-8");
      return JSON.parse(cached);
    }
  } catch (e) {
    console.debug("Cache not found or expired. Fetching fresh data...");
  }

  // Fetch fresh data
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }
  const data = await response.json();

  // Cache the fresh data
  await fs.promises.mkdir(`./tmp/cache/${config.directory}`, { recursive: true });
  await fs.promises.writeFile(cachePath, JSON.stringify(data, null, 2), "utf-8");

  return data;
};
