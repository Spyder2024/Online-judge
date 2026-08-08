FROM node:18-alpine

# Install GCC, G++, Java 17, and Python 3 in the image at build time
RUN apk add --no-cache gcc g++ openjdk17 python3

WORKDIR /app

COPY package.json ./
RUN npm install

COPY index.js ./

EXPOSE 8000

CMD ["node", "index.js"]
