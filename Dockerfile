# Build Python Deps------------------------------------------------------------
FROM ubuntu:20.04 as pydeps

# python3-curl is built with gnutls so we build it by hand
RUN apt update && \
	apt install -y gcc libcurl4-openssl-dev libffi-dev libssh-dev python3-pip python3-dev rustc cargo
RUN pip3 install pycurl==7.43.0.6
RUN pip3 install asyncssh==2.2.1 netifaces==0.10.9 requests==2.23.0 pyyaml==5.3.1 pydantic==1.5.1

# Build Container -------------------------------------------------------------
FROM ubuntu:20.04

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

COPY --from=pydeps /usr/local/lib/python3.8/dist-packages/ /usr/local/lib/python3.8/dist-packages/
COPY ./bin/* /usr/local/bin/
COPY ./tests /usr/share/fio-tests
COPY ./fiotest /usr/local/lib/python3.8/dist-packages/fiotest
COPY ./aklite-callback.sh /
COPY ./trigger-target-tests.sh /
