// description: 世界で最も人口密度の高い国の ISO3166-1 Alpha-2 コードを取得する
// file_path: src/lib/skills/populationDensity/getMostDenselyPopulatedCountry.ts

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
 * @returns A list of all ISO3166-1 alpha-2 country codes.
 */
const getAllCountriesAlpha2Codes = async (): Promise<string> => {
  const overpassQuery = `
[out:json];
relation["admin_level"="2"];
out body;
`;
  const response = await fetchOverpassData(overpassQuery);
  const codes = response.elements
    .map((element: any) => {
      if ("ISO3166-1:alpha2" in element.tags) {
        return element.tags["ISO3166-1:alpha2"];
      } else {
        return null;
      }
    })
    .filter((code: string | null) => code !== null);
  return codes.join("\n");
};

const getMostDenselyPopulatedCountry = async (): Promise<string> => {
  const alpha2Codes = await getAllCountriesAlpha2Codes();
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
        mostDenselyPopulatedCountry = code;
      }
    } catch (error) {
      console.error(`getMostDenselyPopulatedCountry, ${code}: ${error}`);
      continue;
    }
  }
  return mostDenselyPopulatedCountry;
};

export default getMostDenselyPopulatedCountry;
