FROM ls/flask3-uwsgi

USER root
RUN ln -s /var/www/app/static /var/www/okapi-front-static
VOLUME /var/www/okapi-front-static

EXPOSE 5000

CMD ["uwsgi", "--ini", "uwsgi.ini"]
USER okapi
