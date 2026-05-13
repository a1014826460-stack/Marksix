import { dirname } from 'path'
import { fileURLToPath } from 'url'
const __dirname = dirname(fileURLToPath(import.meta.url))

/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',
  turbopack: {
    root: __dirname,
  },
  typescript: {
    ignoreBuildErrors: true,
  },
  images: {
    unoptimized: true,
  },
  async rewrites() {
    return {
      beforeFiles: [
        {
          source: '/',
          has: [
            {
              type: 'query',
              key: 't',
              value: '(?<legacyType>1|2|3)',
            },
          ],
          destination: '/vendor/shengshi8800/embed.html?type=:legacyType&web=4',
        },
        {
          source: '/',
          destination: '/vendor/shengshi8800/embed.html?type=3&web=4',
        },
      ],
    }
  },
  async headers() {
    return [
      {
        source: '/vendor/shengshi8800/static/:path*',
        headers: [
          { key: 'Cache-Control', value: 'public, max-age=31536000, immutable' },
        ],
      },
    ]
  },
}

export default nextConfig
