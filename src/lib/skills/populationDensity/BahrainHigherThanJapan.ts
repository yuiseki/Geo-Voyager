// description: バーレーンの人口密度が日本よりも高いことを確認する。
// file_path: src/lib/skills/populationDensity/BahrainHigherThanJapan.ts

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
  return res.json();
};

/**
 * Fetches total population data from the World Bank API.
 * @param countryCode - The ISO 3166-1 alpha-2 country code.
 * @returns Promise resolving to JSON data containing the population.
 */
const fetchWorldBankTotalPopulation = async (countryCode: string): Promise<any> => {
  const endpoint = `https://api.worldbank.org/v2/country/${countryCode}/indicator/SP.POP.TOTL?format=json`;
  const res = await fetch(endpoint);
  return res.json();
};

/**
 * Checks if Bahrain's population density is higher than Japan's.
 * @returns Promise resolving to a boolean indicating the result.
 */
const isPopulationDensityOfBahrainHigherThanJapan = async (): Promise<boolean> => {
  // Fetch Bahrain's area and population
  const queryBahrain = `[out:json];
  relation["name:en"="Bahrain"]["admin_level"=2];
  out geom;`;
  const resultBahrain = await fetchOverpassData(queryBahrain);
  if (resultBahrain.elements.length === 0) {
    throw new Error(
      `Overpass API returned no data without errors. Please try to fix this query:\n${queryBahrain}`
    );
  }
  const geoJsonBahrain = osmtogeojson(resultBahrain);
  if (geoJsonBahrain.features.length === 0) {
    throw new Error(
      `osmtogeojson returned no GeoJSON data. Please try to fix this query:\n${queryBahrain}`
    );
  }
  const areaBahrain = turf.area(geoJsonBahrain);
  const resultBahrainPopulation = await fetchWorldBankTotalPopulation("BH");
  const populationBahrain = resultBahrainPopulation[1][0].value;
  const populationDensityBahrain = populationBahrain / areaBahrain;

  // Fetch Japan's area and population
  const queryJapan = `[out:json];
  relation["name:en"="Japan"]["admin_level"=2];
  out geom;`;
  const resultJapan = await fetchOverpassData(queryJapan);
  if (resultJapan.elements.length === 0) {
    throw new Error(
      `Overpass API returned no data without errors. Please try to fix this query:\n${queryJapan}`
    );
  }
  const geoJsonJapan = osmtogeojson(resultJapan);
  if (geoJsonJapan.features.length === 0) {
    throw new Error(
      `osmtogeojson returned no GeoJSON data. Please try to fix this query:\n${queryJapan}`
    );
  }
  const areaJapan = turf.area(geoJsonJapan);
  const resultJapanPopulation = await fetchWorldBankTotalPopulation("JP");
  const populationJapan = resultJapanPopulation[1][0].value;
  const populationDensityJapan = populationJapan / areaJapan;

  return populationDensityBahrain > populationDensityJapan;
};

export default isPopulationDensityOfBahrainHigherThanJapan;