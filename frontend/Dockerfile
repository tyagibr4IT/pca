# Simple Node.js React frontend Dockerfile
FROM node:20-alpine
WORKDIR /app
COPY . .
RUN npm install && npm install --global serve
RUN npm run build
EXPOSE 3000
CMD ["serve", "-s", "dist", "-l", "3000"]
