# Use an official Node.js image as the base image
FROM node:18-alpine

# Set the working directory inside the container
WORKDIR /app

# Copy package.json and package-lock.json into the container
COPY package.json package-lock.json ./


# Install dependencies
RUN npm install

RUN npm install chartjs-adapter-date-fns
# Copy the rest of the application into the container
COPY . .

# Expose port 3000 to be accessible outside the container
EXPOSE 3000

# Start the React development server
CMD ["npm", "start"]
