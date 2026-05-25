FROM node:22-alpine AS build

WORKDIR /app

COPY package.json ./
RUN npm install

COPY . .

# Default to empty: the SPA falls back to relative URLs (/api/...) which
# nginx in the runtime stage proxies to the prodx-api service. No need to
# bake the API URL per environment; same image works in compose + k8s.
ARG VITE_API_BASE_URL=""
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL

RUN npm run build

FROM nginx:1.31.1-alpine

# Pick up the latest alpine package patches at build time. nginx:1.27-alpine
# tracks the alpine 3.21 release, which gets security backports faster than
# the nginx maintainers rebuild the image — without this `apk upgrade`,
# Trivy finds CRITICAL openssl/libxml2 CVEs that already have fixed alpine
# packages available.
RUN apk upgrade --no-cache && rm -rf /var/cache/apk/*

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80
