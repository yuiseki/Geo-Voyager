// description: 世界のすべての国の英語名を取得する
// file_path: src/lib/skills/list/getAllCountriesEnglishNames.ts

import fs from "fs";

/**
 * @returns A list of English names of all countries in the world.
 */
const getAllCountriesEnglishNames = async (): Promise<string> => {
  const cachePath = "./tmp/cache/world_bank/countries_english_names.json";
  try {
    const cache = await fs.readFileSync(cachePath, "utf-8");
    return JSON.parse(cache).join("\n");
  } catch (e) {
    console.debug("Cache not found. Call World Bank API...");
  }
  let page = 1;
  let pages = 100;
  let result = [];
  while (page <= pages) {
    const endpoint = `https://api.worldbank.org/v2/country?format=json&page=${page}`;
    const res = await fetch(endpoint);
    if (!res.ok) {
      throw new Error(`HTTP error! status: ${res.status}`);
    }
    const data = await res.json();
    if (page === 1) {
      pages = data[0].pages;
    }
    const countries = data[1];
    for (const country of countries) {
      if (country.longitude.length === 0 || country.latitude.length === 0) {
        continue;
      }
      result.push(country.name);
    }
    page++;
  }
  // cache the data
  await fs.mkdirSync("./tmp/cache/world_bank", { recursive: true });
  await fs.writeFileSync(cachePath, JSON.stringify(result, null, 2), "utf-8");
  return result.join("\n");
};

export default getAllCountriesEnglishNames;
