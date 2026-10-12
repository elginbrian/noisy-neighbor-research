FROM nginx:1.27-alpine

# Hapus konfigurasi default bawaan Nginx
RUN rm -f /etc/nginx/conf.d/default.conf

# Pasang konfigurasi yang mematikan access log
COPY default.conf /etc/nginx/conf.d/default.conf
COPY index.html /usr/share/nginx/html/index.html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
