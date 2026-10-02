FROM docker.io/apache/kafka:4.2.2@sha256:1213eb3943d551e5ed1fca7a4e109001cee35770b66a02a0c37a8964efe09b69

USER root
RUN apk upgrade --no-cache libexpat \
 && wget -q https://repo1.maven.org/maven2/com/fasterxml/jackson/core/jackson-core/2.21.7/jackson-core-2.21.7.jar -O /tmp/jackson-core.jar \
 && wget -q https://repo1.maven.org/maven2/com/fasterxml/jackson/core/jackson-databind/2.21.7/jackson-databind-2.21.7.jar -O /tmp/jackson-databind.jar \
 && echo '8c5623b98f32d5f7e1287ff61ed50e08ab7b11381e991fff89327faabba42261  /tmp/jackson-core.jar' | sha256sum -c - \
 && echo '1290c2795e93e8a6861a6c4d9ff0d844d32f5ea178362cb2721edf5561e828b1  /tmp/jackson-databind.jar' | sha256sum -c - \
 && find /opt/kafka/libs -name 'jackson-core-*.jar' -delete \
 && find /opt/kafka/libs -name 'jackson-databind-*.jar' -delete \
 && install -o appuser -g appuser -m 0444 /tmp/jackson-core.jar /opt/kafka/libs/jackson-core-2.21.7.jar \
 && install -o appuser -g appuser -m 0444 /tmp/jackson-databind.jar /opt/kafka/libs/jackson-databind-2.21.7.jar \
 && rm -f /tmp/jackson-*.jar
USER appuser
