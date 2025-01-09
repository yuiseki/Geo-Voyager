/**
 * Simple rate limiter for API calls
 */
export class RateLimiter {
  private lastCall: number = 0;
  private delayMs: number;

  constructor(callsPerSecond: number) {
    this.delayMs = 1000 / callsPerSecond;
  }

  async waitForNext(): Promise<void> {
    const now = Date.now();
    const timeSinceLastCall = now - this.lastCall;
    
    if (timeSinceLastCall < this.delayMs) {
      const waitTime = this.delayMs - timeSinceLastCall;
      await new Promise(resolve => setTimeout(resolve, waitTime));
    }
    
    this.lastCall = Date.now();
  }
}
