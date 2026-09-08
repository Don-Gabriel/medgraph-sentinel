# Console image (compose pins it as medgraph-frontend:demo).
# Stage 1: build the static bundle; API base URL is baked at build time.
FROM node:20-alpine AS build
ARG VITE_API_BASE_URL=http://localhost:8000
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
WORKDIR /app
# Lockfile is committed, so build from it: `npm ci` installs the exact
# resolved tree CI verified, instead of re-resolving semver ranges at image
# build time (the image and the green check could otherwise disagree).
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY . .
RUN npm run build

# Stage 2: serve static files.
FROM nginx:1.27-alpine
# Raises large_client_header_buffers — see the file for the demo-day
# failure it prevents. Replaces the stock default.conf.
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
