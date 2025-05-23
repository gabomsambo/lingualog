FROM node:18-alpine

WORKDIR /app

COPY v0_lingua-log/package*.json ./

RUN npm install --legacy-peer-deps

COPY v0_lingua-log/ .

RUN npm run build

EXPOSE 3000

CMD ["npm", "run", "start"] 