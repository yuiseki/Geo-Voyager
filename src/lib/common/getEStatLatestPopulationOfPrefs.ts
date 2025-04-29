import fs from "fs";

export type AreaPopulation = {
  [prefName: string]: number;
};

/**
 * Fetches the population of each pref in Japan using e-Stat API.
 * @returns The population of each pref in Japan.
 */
export async function getEStatLatestPopulationOfPrefs(): Promise<AreaPopulation> {
  if (!process.env.E_STAT_APP_ID) {
    throw new Error("process.env.E_STAT_APP_ID is not set!");
  }
  // read cache file if exists
  const cachePath = "./tmp/cache/latestPopulationOfPrefsInJapan.json";
  try {
    const cache = await fs.readFileSync(cachePath, "utf-8");
    return JSON.parse(cache);
  } catch (e) {
    console.debug("Cache not found. Call e-Stat API...");
  }
  const endpoint = "https://api.e-stat.go.jp/rest/3.0/app/json/getStatsData";
  const searchParams = new URLSearchParams();
  searchParams.append("appId", process.env.E_STAT_APP_ID);
  searchParams.append("lang", "J");
  searchParams.append("statsDataId", "0000010101");
  searchParams.append("metaGetFlg", "Y");
  searchParams.append("cntGetFlg", "N");
  searchParams.append("explanationGetFlg", "Y");
  searchParams.append("annotationGetFlg", "Y");
  searchParams.append("sectionHeaderFlg", "1");
  searchParams.append("replaceSpChars", "0");

  // fetch data from e-Stat API
  const res = await fetch(`${endpoint}?${searchParams.toString()}`);
  const json = await res.json();
  const keys: {
    "@code": string; // 00000
    "@name": string; // 全国
    "@level": string; // 1
  }[] = json.GET_STATS_DATA.STATISTICAL_DATA.CLASS_INF.CLASS_OBJ[2].CLASS;
  const values: {
    "@tab": string; // 00001
    "@cat01": string; // A1101
    "@area": string; // 00000
    "@time": string; // 1975100000
    "@unit": string; // 人
    $: string; // 111939643
  }[] = json.GET_STATS_DATA.STATISTICAL_DATA.DATA_INF.VALUE;
  // aggregate latest population value by pref name
  const data: AreaPopulation = {};
  for (const pref of keys) {
    const prefName = pref["@name"];
    if (prefName === "全国") {
      continue;
    }
    const prefCode = pref["@code"];
    // filter by pref code
    const populationValues = values.filter(
      (value) => value["@area"] === prefCode
    );
    const populationValuesParsed = populationValues.map((value) => ({
      population: parseInt(value["$"]),
      time: parseInt(value["@time"]),
    }));
    // get the latest population value
    const latestPopulation = populationValuesParsed.sort(
      (a, b) => b.time - a.time
    )[0].population;
    data[prefName] = latestPopulation;
  }
  // cache the data
  await fs.mkdirSync("./tmp/cache", { recursive: true });
  await fs.writeFileSync(cachePath, JSON.stringify(data, null, 2), "utf-8");
  return data;
}
