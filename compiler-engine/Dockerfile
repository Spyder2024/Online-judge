FROM node:18-alpine

# Install GCC, G++, Java 17, and Python 3 in the image at build time
RUN apk add --no-cache gcc g++ openjdk17 python3

# Create unprivileged runner user and group
RUN addgroup -S sandbox && adduser -S sandbox -G sandbox

WORKDIR /app

COPY package.json ./
RUN npm install

COPY index.js ./

# Set directory permissions for sandbox user
RUN mkdir -p /app/temp && chown -R sandbox:sandbox /app

USER sandbox

EXPOSE 8000

CMD ["node", "index.js"]
