FROM python:3.4.3 

# RUN mkdir ~/.pip
# COPY pip.conf ~/.pip/
COPY requirements.txt /tmp/
RUN pip3 install -r /tmp/requirements.txt -i http://pypi.douban.com/simple/ --trusted-host pypi.douban.com
RUN rm -rf /var/lib/apt/lists/*

RUN mkdir -p /usr/lib/okapi/pyokapi
COPY pyokapi /usr/lib/okapi/pyokapi/
ENV PYTHONPATH=/usr/lib/okapi

RUN useradd okapi
WORKDIR /home/okapi
RUN mkdir -p /home/okapi/bin/
RUN chown -R okapi:okapi /home/okapi

USER okapi

