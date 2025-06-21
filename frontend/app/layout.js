import './globals.css'

export const metadata = {
  title: '摄影姿势灵感库',
  description: '发现和分享创意摄影姿势，提升你的摄影技巧',
  keywords: '摄影,姿势,写真,人像,拍照'
}

export default function RootLayout({ children }) {
  return (
    <html lang="zh-CN">
      <head>
        <meta name="viewport" content="width=device-width, initial-scale=1" />
      </head>
      <body>
        {children}
      </body>
    </html>
  )
}