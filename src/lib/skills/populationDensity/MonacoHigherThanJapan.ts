// description: モナコの人口密度が日本よりも高いことを確認する。
// file_path: src/lib/skills/populationDensity/MonacoHigherThanJapan.ts
import * as turf from "@turf/turf";
import osmtogeojson from "osmtogeojson";

/**
 * @return boolean
 */
const isPopulationDensityOfMonacoHigherThanJapan = async () => {
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
  const fetchWorldBank = async (countryCode: string): Promise<any> => {
    const endpoint = `https://api.worldbank.org/v2/country/${countryCode}/indicator/SP.POP.TOTL?&format=json`;
    const res = await fetch(endpoint);
    return await res.json();
  };

  // モナコの面積を取得
  const queryMonaco = `[out:json];
relation["name"="Monaco"]["admin_level"=2];
out geom;`;
  const resultMonaco = await fetchOverpassData(queryMonaco);
  const geoJsonMonaco = osmtogeojson(resultMonaco);
  const areaMonaco = turf.area(geoJsonMonaco);
  // モナコの人口を取得
  let populationMonaco = geoJsonMonaco.features[0].properties?.population;
  if (isNaN(populationMonaco)) {
    const result = await fetchWorldBank("mc");
    populationMonaco = result[1][0].value;
  }
  // モナコの人口密度を計算
  const populationDensityMonaco = populationMonaco / areaMonaco;

  // 日本の面積を取得
  const queryJapan = `[out:json];
relation["name:en"="Japan"]["admin_level"=2];
out geom;`;
  const resultJapan = await fetchOverpassData(queryJapan);
  const geoJsonJapan = osmtogeojson(resultJapan);
  const areaJapan = turf.area(geoJsonJapan);
  // 日本の人口を取得
  let populationJapan = geoJsonJapan.features[0].properties?.population;
  if (isNaN(populationJapan)) {
    const result = await fetchWorldBank("jp");
    populationJapan = result[1][0].value;
  }
  // 日本の人口密度を計算
  const populationDensityJapan = populationJapan / areaJapan;

  return populationDensityMonaco > populationDensityJapan;
};

export default isPopulationDensityOfMonacoHigherThanJapan;
