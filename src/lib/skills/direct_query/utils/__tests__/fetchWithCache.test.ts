import { fetchWithCache } from '../fetchWithCache';
import * as fs from 'fs';

jest.mock('fs');
jest.mock('node-fetch');

describe('fetchWithCache', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('should fetch and cache new data when cache is missing', async () => {
    const mockData = { test: 'data' };
    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockData)
    });

    const result = await fetchWithCache('http://test.com', { directory: 'test' });
    expect(result).toEqual(mockData);
    expect(fs.promises.writeFile).toHaveBeenCalled();
  });
});
