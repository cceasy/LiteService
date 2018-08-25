FROM ls/okapi-py3

# Install required dependencies (includes Flask and uWSGI)
USER root
COPY requirements.txt /tmp/
RUN pip3 install -r /tmp/requirements.txt -i http://pypi.douban.com/simple/ --trusted-host pypi.douban.com

# Create a place to deploy the application
ENV APP_DIR /var/www/app
RUN mkdir -p $APP_DIR
WORKDIR $APP_DIR

RUN mkdir -p /var/log/uwsgi
USER okapi

# When building a downstream image, copy the application files and then setup
# additional dependencies. It's assumed the application files are present in
# the same directory as the downstream build's Dockerfile.
ONBUILD COPY . $APP_DIR/
ONBUILD RUN pip3 install -r $APP_DIR/requirements.txt -i http://pypi.douban.com/simple/ --trusted-host pypi.douban.com
