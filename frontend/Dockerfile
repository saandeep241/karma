FROM node:22-alpine as build

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci

# Copy source code
COPY . .

# Build the app
# Note: VITE_API_URL should be set as build arg or env var
# For Cloud Run, we'll use /api and proxy via nginx
ARG VITE_API_URL=/api
ENV VITE_API_URL=$VITE_API_URL
RUN npm run build

# Production stage
FROM nginx:alpine

# Copy built assets
COPY --from=build /app/dist /usr/share/nginx/html

# Create nginx config template
# Cloud Run sets PORT environment variable (defaults to 8080)
# We'll use envsubst to replace $PORT at runtime
RUN echo 'server { \
    listen ${PORT} default_server; \
    listen [::]:${PORT} default_server; \
    server_name _; \
    root /usr/share/nginx/html; \
    index index.html; \
    \
    # SPA routing \
    location / { \
        try_files $uri $uri/ /index.html; \
    } \
    \
    # API proxy (for local dev, not used in Cloud Run) \
    location /api { \
        proxy_pass http://localhost:8000; \
        proxy_http_version 1.1; \
        proxy_set_header Upgrade $http_upgrade; \
        proxy_set_header Connection "upgrade"; \
        proxy_set_header Host $host; \
        proxy_set_header X-Real-IP $remote_addr; \
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for; \
        proxy_set_header X-Forwarded-Proto $scheme; \
    } \
}' > /etc/nginx/templates/default.conf.template

# Install gettext for envsubst
RUN apk add --no-cache gettext

EXPOSE 8080

# Use envsubst to replace PORT at runtime
CMD envsubst '\$PORT' < /etc/nginx/templates/default.conf.template > /etc/nginx/conf.d/default.conf && nginx -g 'daemon off;'