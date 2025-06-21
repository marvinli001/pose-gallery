FROM node:20-alpine AS builder
WORKDIR /app
COPY frontend/package*.json ./frontend/
RUN cd frontend && npm install
COPY frontend ./frontend
RUN cd frontend && npm run build

FROM node:20-alpine
WORKDIR /app
COPY --from=builder /app/frontend .
ENV NODE_ENV=production
EXPOSE 3000
CMD ["npm", "start"]