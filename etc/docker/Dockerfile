FROM nginx:latest
COPY etc/nginx/conf.d/ /etc/nginx/conf.d/
COPY src/ /usr/share/nginx/html/
CMD ["nginx", "-g", "daemon off;"]
