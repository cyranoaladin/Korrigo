# Stage 1: Build the Frontend
FROM node:20-alpine as builder
WORKDIR /app
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ .
RUN npm run build

# Stage 2: Serve with Nginx
FROM nginx:1.25-alpine

RUN rm /etc/nginx/conf.d/default.conf
COPY infra/nginx/nginx.conf /etc/nginx/conf.d/

# Copy built assets from builder stage
COPY --from=builder /app/dist /usr/share/nginx/html

# Directory for backend static files (collected via volume)
RUN mkdir -p /app/staticfiles /app/media

ARG OCI_REVISION=unknown
ARG OCI_SOURCE=unknown
ARG OCI_VERSION=dev
ARG OCI_CREATED=unknown

LABEL org.opencontainers.image.revision="${OCI_REVISION}" \
      org.opencontainers.image.source="${OCI_SOURCE}" \
      org.opencontainers.image.version="${OCI_VERSION}" \
      org.opencontainers.image.created="${OCI_CREATED}"
