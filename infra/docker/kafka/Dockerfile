FROM docker.io/apache/kafka:4.2.2@sha256:1213eb3943d551e5ed1fca7a4e109001cee35770b66a02a0c37a8964efe09b69

USER root
RUN apk upgrade --no-cache libexpat \
 && wget -q https://repo1.maven.org/maven2/com/fasterxml/jackson/core/jackson-core/2.21.7/jackson-core-2.21.7.jar -O /tmp/jackson-core.jar \
 && wget -q https://repo1.maven.org/maven2/com/fasterxml/jackson/core/jackson-databind/2.21.7/jackson-databind-2.21.7.jar -O /tmp/jackson-databind.jar \
 && wget -q https://repo.maven.apache.org/maven2/at/yawk/lz4/lz4-java/1.11.4/lz4-java-1.11.4.jar -O /tmp/lz4-java.jar \
 && echo '8c5623b98f32d5f7e1287ff61ed50e08ab7b11381e991fff89327faabba42261  /tmp/jackson-core.jar' | sha256sum -c - \
 && echo '1290c2795e93e8a6861a6c4d9ff0d844d32f5ea178362cb2721edf5561e828b1  /tmp/jackson-databind.jar' | sha256sum -c - \
 && echo '58c8e0b813960d2a248e050c353baea73139b48a2ffc55382d42c69707e17325  /tmp/lz4-java.jar' | sha256sum -c - \
 && find /opt/kafka/libs -name 'jackson-core-*.jar' -delete \
 && find /opt/kafka/libs -name 'jackson-databind-*.jar' -delete \
 && find /opt/kafka/libs -name 'lz4-java-*.jar' -delete \
 && install -o appuser -g appuser -m 0444 /tmp/jackson-core.jar /opt/kafka/libs/jackson-core-2.21.7.jar \
 && install -o appuser -g appuser -m 0444 /tmp/jackson-databind.jar /opt/kafka/libs/jackson-databind-2.21.7.jar \
 && install -o appuser -g appuser -m 0444 /tmp/lz4-java.jar /opt/kafka/libs/lz4-java-1.11.4.jar \
 && rm -f /tmp/jackson-*.jar /tmp/lz4-java.jar
RUN mkdir -p /tmp/kraft-combined-logs && chown appuser:appuser /tmp/kraft-combined-logs
USER appuser
