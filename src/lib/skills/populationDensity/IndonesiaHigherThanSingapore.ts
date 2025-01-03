// description: インドネシアの人口密度がシンガポールよりも高いことを確認する。
// file_path: src/lib/skills/populationDensity/IndonesiaHigherThanSingapore.ts

import * as turf from "@turf/turf";
import osmtogeojson from "osmtogeojson";

/**
 * @return boolean
 */
const isPopulationDensityOfIndonesiaHigherThanSingapore = async () => {
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

  // インドネシアの面積を取得
  const queryIndonesia = `[out:json];
relation["name"="Indonesia"]["admin_level"=2];
out geom;`;
  const resultIndonesia = await fetchOverpassData(queryIndonesia);
  if (resultIndonesia.elements.length === 0) {
    throw new Error(
      `Overpass API returned no data without errors. Please try to fix this query:\n${queryIndonesia}`
    );
  }
  const geoJsonIndonesia = osmtogeojson(resultIndonesia);
  if (geoJsonIndonesia.features.length === 0) {
    throw new Error(
      `osmtogeojson returned no GeoJSON data. Please try to fix this query:\n${queryIndonesia}`
    );
  }
  const areaIndonesia = turf.area(geoJsonIndonesia);
  // インドネシアの人口を取得
  const resultPopulationIndonesia = await fetchWorldBankTotalPopulation("id");
  const populationIndonesia = resultPopulationIndonesia[1][0].value;
  // インドネシアの人口密度を計算
  const populationDensityIndonesia = populationIndonesia / areaIndonesia;

  //シンガポールの面積を取得
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
  //シンガポールの人口を取得
  const resultPopulationSingapore = await fetchWorldBankTotalPopulation("sg");
  const populationSingapore = resultPopulationSingapore[1][0].value;
  //シンガポールの人口密度を計算
  const populationDensitySingapore = populationSingapore / areaSingapore;

  return populationDensityIndonesia > populationDensitySingapore;
};

export default isPopulationDensityOfIndonesiaHigherThanSingapore;