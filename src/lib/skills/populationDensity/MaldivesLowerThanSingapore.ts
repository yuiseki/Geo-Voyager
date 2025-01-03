// description: モルディブの人口密度がシンガポールより低いことを確認する。
// file_path: src/lib/skills/populationDensity/MaldivesLowerThanSingapore.ts

import * as turf from "@turf/turf";
import osmtogeojson from "osmtogeojson";

/**
 * @return boolean
 */
const isPopulationDensityOfMaldivesLowerThanSingapore = async () => {
  /**
   *
   * @param query Overpass QL
   * @returns Overpass API JSON
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
    return await res.json();
  };

  /**
   *
   * @param countryCode ISO 3166-1 alpha-2 country code
   * @returns JSON
   */
  const fetchWorldBankTotalPopulation = async (
    countryCode: string
  ): Promise<any> => {
    const endpoint = `https://api.worldbank.org/v2/country/${countryCode}/indicator/SP.POP.TOTL?&format=json`;
    const res = await fetch(endpoint);
    return await res.json();
  };

  // モルディブの面積を取得
  const queryMaldives = `[out:json];
relation["name:en"="Maldives"]["admin_level"=2];
out geom;`;
  const resultMaldives = await fetchOverpassData(queryMaldives);
  if (resultMaldives.elements.length === 0) {
    throw new Error(
      `Overpass API returned no data without errors. Please try to fix this query:\n${queryMaldives}`
    );
  }
  const geoJsonMaldives = osmtogeojson(resultMaldives);
  if (geoJsonMaldives.features.length === 0) {
    throw new Error(
      `osmtogeojson returned no GeoJSON data. Please try to fix this query:\n${queryMaldives}`
    );
  }
  const areaMaldives = turf.area(geoJsonMaldives);
  // モルディブの人口を取得
  const resultPopulationMaldives = await fetchWorldBankTotalPopulation("mv");
  const populationMaldives = resultPopulationMaldives[1][0].value;
  // モルディブの人口密度を計算
  const populationDensityMaldives = populationMaldives / areaMaldives;

  //シンガポールの面積と人口密度を取得（仮）
  const querySingapore = `[out:json];
relation["name"="Singapore"]["admin_level"=2];
out geom;`;
  const resultSingapore = await fetchOverpassData(querySingapore);
  if (resultSingapore.elements.length === 0) {
    throw new Error(
      `Overpass API returned no data without errors. Please try to fix this query:\n${querySingapore}`
    );
  }
  const geoJsonSingapore = osmtogeojson(resultSingapore);
  if (geoJsonSingapore.features.length === 0) {
    throw new Error(
      `osmtogeojson returned no GeoJSON data. Please try to fix this query:\n${querySingapore}`
    );
  }
  const areaSingapore = turf.area(geoJsonSingapore);
  //シンガポールの人口を取得（仮）
  const resultPopulationSingapore = await fetchWorldBankTotalPopulation("sg");
  const populationSingapore = resultPopulationSingapore[1][0].value;
  //シンガポールの人口密度を計算（仮）
  const populationDensitySingapore = populationSingapore / areaSingapore;

  return populationDensityMaldives < populationDensitySingapore;
};

export default isPopulationDensityOfMaldivesLowerThanSingapore;