/** @type {import('next').NextConfig} */
const nextConfig = {
  // 启用 standalone 模式用于 Docker
  output: 'standalone',
  
  images: {
    domains: ['localhost'],
    remotePatterns: [
      {
        protocol: 'http',
        hostname: 'localhost',
        port: '8000',
      },
      {
        protocol: 'https',
        hostname: 'your-domain.com',
      },
    ],
  },
  
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: process.env.NEXT_PUBLIC_API_URL 
          ? `${process.env.NEXT_PUBLIC_API_URL}/api/:path*`
          : 'http://localhost:8000/api/:path*',
      },
    ];
  },
}

module.exports = nextConfig