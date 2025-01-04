// description: バーレーンの人口密度がシンガポールよりも低いことを確認する。
// file_path: src/lib/skills/populationDensity/BahrainLowerThanSingapore.ts

import * as turf from "@turf/turf";
import osmtogeojson from "osmtogeojson";

/**
 * Fetches data from the Overpass API.
 * @param query - The Overpass QL query to execute.
 * @returns A promise that resolves to the JSON response from the Overpass API.
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
    throw new Error(`Overpass API request failed with status ${res.status}`);
  }
  return res.json();
};

/**
 * Fetches total population data from the World Bank API.
 * @param countryCode - The ISO 3166-1 alpha-2 country code.
 * @returns A promise that resolves to the JSON response containing population data.
 */
const fetchWorldBankPopulation = async (countryCode: string): Promise<any> => {
  const endpoint = `https://api.worldbank.org/v2/country/${countryCode}/indicator/SP.POP.TOTL?format=json`;
  const res = await fetch(endpoint);
  if (!res.ok) {
    throw new Error(`World Bank API request failed with status ${res.status}`);
  }
  return res.json();
};

/**
 * Calculates the population density of a country.
 * @param area - The area in square meters.
 * @param population - The total population.
 * @returns The population density in people per square kilometer.
 */
const calculatePopulationDensity = (
  area: number,
  population: number
): number => {
  return (population / area) * 1e6; // Convert from m² to km²
};

/**
 * Checks if the population density of Bahrain is lower than Singapore.
 * @returns A promise that resolves to true if Bahrain's population density is lower, otherwise false.
 */
const isPopulationDensityOfBahrainLowerThanSingapore =
  async (): Promise<boolean> => {
    try {
      // Fetch Bahrain data
      const bahrainQuery = `[out:json];
    relation["name:en"="Bahrain"]["admin_level"=2];
    out geom;`;
      const bahrainData = await fetchOverpassData(bahrainQuery);
      const geoJsonBahrain = osmtogeojson(bahrainData);
      const areaBahrain = turf.area(geoJsonBahrain);

      // Fetch Bahrain population
      const resultPopulationBahrain = await fetchWorldBankPopulation("BH");
      const populationBahrain = resultPopulationBahrain[1][0].value;

      // Calculate Bahrain's population density
      const populationDensityBahrain = calculatePopulationDensity(
        areaBahrain,
        populationBahrain
      );

      // Fetch Singapore data
      const singaporeQuery = `[out:json];
    relation["name"="Singapore"]["admin_level"=2];
    out geom;`;
      const singaporeData = await fetchOverpassData(singaporeQuery);
      const geoJsonSingapore = osmtogeojson(singaporeData);
      const areaSingapore = turf.area(geoJsonSingapore);

      // Fetch Singapore population
      const resultPopulationSingapore = await fetchWorldBankPopulation("SG");
      const populationSingapore = resultPopulationSingapore[1][0].value;

      // Calculate Singapore's population density
      const populationDensitySingapore = calculatePopulationDensity(
        areaSingapore,
        populationSingapore
      );

      // Compare population densities
      return populationDensityBahrain < populationDensitySingapore;
    } catch (error) {
      console.error("Error checking population density:", error);
      throw error;
    }
  };

export default isPopulationDensityOfBahrainLowerThanSingapore;
