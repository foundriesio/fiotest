import asyncio
import asyncssh


def _host_connect():
    return asyncssh.connect(
        "172.17.0.1", known_hosts=None, username="fio", password="fio"
    )


def execute(cmd: str) -> str:
    async def ssh():
        async with _host_connect() as conn:
            return await conn.run(cmd)

    try:
        loop = asyncio.get_event_loop()
        if loop is None:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        result = loop.run_until_complete(ssh())
        return result.stdout
    except (OSError, asyncssh.Error) as exc:
        print("SSH connection failed: " + str(exc))
