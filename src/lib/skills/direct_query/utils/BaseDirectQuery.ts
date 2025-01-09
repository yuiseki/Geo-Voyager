import { QueryResponse } from './types';
import { RateLimiter } from './rateLimiter';

export abstract class BaseDirectQuery<T> {
  protected rateLimiter: RateLimiter;

  constructor(callsPerSecond: number = 1) {
    this.rateLimiter = new RateLimiter(callsPerSecond);
  }

  abstract execute(): Promise<QueryResponse<T>>;

  protected async handleError(error: unknown): Promise<QueryResponse<T>> {
    const errorResult = {
      error: error instanceof Error ? error.message : 'Unknown error occurred',
      details: error,
      timestamp: Date.now()
    };
    console.error('Query error:', errorResult);
    return errorResult;
  }
}
