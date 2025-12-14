import json
import os
import asyncio
import aiohttp
import urllib3

from Crypto.Cipher import AES
from Crypto.Util.Padding import pad

from proto import like_pb2
from proto import like_count_pb2
from proto import uid_generator_pb2

from config import URLS_LIKE, FILES, AES_KEY, AES_IV

urllib3.disable_warnings()

BASE_DIR = os.path.dirname(os.path.dirname(__file__))


def load_tokens(server):
    file = FILES.get(server, "token_bd.json")
    path = os.path.join(BASE_DIR, "tokens", file)
    with open(path, "r") as f:
        return json.load(f)


def encrypt_payload(data: bytes) -> bytes:
    cipher = AES.new(AES_KEY, AES.MODE_CBC, AES_IV)
    return cipher.encrypt(pad(data, 16))


async def send_like(uid: int, token: str, server: str):
    payload = like_pb2.LikeRequest()
    payload.uid = uid

    encrypted = encrypt_payload(payload.SerializeToString())

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/octet-stream",
        "User-Agent": "Dalvik/2.1.0"
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(
            URLS_LIKE[server],
            data=encrypted,
            headers=headers,
            ssl=False
        ) as resp:
            return resp.status


async def handler(request):
    try:
        uid = int(request.args.get("uid"))
        server = request.args.get("server", "bd")
    except Exception:
        return {
            "statusCode": 400,
            "body": json.dumps({"error": "Invalid UID"})
        }

    tokens = load_tokens(server)

    tasks = []
    for token in tokens:
        tasks.append(send_like(uid, token["token"], server))

    results = await asyncio.gather(*tasks, return_exceptions=True)

    success = sum(1 for r in results if r == 200)

    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({
            "uid": uid,
            "server": server,
            "likes_sent": success,
            "total_tokens": len(tokens)
        })
    }
