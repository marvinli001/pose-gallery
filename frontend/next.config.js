/** @type {import('next').NextConfig} */
const nextConfig = {
  // 移除过时的 experimental.appDir 配置
  images: {
    domains: ['localhost'],
    remotePatterns: [
      {
        protocol: 'http',
        hostname: 'localhost',
        port: '8000',
      },
    ],
  },
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: 'http://localhost:8000/api/:path*',
      },
    ];
  },
}

module.exports = nextConfig