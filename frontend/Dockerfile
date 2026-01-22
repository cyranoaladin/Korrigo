# Stage 1: Build
FROM node:20-slim AS builder

WORKDIR /app

# Install dependencies causing cache invalidation only when package.json changes
COPY package.json package-lock.json* ./
RUN npm ci

# Copy source and build
COPY . .
# Bake in the API URL for the Nginx gateway routing
ARG VITE_API_URL=/api
ENV VITE_API_URL=${VITE_API_URL}
RUN npm run build

# Stage 2: Serve
FROM nginx:alpine

# Remove default nginx static assets
RUN rm -rf /usr/share/nginx/html/*

# Copy static assets from builder stage
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy custom nginx config for SPA fallback within the container (optional, but good practice)
# We can use a simple config block here or rely on default if we don't need SPA routing (history mode).
# For Vue Router history mode, we need try_files $uri $uri/ /index.html;
RUN echo 'server { \
    listen 80; \
    server_name localhost; \
    location / { \
    root /usr/share/nginx/html; \
    index index.html; \
    try_files $uri $uri/ /index.html; \
    } \
    }' > /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
