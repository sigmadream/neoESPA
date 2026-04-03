FROM node:22-alpine

WORKDIR /app

# Copy dependency files first for layer caching
COPY package.json package-lock.json ./

# Install dependencies
RUN npm ci

# Copy application source code
COPY . .

EXPOSE 3000

# Run Next.js dev server
CMD ["npm", "run", "dev"]
