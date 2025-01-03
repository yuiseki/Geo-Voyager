// description: 日本の人口密度が中国よりも高いことを確認する。
// file_path: src/lib/skills/populationDensity/JapanHigherThanChina.ts

import * as turf from "@turf/turf";
import osmtogeojson from "osmtogeojson";

/**
 * @return boolean
 */
const isPopulationDensityOfJapanHigherThanChina = async () => {
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

  // 日本の面積を取得
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
  // 日本の人口を取得
  const resultPopulationJapan = await fetchWorldBankTotalPopulation("jp");
  const populationJapan = resultPopulationJapan[1][0].value;
  // 日本の人口密度を計算
  const populationDensityJapan = populationJapan / areaJapan;

  // 中国の面積を取得
  const queryChina = `[out:json];
relation["name:en"="China"]["admin_level"=2];
out geom;`;
  const resultChina = await fetchOverpassData(queryChina);
  if (resultChina.elements.length === 0) {
    throw new Error(
      `Overpass API returned no data without errors. Please try to fix this query:\n${queryChina}`
    );
  }
  const geoJsonChina = osmtogeojson(resultChina);
  if (geoJsonChina.features.length === 0) {
    throw new Error(
      `osmtogeojson returned no GeoJSON data. Please try to fix this query:\n${queryChina}`
    );
  }
  const areaChina = turf.area(geoJsonChina);
  // 中国の人口を取得
  const resultChinaPopulation = await fetchWorldBankTotalPopulation("cn");
  const populationChina = resultChinaPopulation[1][0].value;
  // 中国の人口密度を計算
  const populationDensityChina = populationChina / areaChina;

  return populationDensityJapan > populationDensityChina;
};

export default isPopulationDensityOfJapanHigherThanChina;