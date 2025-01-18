# Use the official Certbot Docker image
FROM certbot/dns-cloudflare

ENV WORKDIR=/home

WORKDIR $WORKDIR

# install package
RUN pip install cloudflare

# Declare build-time variables (ARG)
ARG EMAIL_CERTIFICATOR
ARG CLOUDFLARE_API_KEY

# Set environment variables for runtime (optional)
ENV EMAIL_CERTIFICATOR=${EMAIL_CERTIFICATOR}
ENV CLOUDFLARE_API_KEY=${CLOUDFLARE_API_KEY}

# Copy the entrypoint script into the container
COPY ./docker-entrypoint.sh $WORKDIR

# Ensure the script is executable
RUN chmod +x $WORKDIR/docker-entrypoint.sh

# Use the correct path in ENTRYPOINT
ENTRYPOINT ["./docker-entrypoint.sh"]
