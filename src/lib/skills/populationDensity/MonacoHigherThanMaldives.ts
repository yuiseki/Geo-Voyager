// description: モナコの人口密度がモルディブよりも高いことを確認する。
// file_path: src/lib/skills/populationDensity/MonacoHigherThanMaldives.ts

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
  const data = await res.json();
  if (!data.elements || data.elements.length === 0) {
    throw new Error(
      `Overpass API returned no data without errors. Please try to fix this query:\n${query}`
    );
  }
  return data;
};

/**
 * Fetches total population data from the World Bank API.
 * @param countryCode - The ISO 3166-1 alpha-2 country code.
 * @returns Promise resolving to JSON data containing the population.
 */
const fetchWorldBankTotalPopulation = async (
  countryCode: string
): Promise<any> => {
  const endpoint = `https://api.worldbank.org/v2/country/${countryCode}/indicator/SP.POP.TOTL?format=json`;
  const res = await fetch(endpoint);
  if (!res.ok) {
    throw new Error(`HTTP error! status: ${res.status}`);
  }
  const data = await res.json();
  if (data.length === 0 || data[1].length === 0) {
    throw new Error(`No population data found for country code ${countryCode}`);
  }
  return data;
};

/**
 * Calculates the population density of a country.
 * @param geojsonData - GeoJSON data representing the country's boundaries.
 * @param population - The total population of the country.
 * @returns Population density in people per square kilometer.
 */
const calculatePopulationDensity = (
  geojsonData: any,
  population: number
): number => {
  const area = turf.area(geojsonData); // Area in square meters
  const areaInKm2 = area / 1000000; // Convert to square kilometers
  return population / areaInKm2;
};

/**
 * Checks if Monaco's population density is higher than Maldives's.
 * @returns Promise resolving to a boolean indicating whether Monaco's population density is higher.
 */
const isPopulationDensityOfMonacoHigherThanMaldives =
  async (): Promise<boolean> => {
    // Fetch Monaco's GeoJSON data
    const monacoOverpassQuery = `[out:json];relation["name"="Monaco"]["admin_level"=2];out geom;`;
    const monacoOverpassData = await fetchOverpassData(monacoOverpassQuery);
    const monacoGeojsonData = osmtogeojson(monacoOverpassData);
    // Fetch Monaco's population data
    const monacoPopulationData = await fetchWorldBankTotalPopulation("mc");
    const monacoPopulation = monacoPopulationData[1][0].value;
    // Calculate Monaco's population density
    const monacoPopulationDensity = calculatePopulationDensity(
      monacoGeojsonData,
      monacoPopulation
    );

    // Fetch Maldives's geojson data
    const maldivesOverpassQuery = `[out:json];relation["name:en"="Maldives"]["admin_level"=2];out geom;`;
    const maldivesOverpassData = await fetchOverpassData(maldivesOverpassQuery);
    const maldivesGeojsonData = osmtogeojson(maldivesOverpassData);
    // Fetch Maldives's population
    const maldivesPopulationData = await fetchWorldBankTotalPopulation("mv");
    const maldivesPopulation = maldivesPopulationData[1][0].value;
    // Calculate Maldives's population density
    const maldivesPopulationDensity = calculatePopulationDensity(
      maldivesGeojsonData,
      maldivesPopulation
    );
    // Compare the population densities
    return monacoPopulationDensity > maldivesPopulationDensity;
  };

export default isPopulationDensityOfMonacoHigherThanMaldives;
