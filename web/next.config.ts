import type { NextConfig } from "next"

const nextConfig: NextConfig = {
  // Allow large static JSON files in /public
  experimental: {
    largePageDataBytes: 512 * 1000,
  },
  webpack: (config) => {
    config.resolve = config.resolve ?? {}
    config.resolve.alias = {
      ...(config.resolve.alias ?? {}),
      "mapbox-gl": "maplibre-gl",
    }
    return config
  },
  // Turbopack alias for deck.gl mapbox → maplibre swap
  turbopack: {
    resolveAlias: {
      "mapbox-gl": "maplibre-gl",
    },
  },
}

export default nextConfig
