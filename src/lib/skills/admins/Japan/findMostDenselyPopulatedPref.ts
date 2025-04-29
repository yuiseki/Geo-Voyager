// description: 日本で人口密度が最も高い都道府県を探す。
// file_path: src/lib/skills/admins/Japan/findMostDenselyPopulatedPref.ts

import { getEStatLatestPopulationOfPrefs } from "../../../common/getEStatLatestPopulationOfPrefs";
import { getPopulationDensityByPrefOnlyLandMask } from "../../../common/getPopulationDensityByPrefOnlyLandMask";

const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

/**
 * Get the name of the most densely populated pref in Japan.
 * @returns The name of the most densely populated pref in Japan.
 */
const findMostDenselyPopulatedPref = async (): Promise<string> => {
  const prefs = await getEStatLatestPopulationOfPrefs();
  let maxPopulationDensity = 0;
  let prefWithMaxPopulationDensity = "";
  for (const prefName of Object.keys(prefs)) {
    await sleep(5000);
    const latestPopulation = prefs[prefName];
    const populationDensity = await getPopulationDensityByPrefOnlyLandMask(
      prefName,
      latestPopulation
    );
    console.info(
      `${prefName}: ${latestPopulation} people, ${populationDensity} people/km²`
    );
    if (populationDensity > maxPopulationDensity) {
      maxPopulationDensity = populationDensity;
      prefWithMaxPopulationDensity = prefName;
    }
  }
  return prefWithMaxPopulationDensity;
};

export default findMostDenselyPopulatedPref;
