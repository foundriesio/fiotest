# Build Python Deps------------------------------------------------------------
FROM rust:bullseye as pydeps

# python3-curl is built with gnutls so we build it by hand
RUN apt update && \
    DEBIAN_FRONTEND=noninteractive apt install -y gcc openssl libcurl4-openssl-dev libssl-dev pkg-config libffi-dev libssh-dev python3-pip python3-dev git
RUN python3 -m pip install -U pip setuptools
RUN CARGO_NET_GIT_FETCH_WITH_CLI=true pip3 -v install --no-cache-dir cryptography
RUN pip3 install pycurl==7.43.0.6
RUN pip3 install asyncssh==2.2.1 netifaces==0.10.9 requests==2.23.0 pyyaml==5.3.1 pydantic==1.5.1

# Build Container -------------------------------------------------------------
FROM debian:bullseye

# opensc install tzdata which requires user input without this:
ENV TZ=UTC
RUN \
	ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone && \
	apt update &&\
	apt install -y bash openssh-client python3 sshpass && \
	apt install -y bash libcurl4 libengine-pkcs11-openssl opensc softhsm && \
	ln -s /usr/local/bin/reboot /sbin/reboot && \
	ln -s /usr/lib/*-linux-gnu/engines-1.1 /usr/lib/engines-1.1 && \
	rm -rf /var/lib/apt/lists/*

COPY --from=pydeps /usr/local/lib/python3.9/dist-packages/ /usr/local/lib/python3.9/dist-packages/
COPY ./bin/* /usr/local/bin/
COPY ./tests /usr/share/fio-tests
COPY ./fiotest /usr/local/lib/python3.9/dist-packages/fiotest
COPY ./aklite-callback.sh /
COPY ./trigger-target-tests.sh /
