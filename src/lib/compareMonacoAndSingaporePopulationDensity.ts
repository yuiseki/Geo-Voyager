import { compareKeyValue } from "./compareKeyValue";
import { getMonacoPopulationDensity } from "./getMonacoPopulationDensity";
import { getSingaporePopulationDensity } from "./getSingaporePopulationDensity";

export const compareMonacoAndSingaporePopulationDensity = async () => {
  const monacoPopDen = await getMonacoPopulationDensity();
  const singaporePopDen = await getSingaporePopulationDensity();
  const entry1 = { key: "Monaco", value: monacoPopDen };
  const entry2 = { key: "Singapore", value: singaporePopDen };
  const result = compareKeyValue(entry1, entry2);
  return result.key;
};
