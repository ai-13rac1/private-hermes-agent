FROM alpine:3.24
RUN apk add --no-cache python3
COPY components/webapp/publisher.py /opt/publisher.py
USER 10004:10004
ENV PYTHONDONTWRITEBYTECODE=1
ENTRYPOINT ["python3", "/opt/publisher.py"]
