# Build LTP ------------------------------------------------------------------
FROM ubuntu:20.04 as ltp

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

# Build Container -------------------------------------------------------------
FROM ubuntu:20.04

RUN \
	apt update &&\
	apt install -y bash openssh-client python3 python3-pip sshpass && \
	ln -s /usr/local/bin/reboot /sbin/reboot && \
	pip3 install asyncssh==2.2.1 netifaces==0.10.9 requests==2.23.0 pyyaml==5.3.1 pydantic==1.5.1 && \
	rm -rf /var/lib/apt/lists/*

COPY --from=ltp /opt/ltp /opt/ltp
COPY ./bin/* /usr/local/bin/
COPY ./tests /usr/share/fio-tests
COPY ./fiotest /usr/local/lib/python3.8/dist-packages/fiotest
COPY ./aklite-callback.sh /
COPY ./trigger-target-tests.sh /
