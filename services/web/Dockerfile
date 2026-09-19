FROM node:20-alpine

WORKDIR /app

COPY package*.json ./
RUN npm install

COPY . .

RUN npm run build

# Install serve to run the build output
RUN npm install -g serve
CMD ["serve", "-s", "dist", "-l", "3000"]
