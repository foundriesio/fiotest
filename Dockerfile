FROM ubuntu:20.04

ARG BUILD_PKGS="build-essential wget"

RUN \
	apt update -y  && \
	apt install -y $BUILD_PKGS python3 python3-requests && \
	wget -O /ltp.tar.xz https://github.com/linux-test-project/ltp/releases/download/20200515/ltp-full-20200515.tar.xz && \
		tar -xf /ltp.tar.xz && \
		cd ltp-full* && \
		./configure && \
		make -j8 all && \
		make install && \
		cd ../ && \
	rm -rf /ltp.tar.xz ./ltp-full* && \
	apt remove -y $BUILD_PKGS && \
	rm -rf /var/lib/apt/lists/* && \
	apt clean

COPY ./bin/* /usr/local/bin/
COPY ./tests /usr/share/fio-tests
