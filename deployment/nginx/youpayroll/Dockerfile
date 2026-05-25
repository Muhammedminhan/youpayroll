ARG BASE_IMAGE

FROM $BASE_IMAGE

ARG ENVIRONMENT

ADD ./${ENVIRONMENT}/templates /ygag/nginx/templates
COPY ./${ENVIRONMENT}/nginx.conf /ygag/nginx/conf/nginx.conf

# Overwrite default one
COPY entrypoint.sh /ygag/nginx/entrypoint.sh
RUN chmod +x /ygag/nginx/entrypoint.sh
CMD ["/ygag/nginx/entrypoint.sh"]
