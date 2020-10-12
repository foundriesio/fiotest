# Build LTP ------------------------------------------------------------------
FROM ubuntu:19.10 as ltp

RUN apt update && \
	apt install -y gcc git make pkgconf autoconf automake bison flex m4 libc6-dev wget

RUN wget -O /ltp.tar.xz https://github.com/linux-test-project/ltp/releases/download/20200515/ltp-full-20200515.tar.xz
RUN tar -xf /ltp.tar.xz
RUN	cd ltp-full* && \
	./configure && \
	make -j8 all && \
	make install

RUN cd /opt/ltp/testcases/bin && \
	(strip `ls | grep -v .sh | grep -v .py` || true)

# Build Python Deps------------------------------------------------------------
FROM ubuntu:19.10 as pydeps

# python3-curl is built with gnutls so we build it by hand
RUN apt update && \
	apt install -y gcc libcurl4-openssl-dev libffi-dev libssh-dev python3-pip python3-dev
RUN pip3 install pycurl==7.43.0.6
RUN pip3 install asyncssh==2.2.1 netifaces==0.10.9 requests==2.23.0 pyyaml==5.3.1 pydantic==1.5.1

# Build Container -------------------------------------------------------------
FROM ubuntu:19.10

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

COPY --from=ltp /opt/ltp /opt/ltp
COPY --from=pydeps /usr/local/lib/python3.7/dist-packages/ /usr/local/lib/python3.7/dist-packages/
COPY --from=pydeps /usr/lib/python3/dist-packages/six* /usr/local/lib/python3.7/dist-packages/
COPY ./bin/* /usr/local/bin/
COPY ./tests /usr/share/fio-tests
COPY ./fiotest /usr/local/lib/python3.7/dist-packages/fiotest
COPY ./aklite-callback.sh /
COPY ./trigger-target-tests.sh /
