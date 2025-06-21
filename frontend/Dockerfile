# 多阶段构建 - 构建阶段
FROM node:18-alpine as builder

WORKDIR /app

# 复制package文件
COPY package*.json ./

# 安装依赖
RUN npm ci

# 复制源代码
COPY . .

# 构建应用
RUN npm run build

# 运行阶段
FROM node:18-alpine

WORKDIR /app

# 安装 dumb-init 用于正确处理信号
RUN apk add --no-cache dumb-init

# 创建非root用户
RUN addgroup -g 1001 -S nodejs
RUN adduser -S nextjs -u 1001

# 复制构建产物
COPY --from=builder /app/public ./public
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static

# 设置正确的权限
RUN chown -R nextjs:nodejs /app
USER nextjs

# 健康检查
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:3000 || exit 1

# 暴露端口
EXPOSE 3000

# 启动命令
ENTRYPOINT ["dumb-init", "--"]
CMD ["node", "server.js"]