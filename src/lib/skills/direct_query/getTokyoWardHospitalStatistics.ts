import { BaseDirectQuery } from './utils/BaseDirectQuery';
import { QueryResponse } from './utils/types';
import { fetchWithCache } from './utils/fetchWithCache';

interface HospitalData {
  ward: string;
  totalHospitals: number;
  hospitalsPerPopulation: number;
  population: number;
}

interface HospitalQueryResult {
  mostHospitals: HospitalData;
  mostHospitalsPerCapita: HospitalData;
  allWards: HospitalData[];
  rankings: {
    byTotal: { [key: string]: number };
    byPerCapita: { [key: string]: number };
  };
}

export class TokyoWardHospitalStatisticsQuery extends BaseDirectQuery<HospitalQueryResult> {
  private readonly CACHE_PATH = './tmp/cache/osm/tokyo_ward_hospitals.json';
  private readonly CACHE_TTL = 43200; // 12 hours in seconds

  constructor() {
    // Set rate limit to 2 calls per second as per Overpass API guidelines
    super(2);
  }

  private async fetchWardPopulations(): Promise<Map<string, number>> {
    const populationData = await fetchWithCache(
      'https://api.data.metro.tokyo.lg.jp/v1/WardPopulation',
      {
        directory: 'tokyo',
        ttlSeconds: this.CACHE_TTL
      }
    );

    const populations = new Map<string, number>();
    for (const ward of populationData) {
      populations.set(ward.ward_name, ward.population);
    }
    return populations;
  }

  private async fetchHospitalsInWard(wardName: string): Promise<number> {
    const query = `
      [out:json][timeout:25];
      area["name:en"="${wardName}"]["admin_level"="8"]->.ward;
      (
        node["amenity"="hospital"](area.ward);
        way["amenity"="hospital"](area.ward);
        relation["amenity"="hospital"](area.ward);
      );
      out count;
    `;

    const data = await fetchWithCache(
      `https://overpass-api.de/api/interpreter?data=${encodeURIComponent(query)}`,
      {
        directory: 'osm',
        ttlSeconds: this.CACHE_TTL
      }
    );

    return data.elements[0].count || 0;
  }

  async execute(): Promise<QueryResponse<HospitalQueryResult>> {
    try {
      const tokyoWards = [
        'Adachi', 'Arakawa', 'Bunkyo', 'Chiyoda', 'Chuo',
        'Edogawa', 'Itabashi', 'Katsushika', 'Kita', 'Koto',
        'Meguro', 'Minato', 'Nakano', 'Nerima', 'Ota',
        'Setagaya', 'Shibuya', 'Shinagawa', 'Shinjuku', 'Suginami',
        'Sumida', 'Taito', 'Toshima'
      ];

      const wardData: HospitalData[] = [];
      const populations = await this.fetchWardPopulations();

      // Fetch hospital data for all wards
      for (const ward of tokyoWards) {
        await this.rateLimiter.waitForNext();
        const hospitals = await this.fetchHospitalsInWard(ward);
        const population = populations.get(ward) || 0;
        
        wardData.push({
          ward,
          totalHospitals: hospitals,
          population,
          hospitalsPerPopulation: population > 0 ? (hospitals / population) * 100000 : 0
        });
      }

      // Sort by total hospitals and hospitals per capita
      const byTotal = [...wardData].sort((a, b) => b.totalHospitals - a.totalHospitals);
      const byPerCapita = [...wardData].sort((a, b) => b.hospitalsPerPopulation - a.hospitalsPerPopulation);

      // Calculate rankings
      const rankings = {
        byTotal: {},
        byPerCapita: {}
      };

      byTotal.forEach((ward, index) => {
        rankings.byTotal[ward.ward] = index + 1;
      });

      byPerCapita.forEach((ward, index) => {
        rankings.byPerCapita[ward.ward] = index + 1;
      });

      const result: HospitalQueryResult = {
        mostHospitals: byTotal[0],
        mostHospitalsPerCapita: byPerCapita[0],
        allWards: wardData,
        rankings
      };

      return {
        data: result,
        metadata: {
          timestamp: Date.now(),
          source: 'OpenStreetMap Overpass API',
          cacheHit: false
        }
      };
    } catch (error) {
      return this.handleError(error);
    }
  }
}

// Export singleton instance
export const tokyoWardHospitalStatisticsQuery = new TokyoWardHospitalStatisticsQuery();
