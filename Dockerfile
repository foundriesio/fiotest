FROM alpine:3.12

ARG BUILD_PKGS="acl-dev autoconf automake binutils gcc keyutils-dev libaio-dev libacl libcap-dev libffi-dev libselinux-dev libsepol-dev libtirpc-dev linux-headers make musl-dev openssl-dev python3-dev"

RUN \
	apk add --no-cache $BUILD_PKGS bash openssh-client python3 py3-pip sshpass && \
	rm /sbin/reboot && ln -s /usr/local/bin/reboot /sbin/reboot && \
	pip3 install asyncssh==2.2.1 requests==2.23.0 pyyaml==5.3.1 pydantic==1.5.1 && \
	wget -O /ltp.tar.xz https://github.com/linux-test-project/ltp/releases/download/20200515/ltp-full-20200515.tar.xz && \
		tar -xf /ltp.tar.xz && \
		cd ltp-full* && \
		rm -rf \
			testcases/kernel/sched/process_stress \
			testcases/kernel/syscalls/confstr \
			testcases/kernel/syscalls/fmtmsg \
			testcases/kernel/syscalls/getcontext \
			testcases/kernel/syscalls/getdents \
			testcases/kernel/syscalls/rt_tgsigqueueinfo \
			testcases/kernel/syscalls/timer_create \
			utils/benchmark && \
		./configure && \
		make -j8 all && \
		make install && \
		cd ../ && \
	rm -rf /ltp.tar.xz ./ltp-full* && \
	cd /opt/ltp/testcases/bin && \
	(strip `ls | grep -v .sh | grep -v .py` || true) && \
	apk del $BUILD_PKGS

COPY ./bin/* /usr/local/bin/
COPY ./tests /usr/share/fio-tests
COPY ./fiotest /usr/lib/python3.8/site-packages/fiotest
COPY ./aklite-callback.sh /
COPY ./trigger-target-tests.sh /
