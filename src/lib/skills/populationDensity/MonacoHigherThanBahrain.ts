// description: モナコの人口密度がバーレーンよりも高いことを確認する。
// file_path: src/lib/skills/populationDensity/MonacoHigherThanBahrain.ts
import * as turf from "@turf/turf";
import osmtogeojson from "osmtogeojson";

/**
 * @returns boolean
 */
const isPopulationDensityOfMonacoHigherThanBahrain = async () => {
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

  // バーレーンの面積を取得
  const queryBahrain = `[out:json];
relation["name:en"="Bahrain"]["admin_level"=2];
out geom;`;
  const resultBahrain = await fetchOverpassData(queryBahrain);
  const geoJsonBahrain = osmtogeojson(resultBahrain);
  const areaBahrain = turf.area(geoJsonBahrain);
  // バーレーンの人口を取得
  let populationBahrain = geoJsonBahrain.features[0].properties?.population;
  if (isNaN(populationBahrain)) {
    const result = await fetchWorldBank("bh");
    populationBahrain = result[1][0].value;
  }
  // バーレーンの人口密度を計算
  const populationDensityBahrain = populationBahrain / areaBahrain;

  return populationDensityMonaco > populationDensityBahrain;
};

export default isPopulationDensityOfMonacoHigherThanBahrain;
