FROM node:18-alpine
WORKDIR /app
RUN npm install -g serve
COPY static /app/static
EXPOSE 3001
CMD ["serve", "-s", "static", "-l", "3001"]
