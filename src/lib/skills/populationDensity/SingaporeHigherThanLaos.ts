// description: シンガポールの人口密度がラオスよりも高いことを確認する。
// file_path: src/lib/skills/populationDensity/SingaporeHigherThanLaos.ts

import * as turf from "@turf/turf";
import osmtogeojson from "osmtogeojson";
import fetch from "node-fetch";

/**
 * Fetches data from the Overpass API.
 * @param query - The Overpass QL query to execute.
 * @returns Promise resolving to the JSON response from the Overpass API.
 */
const fetchOverpassData = async (query: string): Promise<any> => {
  const endpoint = "https://overpass-api.de/api/interpreter";
  const res = await fetch(endpoint, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
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
 * @returns Promise resolving to the population value.
 */
const fetchWorldBankPopulation = async (countryCode: string): Promise<number> => {
  const endpoint = `https://api.worldbank.org/v2/country/${countryCode}/indicator/SP.POP.TOTL?format=json`;
  const res = await fetch(endpoint);
  if (!res.ok) {
    throw new Error(`World Bank API request failed with status ${res.status}`);
  }
  const data = await res.json();
  return data[1][0].value as number;
};

/**
 * Calculates the population density of a country.
 * @param area - The area in square meters.
 * @param population - The total population.
 * @returns Population density in people per square kilometer.
 */
const calculatePopulationDensity = (area: number, population: number): number => {
  return (population / area) * 1e6; // Convert from m² to km²
};

/**
 * Checks if Singapore's population density is higher than Laos'.
 * @returns Promise resolving to a boolean indicating the result.
 */
const isPopulationDensityOfSingaporeHigherThanLaos = async (): Promise<boolean> => {
  try {
    // Fetch Singapore's area and population
    const querySingapore = `[out:json];
    relation["name"="Singapore"]["admin_level"=2];
    out body;
    >;
    out skel qt;`;
    const dataSingapore = await fetchOverpassData(querySingapore);
    const geoJsonSingapore = osmtogeojson(dataSingapore);
    const areaSingapore = turf.area(geoJsonSingapore);
    const populationSingapore = await fetchWorldBankPopulation("SG");

    // Fetch Laos's area and population
    const queryLaos = `[out:json];
    relation["name"="Laos"]["admin_level"=2];
    out body;
    >;
    out skel qt;`;
    const dataLaos = await fetchOverpassData(queryLaos);
    const geoJsonLaos = osmtogeojson(dataLaos);
    const areaLaos = turf.area(geoJsonLaos);
    const populationLaos = await fetchWorldBankPopulation("LA");

    // Calculate population densities
    const densitySingapore = calculatePopulationDensity(areaSingapore, populationSingapore);
    const densityLaos = calculatePopulationDensity(areaLaos, populationLaos);

    return densitySingapore > densityLaos;
  } catch (error) {
    console.error("Error checking population density:", error);
    throw error;
  }
};

export default isPopulationDensityOfSingaporeHigherThanLaos;