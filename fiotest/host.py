import asyncio
import asyncssh
import sys
from typing import Optional

from fiotest.environment import docker_host


def _host_connect():
    return asyncssh.connect(
        docker_host(), known_hosts=None, username="fio", password="fio"
    )


class MySSHClientSession(asyncssh.SSHClientSession):
    def data_received(self, data, datatype):
        sys.stderr.write(data)

    def connection_lost(self, exc):
        if exc:
            print("SSH session error: " + str(exc))
            raise


def execute(cmd: str, stdin: Optional[str] = None) -> int:
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        # we are doing async on a thread that hasn't been set up
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    async def ssh():
        async with _host_connect() as conn:
            chan, session = await conn.create_session(MySSHClientSession, cmd)
            if stdin:
                chan.write(stdin + "\n")
                chan.write_eof()
            await chan.wait_closed()
            return chan.get_exit_status()

    try:
        return loop.run_until_complete(ssh())
    except (OSError, asyncssh.Error) as exc:
        print("SSH connection failed: " + str(exc))
        return 1


def sudo_execute(cmd: str) -> int:
    cmd = 'sudo -S /bin/sh -c "' + cmd + '"'
    return execute(cmd, "fio")
