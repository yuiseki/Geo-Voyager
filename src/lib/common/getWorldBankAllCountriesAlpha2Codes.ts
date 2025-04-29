import fs from "fs";

/**
 * @returns A list of all countries' ISO3166-1 alpha-2 codes.
 */
export const getWorldBankAllCountriesAlpha2Codes = async (): Promise<
  string[]
> => {
  let result;
  const cachePath = "./tmp/cache/world_bank/countries_alpha2_codes.json";
  try {
    const cache = await fs.readFileSync(cachePath, "utf-8");
    result = JSON.parse(cache);
  } catch (e) {
    console.debug("Cache not found. Call World Bank countries API...");
    let page = 1;
    let pages = 100;
    let data = [];
    while (page <= pages) {
      const endpoint = `https://api.worldbank.org/v2/country?format=json&page=${page}`;
      const res = await fetch(endpoint);
      if (!res.ok) {
        throw new Error(`HTTP error! status: ${res.status}`);
      }
      const json = await res.json();
      if (page === 1) {
        pages = json[0].pages;
      }
      const countries = json[1];
      for (const country of countries) {
        if (country.longitude.length === 0 || country.latitude.length === 0) {
          continue;
        }
        data.push(country.iso2Code);
      }
      page++;
    }
    // cache the data
    await fs.mkdirSync("./tmp/cache/world_bank", { recursive: true });
    await fs.writeFileSync(cachePath, JSON.stringify(data, null, 2), "utf-8");
    result = data;
  }
  return result;
};
