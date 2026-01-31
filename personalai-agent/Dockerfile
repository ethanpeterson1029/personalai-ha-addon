ARG BUILD_FROM
FROM $BUILD_FROM

# Install Python dependencies
RUN apk add --no-cache python3 py3-pip
RUN pip3 install --no-cache-dir aiohttp

# Copy agent
COPY run.sh /
COPY agent.py /

RUN chmod a+x /run.sh

CMD [ "/run.sh" ]
