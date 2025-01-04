// description: 世界で最も人口密度の高い国の ISO3166-1 Alpha-2 コードを取得する
// file_path: src/lib/skills/populationDensity/getWorldsMostDenselyPopulatedCountry.ts

/**
 * Fetches data from the Overpass API.
 * @param query - The Overpass QL query string.
 * @returns Promise resolving to JSON data from the Overpass API.
 */
const fetchOverpassData = async (query: string): Promise<any> => {
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
  if (!data.elements || data.elements.length === 0) {
    throw new Error(
      `Overpass API returned no data without errors. Please try to fix this query:\n${query}`
    );
  }
  return data;
};

/**
 * Fetches population density data from the World Bank API.
 * @param countryCode - The ISO 3166-1 alpha-2 country code.
 * @returns Promise resolving to JSON data containing the population density.
 */
const fetchWorldBankPopulationDensity = async (
  countryCode: string
): Promise<any> => {
  const endpoint = `https://api.worldbank.org/v2/country/${countryCode}/indicator/EN.POP.DNST?format=json`;
  const res = await fetch(endpoint);
  if (!res.ok) {
    throw new Error(`HTTP error! status: ${res.status}`);
  }
  const data = await res.json();
  if (data.length === 0 || !data[1] || data[1].length === 0) {
    throw new Error(
      `No population density data found for country code ${countryCode}`
    );
  }
  const rows = data[1];
  const value = rows.filter(
    (row: any) => row.value !== null && row.value !== 0
  )[0].value;
  return value;
};

/**
 * @returns A list of all countries' ISO3166-1 alpha-2 codes.
 */
const fetchAllCountriesAlpha2Code = async (): Promise<string> => {
  let page = 1;
  let pages = 100;
  let result = "";
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
      result += `${country.iso2Code}\n`;
    }
    page++;
  }
  return result;
};

/**
 * Fetches the country name by ISO3166-1 alpha-2 code.
 * @param alpha2Code - The ISO3166-1 alpha-2 country code.
 * @returns The name of the country.
 */
const getCountryNameByAlpha2Code = async (
  alpha2Code: string
): Promise<string> => {
  const endpoint = `https://api.worldbank.org/v2/country/${alpha2Code}?format=json`;
  const res = await fetch(endpoint);
  if (!res.ok) {
    throw new Error(`HTTP error! status: ${res.status}`);
  }
  const data = await res.json();
  if (data.length === 0 || !data[1] || data[1].length === 0) {
    throw new Error(`No country data found for country code ${alpha2Code}`);
  }
  return data[1][0].name;
};

/**
 * @returns The ISO3166-1 alpha-2 country code of the most densely populated country.
 */
const getWorldsMostDenselyPopulatedCountry = async (): Promise<string> => {
  const alpha2Codes = await fetchAllCountriesAlpha2Code();
  let mostDenselyPopulatedCountry = "";
  let highestPopulationDensity = 0;
  for (const code of alpha2Codes.split("\n")) {
    try {
      const populationDensity = await fetchWorldBankPopulationDensity(code);
      console.log(
        `getMostDenselyPopulatedCountry, ${code}: ${populationDensity}`
      );
      if (populationDensity > highestPopulationDensity) {
        highestPopulationDensity = populationDensity;
        mostDenselyPopulatedCountry = await getCountryNameByAlpha2Code(code);
      }
    } catch (error) {
      console.error(`getMostDenselyPopulatedCountry, ${code}: ${error}`);
      continue;
    }
  }
  return mostDenselyPopulatedCountry;
};

export default getWorldsMostDenselyPopulatedCountry;
