/** @type {import('next').NextConfig} */
const nextConfig = {
  images: {
    remotePatterns: [
      {
        protocol: 'https',
        hostname: '**.aliyuncs.com',
      },
      {
        protocol: 'https',
        hostname: 'your-oss-bucket.oss-cn-**.aliyuncs.com',
      },
      // 添加其他需要的图片域名
    ],
  },
}

module.exports = nextConfig
