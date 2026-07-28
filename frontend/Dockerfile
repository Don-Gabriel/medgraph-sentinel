# Console image (compose pins it as medgraph-frontend:demo).
# Stage 1: build the static bundle; API base URL is baked at build time.
FROM node:20-alpine AS build
ARG VITE_API_BASE_URL=http://localhost:8000
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
WORKDIR /app
COPY package.json ./
# package-lock.json doesn't exist until the first npm install; switch this
# to `npm ci` once the lockfile is committed (frontend/README.md).
RUN npm install --no-audit --no-fund
COPY . .
RUN npm run build

# Stage 2: serve static files.
FROM nginx:1.27-alpine
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
