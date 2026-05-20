ARG REQ_IMAGE

FROM $REQ_IMAGE

WORKDIR /ygag

ADD ./ /ygag

# Create a non-root user and hand over ownership so the app never runs as root.
# This also removes the need for C_FORCE_ROOT=1 in Celery workers.
RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser \
    && chown -R appuser:appgroup /ygag

USER appuser

EXPOSE 8000
