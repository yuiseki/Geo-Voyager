import fs from "fs";
import { fetchOverpassData } from "./fetchOverpassData";

// Mock dependencies
jest.mock("fs", () => ({
  promises: {
    readFile: jest.fn(),
    mkdir: jest.fn().mockResolvedValue(undefined),
    writeFile: jest.fn().mockResolvedValue(undefined),
  },
}));

jest.mock("ts-md5", () => ({
  Md5: jest.fn().mockImplementation(() => ({
    appendStr: jest.fn(),
    end: jest.fn().mockReturnValue("mockedHash"),
  })),
}));

global.fetch = jest.fn();
global.console.log = jest.fn();

describe("fetchOverpassData", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("should return cached data if available", async () => {
    const mockData = { elements: [{ id: 1 }] };
    (fs.promises.readFile as jest.Mock).mockResolvedValue(
      JSON.stringify(mockData)
    );

    const result = await fetchOverpassData("test query");

    expect(fs.promises.readFile).toHaveBeenCalledWith(
      "./tmp/cache/overpass/query_mockedHash.json",
      "utf-8"
    );
    expect(result).toEqual(mockData);
    expect(fetch).not.toHaveBeenCalled();
  });

  it("should fetch data from API if cache is not available", async () => {
    const mockData = { elements: [{ id: 2 }] };
    (fs.promises.readFile as jest.Mock).mockRejectedValue(
      new Error("File not found")
    );
    (global.fetch as jest.Mock).mockResolvedValue({
      ok: true,
      json: jest.fn().mockResolvedValue(mockData),
    });

    const result = await fetchOverpassData("test query");

    expect(fs.promises.readFile).toHaveBeenCalledWith(
      "./tmp/cache/overpass/query_mockedHash.json",
      "utf-8"
    );
    expect(console.log).toHaveBeenCalledWith(
      "Cache not found. Calling Overpass API..."
    );
    expect(fetch).toHaveBeenCalledWith(
      "https://overpass-api.de/api/interpreter",
      {
        method: "POST",
        headers: {
          "Content-Type": "application/x-www-form-urlencoded",
        },
        body: "data=test%20query",
      }
    );
    expect(fs.promises.mkdir).toHaveBeenCalledWith("./tmp/cache/overpass", {
      recursive: true,
    });
    expect(fs.promises.writeFile).toHaveBeenCalledWith(
      "./tmp/cache/overpass/query_mockedHash.json",
      JSON.stringify(mockData, null, 2),
      "utf-8"
    );
    expect(result).toEqual(mockData);
  });

  it("should throw an error if the API response is not ok", async () => {
    (fs.promises.readFile as jest.Mock).mockRejectedValue(
      new Error("File not found")
    );
    (global.fetch as jest.Mock).mockResolvedValue({
      ok: false,
      status: 500,
    });

    await expect(fetchOverpassData("test query")).rejects.toThrow(
      "HTTP error! status: 500"
    );
  });
});
