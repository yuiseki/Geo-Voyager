// description: バーレーンの人口密度がモナコよりも低いことを確認する。
// file_path: src/lib/skills/populationDensity/BahrainLowerThanMonaco.ts

import * as turf from "@turf/turf";
import osmtogeojson from "osmtogeojson";

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
  return res.json();
};

/**
 * Fetches total population data from the World Bank API.
 * @param countryCode - The ISO 3166-1 alpha-2 country code.
 * @returns Promise resolving to JSON data containing the population.
 */
const fetchWorldBankPopulation = async (countryCode: string): Promise<any> => {
  const endpoint = `https://api.worldbank.org/v2/country/${countryCode}/indicator/SP.POP.TOTL?format=json`;
  const res = await fetch(endpoint);
  if (!res.ok) {
    throw new Error(`HTTP error! status: ${res.status}`);
  }
  return res.json();
};

/**
 * Calculates the population density of a country.
 * @param geojsonData - GeoJSON data representing the country's boundaries.
 * @param population - The total population of the country.
 * @returns Population density in people per square kilometer.
 */
const calculatePopulationDensity = (geojsonData: any, population: number): number => {
  const area = turf.area(geojsonData); // Area in square meters
  const areaInKm2 = area / 1000000; // Convert to square kilometers
  return population / areaInKm2;
};

/**
 * Checks if Bahrain's population density is lower than Monaco's.
 * @returns Promise resolving to a boolean indicating the result.
 */
const isBahrainPopulationDensityLowerThanMonaco = async (): Promise<boolean> => {
  try {
    // Fetch Bahrain's geojson data
    const bahrainQuery = `[out:json];relation["name:en"="Bahrain"]["admin_level"=2];out geom;>;`;
    const bahrainData = await fetchOverpassData(bahrainQuery);
    const bahrainGeojsonData = osmtogeojson(bahrainData);

    // Fetch Monaco's geojson data
    const monacoQuery = `[out:json];relation["name"="Monaco"]["admin_level"=2];out geom;`;
    const monacoData = await fetchOverpassData(monacoQuery);
    const monacoGeojsonData = osmtogeojson(monacoData);

    // Fetch Bahrain's population
    const bahrainPopulationData = await fetchWorldBankPopulation("BH");
    const bahrainPopulation = bahrainPopulationData[1][0].value;

    // Fetch Monaco's population
    const monacoPopulationData = await fetchWorldBankPopulation("MC");
    const monacoPopulation = monacoPopulationData[1][0].value;

    // Calculate population densities
    const bahrainDensity = calculatePopulationDensity(bahrainGeojsonData, bahrainPopulation);
    const monacoDensity = calculatePopulationDensity(monacoGeojsonData, monacoPopulation);

    // Compare and return result
    return bahrainDensity < monacoDensity;
  } catch (error) {
    console.error("Error fetching data:", error);
    throw error;
  }
};

export default isBahrainPopulationDensityLowerThanMonaco;