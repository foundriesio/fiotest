FROM ubuntu:18.04

ARG BUILD_PKGS="build-essential python3-pip wget"

RUN \
	apt update -y  && \
	apt install -y $BUILD_PKGS python3 python3-asyncssh python3-requests python3-yaml && \
	ln -s /usr/local/bin/reboot /sbin/reboot && \
	pip3 install pydantic==1.5.1 && \
	wget -O /ltp.tar.xz https://github.com/linux-test-project/ltp/releases/download/20200515/ltp-full-20200515.tar.xz && \
		tar -xf /ltp.tar.xz && \
		cd ltp-full* && \
		./configure && \
		make -j8 all && \
		make install && \
		cd ../ && \
	rm -rf /ltp.tar.xz ./ltp-full* && \
	apt autoremove -y $BUILD_PKGS && \
	rm -rf /var/lib/apt/lists/* && \
	apt clean

COPY ./bin/* /usr/local/bin/
COPY ./tests /usr/share/fio-tests
COPY ./fiotest /usr/lib/python3/dist-packages/fiotest
COPY ./aklite-callback.sh /
