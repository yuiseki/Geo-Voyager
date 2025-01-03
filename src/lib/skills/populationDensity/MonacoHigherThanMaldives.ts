// description: モナコの人口密度がモルディブよりも高いことを確認する。
// file_path: src/lib/skills/populationDensity/MonacoHigherThanMaldives.ts
import * as turf from "@turf/turf";
import osmtogeojson from "osmtogeojson";

/**
 * @return boolean
 */
const isPopulationDensityOfMonacoHigherThanMaldives = async () => {
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

  // モナコの面積を取得
  const queryMonaco = `[out:json];
relation["name"="Monaco"]["admin_level"=2];
out geom;`;
  const resultMonaco = await fetchOverpassData(queryMonaco);
  if (resultMonaco.elements.length === 0) {
    throw new Error(
      `Overpass API returned no data without errors. Please try to fix this query:\n${queryMonaco}`
    );
  }
  const geoJsonMonaco = osmtogeojson(resultMonaco);
  if (geoJsonMonaco.features.length === 0) {
    throw new Error(
      `osmtogeojson returned no GeoJSON data. Please try to fix this query:\n${queryMonaco}`
    );
  }
  const areaMonaco = turf.area(geoJsonMonaco);
  // モナコの人口を取得
  const resultMonacoPopulation = await fetchWorldBankTotalPopulation("mc");
  const populationMonaco = resultMonacoPopulation[1][0].value;
  // モナコの人口密度を計算
  const populationDensityMonaco = populationMonaco / areaMonaco;

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

  return populationDensityMonaco > populationDensityMaldives;
};

export default isPopulationDensityOfMonacoHigherThanMaldives;
