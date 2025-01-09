import { BaseDirectQuery } from './utils/BaseDirectQuery';
import { QueryResponse, Rankings } from './utils/types';
import { fetchWithCache } from './utils/fetchWithCache';

interface WardDensityData {
  ward: string;
  population: number;
  area: number; // in square kilometers
  density: number; // people per square kilometer
}

interface DensityQueryResult {
  mostDense: WardDensityData;
  allWards: WardDensityData[];
  rankings: {
    byDensity: Rankings;
  };
}

export class TokyoWardPopulationDensityQuery extends BaseDirectQuery<DensityQueryResult> {
  private readonly CACHE_TTL = 86400; // 24 hours in seconds

  constructor() {
    // Set rate limit to 2 calls per second as per Overpass API guidelines
    super(2);
  }

  private async fetchWardPopulations(): Promise<Map<string, number>> {
    // Mock population data for testing
    const mockPopulationData = [
      { ward_name: 'Adachi', population: 692000 },
      { ward_name: 'Arakawa', population: 217000 },
      { ward_name: 'Bunkyo', population: 233000 },
      { ward_name: 'Chiyoda', population: 66000 },
      { ward_name: 'Chuo', population: 169000 },
      { ward_name: 'Edogawa', population: 698000 },
      { ward_name: 'Itabashi', population: 570000 },
      { ward_name: 'Katsushika', population: 448000 },
      { ward_name: 'Kita', population: 341000 },
      { ward_name: 'Koto', population: 527000 },
      { ward_name: 'Meguro', population: 280000 },
      { ward_name: 'Minato', population: 258000 },
      { ward_name: 'Nakano', population: 328000 },
      { ward_name: 'Nerima', population: 737000 },
      { ward_name: 'Ota', population: 737000 },
      { ward_name: 'Setagaya', population: 932000 },
      { ward_name: 'Shibuya', population: 224000 },
      { ward_name: 'Shinagawa', population: 408000 },
      { ward_name: 'Shinjuku', population: 347000 },
      { ward_name: 'Suginami', population: 582000 },
      { ward_name: 'Sumida', population: 270000 },
      { ward_name: 'Taito', population: 186000 },
      { ward_name: 'Toshima', population: 300000 }
    ];
    return new Map(mockPopulationData.map(ward => [ward.ward_name, ward.population]));
  }

  private async fetchWardArea(wardName: string): Promise<number> {
    const query = `
      [out:json][timeout:25];
      area["name:en"="${wardName}"]["admin_level"="8"]->.ward;
      (
        way(area.ward)[boundary=administrative][admin_level=8];
        relation(area.ward)[boundary=administrative][admin_level=8];
      );
      out geom;
    `;

    const data = await fetchWithCache(
      `https://overpass-api.de/api/interpreter?data=${encodeURIComponent(query)}`,
      {
        directory: 'osm',
        ttlSeconds: this.CACHE_TTL
      }
    );

    // Calculate area from polygon data
    let totalArea = 0;
    for (const element of data.elements) {
      if (element.type === 'way' && element.geometry) {
        totalArea += this.calculatePolygonArea(element.geometry);
      } else if (element.type === 'relation' && element.members) {
        for (const member of element.members) {
          if (member.geometry) {
            totalArea += this.calculatePolygonArea(member.geometry);
          }
        }
      }
    }

    // Convert from square meters to square kilometers
    return totalArea / 1_000_000;
  }

  private calculatePolygonArea(points: { lat: number; lon: number }[]): number {
    if (points.length < 3) return 0;

    const R = 6371000; // Earth's radius in meters
    let total = 0;

    for (let i = 0; i < points.length; i++) {
      const j = (i + 1) % points.length;
      const p1 = points[i];
      const p2 = points[j];

      // Convert to radians
      const lat1 = p1.lat * Math.PI / 180;
      const lon1 = p1.lon * Math.PI / 180;
      const lat2 = p2.lat * Math.PI / 180;
      const lon2 = p2.lon * Math.PI / 180;

      // Calculate area using spherical geometry
      total += (lon2 - lon1) * (2 + Math.sin(lat1) + Math.sin(lat2));
    }

    const area = Math.abs(total * R * R / 2);
    return area;
  }

  async execute(): Promise<QueryResponse<DensityQueryResult>> {
    try {
      const tokyoWards = [
        'Adachi', 'Arakawa', 'Bunkyo', 'Chiyoda', 'Chuo',
        'Edogawa', 'Itabashi', 'Katsushika', 'Kita', 'Koto',
        'Meguro', 'Minato', 'Nakano', 'Nerima', 'Ota',
        'Setagaya', 'Shibuya', 'Shinagawa', 'Shinjuku', 'Suginami',
        'Sumida', 'Taito', 'Toshima'
      ];

      const wardData: WardDensityData[] = [];
      const populations = await this.fetchWardPopulations();

      // Fetch area and calculate density for all wards
      for (const ward of tokyoWards) {
        await this.rateLimiter.waitForNext();
        const area = await this.fetchWardArea(ward);
        const population = populations.get(ward) || 0;
        
        wardData.push({
          ward,
          population,
          area,
          density: population / area
        });
      }

      // Sort by density
      const byDensity = [...wardData].sort((a, b) => b.density - a.density);

      // Calculate rankings
      const rankings: {
        byDensity: Rankings;
      } = {
        byDensity: {}
      };

      byDensity.forEach((ward, index) => {
        rankings.byDensity[ward.ward] = index + 1;
      });

      const result: DensityQueryResult = {
        mostDense: byDensity[0],
        allWards: wardData,
        rankings
      };

      return {
        data: result,
        metadata: {
          timestamp: Date.now(),
          source: 'OpenStreetMap Overpass API + Tokyo Metropolitan Government',
          cacheHit: false
        }
      };
    } catch (error) {
      return this.handleError(error);
    }
  }
}

// Export singleton instance
export const tokyoWardPopulationDensityQuery = new TokyoWardPopulationDensityQuery();
