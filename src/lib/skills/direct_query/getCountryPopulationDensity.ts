import { BaseDirectQuery } from './utils/BaseDirectQuery';
import { QueryResponse } from './utils/types';
import { fetchWithCache } from './utils/fetchWithCache';
import getAllCountriesAlpha2Codes from '../getAllCountriesAlpha2Codes';
import fs from 'fs';

interface CountryDensityData {
  country: string;
  density: number;
  year: number;
  iso2Code: string;
}

interface DensityQueryResult {
  mostDense: CountryDensityData;
  allDensities: CountryDensityData[];
  rankings: { [key: string]: number }; // Position in density ranking
}

export class CountryPopulationDensityQuery extends BaseDirectQuery<DensityQueryResult> {
  private readonly CACHE_PATH = './tmp/cache/world_bank/population_density.json';
  private readonly CACHE_TTL = 86400; // 24 hours in seconds

  constructor() {
    // Set rate limit to 30 calls per second as per World Bank API guidelines
    super(30);
  }

  private async checkCache(): Promise<DensityQueryResult | null> {
    try {
      const stats = await fs.promises.stat(this.CACHE_PATH);
      const age = (Date.now() - stats.mtimeMs) / 1000;
      
      if (age < this.CACHE_TTL) {
        const cached = await fs.promises.readFile(this.CACHE_PATH, 'utf-8');
        return JSON.parse(cached);
      }
    } catch (e) {
      console.debug('Cache not found or expired. Fetching fresh data...');
    }
    return null;
  }

  private async saveToCache(data: DensityQueryResult): Promise<void> {
    await fs.promises.mkdir('./tmp/cache/world_bank', { recursive: true });
    await fs.promises.writeFile(
      this.CACHE_PATH,
      JSON.stringify(data, null, 2),
      'utf-8'
    );
  }

  async execute(): Promise<QueryResponse<DensityQueryResult>> {
    try {
      // Check cache first
      const cached = await this.checkCache();
      if (cached) {
        return {
          data: cached,
          metadata: {
            timestamp: Date.now(),
            source: 'World Bank API (cached)',
            cacheHit: true
          }
        };
      }

      const countries = await getAllCountriesAlpha2Codes();
      const densityMap = new Map<string, CountryDensityData>();

      // Fetch all country data in parallel with rate limiting
      const codes = countries.split('\n');
      const batchSize = 10; // Process 10 countries at a time
      
      for (let i = 0; i < codes.length; i += batchSize) {
        const batch = codes.slice(i, i + batchSize);
        const promises = batch.map(async (code) => {
          await this.rateLimiter.waitForNext();
          try {
            const data = await fetchWithCache(
              `https://api.worldbank.org/v2/country/${code}/indicator/EN.POP.DNST?format=json`,
              {
                directory: 'world_bank',
                ttlSeconds: this.CACHE_TTL
              }
            );

            if (data[1] && data[1][0]) {
              return {
                code,
                data: {
                  country: data[1][0].country.value,
                  density: data[1][0].value,
                  year: parseInt(data[1][0].date),
                  iso2Code: code
                }
              };
            }
          } catch (error) {
            console.error(`Error fetching density for ${code}:`, error);
          }
          return null;
        });

        const results = await Promise.all(promises);
        results.forEach(result => {
          if (result) {
            densityMap.set(result.code, result.data);
          }
        });
      }

      const allDensities = Array.from(densityMap.values())
        .sort((a, b) => b.density - a.density);

      // Calculate rankings
      const rankings: { [key: string]: number } = {};
      allDensities.forEach((country, index) => {
        rankings[country.iso2Code] = index + 1;
      });

      const result: DensityQueryResult = {
        mostDense: allDensities[0],
        allDensities,
        rankings
      };

      // Save to cache
      await this.saveToCache(result);

      return {
        data: result,
        metadata: {
          timestamp: Date.now(),
          source: 'World Bank API',
          cacheHit: false
        }
      };
    } catch (error) {
      return this.handleError(error);
    }
  }
}

// Export singleton instance
export const countryPopulationDensityQuery = new CountryPopulationDensityQuery();
