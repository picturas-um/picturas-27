FROM node:22-bookworm
workdir /app

copy . .
run npm install

expose 9001
cmd ["npm", "start"]