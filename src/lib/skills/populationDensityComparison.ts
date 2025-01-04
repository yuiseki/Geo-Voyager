// description: ラオスの人口密度がシンガポールよりも低いことを確認する。
// file_path: src/lib/skills/populationDensityComparison.ts

import fetch from 'node-fetch';

async function isLaosPopulationDensityLowerThanSingapore(): Promise<boolean> {
  try {
    // Fetch data for Laos
    const laosResponse = await fetch('https://restcountries.com/v3.1/name/laos');
    const laosData = await laosResponse.json();
    const laosPopulation = laosData[0].population;
    const laosArea = laosData[0].area;
    const laosDensity = laosPopulation / laosArea;

    // Fetch data for Singapore
    const singaporeResponse = await fetch('https://restcountries.com/v3.1/name/singapore');
    const singaporeData = await singaporeResponse.json();
    const singaporePopulation = singaporeData[0].population;
    const singaporeArea = singaporeData[0].area;
    const singaporeDensity = singaporePopulation / singaporeArea;

    // Compare the population densities
    return laosDensity < singaporeDensity;
  } catch (error) {
    console.error('Error fetching data:', error);
    throw error;
  }
}

export default isLaosPopulationDensityLowerThanSingapore;