import asyncio
from enum import Enum
import logging
from typing import Any
import aiohttp
import os
import re
from dataclasses import dataclass


handler = logging.StreamHandler()
handler.setLevel(logging.INFO)

formatter = logging.Formatter("[%(levelname)s] %(message)s")
handler.setFormatter(formatter)

logging.basicConfig(force=True, handlers=[handler], level=logging.INFO)
logger = logging.getLogger(__name__)


_BASE_URL = "https://api.render.com/v1"


class Status(str, Enum):
    created = "created"
    building = "build_in_progress"
    updating = "update_in_progress"
    live = "live"
    deactivated = "deactivated"
    build_failed = "build_failed"
    update_failed = "update_failed"
    canceled = "canceled"
    rate_limited = "rate_limited"


@dataclass
class ScriptInputs:
    service_id: str
    deploy_id: str
    api_key: str
    poll_interval_s: int

    @staticmethod
    def from_env() -> "ScriptInputs":
        try:
            deploy_id = os.environ["RENDER_DEPLOY_ID"]
            webhook = os.environ["RENDER_WEBHOOK"]
            api_key = os.environ["RENDER_API_KEY"]
            poll_rate = int(os.environ.get("RENDER_POLL_RATE_S", 5))
        except KeyError as e:
            raise ValueError(f"missing environment variable: {e}") from e

        m = re.search(r"\/deploy\/(srv-[a-z0-9]+)", webhook)
        if not m:
            raise ValueError(f"could not extract service_id from webhook secret")

        service_id = str(m.group(1))
        return ScriptInputs(service_id, deploy_id, api_key, poll_rate)


async def get_deploy_status(
    service_id: str, deploy_id: str, api_key: str
) -> tuple[Status, bool]:
    """Gets the deploy status for a given Render deploy

    Args:
        service_id: the id of the service being deployed
        deploy_id: the id of the deployment to query
        api_key: the Render API key to use for authentication

    Returns:
        A tuple of the deploy status and a boolean indicating whether the deploy is finished

    Raises:
        `aiohttp.ClientResponseError`
    """
    url = f"{_BASE_URL}/services/{service_id}/deploys/{deploy_id}"
    async with aiohttp.ClientSession() as session:
        async with session.get(
            url, headers={"Authorization": f"Bearer {api_key}"}
        ) as resp:
            if resp.status == 429:
                return Status.rate_limited, False

            resp.raise_for_status()

            data: dict[str, Any] = await resp.json()
            return Status(data["status"]), data.get("finishedAt") is not None


async def poll(input: ScriptInputs) -> str:
    """Polls the status of a Render deploy

    Args:
        input: the input parameters for the script

    Returns:
        The final status of the deploy
    """

    is_done = False
    status = None
    while not is_done:
        await asyncio.sleep(input.poll_interval_s)
        status, is_done = await get_deploy_status(
            input.service_id, input.deploy_id, input.api_key
        )
        logger.info(f"polled status: {status}")

    if not status:
        raise RuntimeError("could not get deploy status")

    return status


def main():
    input = ScriptInputs.from_env()

    deploy_status = asyncio.run(poll(input))

    logger.info(f"final deploy status: {deploy_status}")
    if deploy_status != Status.live:
        raise RuntimeError("deploy is not live")


if __name__ == "__main__":
    main()
