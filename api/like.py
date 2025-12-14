import os
import json
import time
import random
import aiohttp
import urllib3

from Crypto.Cipher import AES
from Crypto.Util.Padding import pad

# protobuf imports
from proto.like_pb2 import LikeRequest
from proto.like_count_pb2 import LikeCountRequest

from config import URLS_INFO, URLS_LIKE, FILES

urllib3.disable_warnings()

BASE_DIR = os.path.dirname(os.path.dirname(__file__))


# -------------------------------------------------
# Helpers
# -------------------------------------------------

def load_tokens(server: str):
    token_file = FILES.get(server, "token_bd.json")
    path = os.path.join(BASE_DIR, "tokens", token_file)

    if not os.path.exists(path):
        raise Exception("Token file not found")

    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def aes_encrypt(data: bytes, key_hex: str, iv_hex: str) -> bytes:
    key = bytes.fromhex(key_hex)
    iv = bytes.fromhex(iv_hex)
    cipher = AES.new(key, AES.MODE_CBC, iv)
    return cipher.encrypt(pad(data, 16))


def build_headers(token: dict) -> dict:
    return {
        "User-Agent": token["user_agent"],
        "Authorization": f"Bearer {token['access_token']}",
        "Content-Type": "application/x-protobuf",
        "Accept": "*/*"
    }


# -------------------------------------------------
# Core API Logic
# -------------------------------------------------

async def send_like(uid: str, server: str):
    token = random.choice(load_tokens(server))

    req = LikeRequest()
    req.uid = uid
    req.timestamp = int(time.time())

    payload = aes_encrypt(
        req.SerializeToString(),
        token["aes_key"],
        token["aes_iv"]
    )

    async with aiohttp.ClientSession() as session:
        async with session.post(
            URLS_LIKE[server],
            data=payload,
            headers=build_headers(token),
            ssl=False
        ) as resp:
            await resp.read()


async def fetch_like_count(uid: str, server: str) -> bytes:
    token = random.choice(load_tokens(server))

    req = LikeCountRequest()
    req.uid = uid

    payload = aes_encrypt(
        req.SerializeToString(),
        token["aes_key"],
        token["aes_iv"]
    )

    async with aiohttp.ClientSession() as session:
        async with session.post(
            URLS_INFO[server],
            data=payload,
            headers=build_headers(token),
            ssl=False
        ) as resp:
            return await resp.read()


# -------------------------------------------------
# Vercel Entry Point (DO NOT RENAME)
# -------------------------------------------------

async def handler(request):
    try:
        params = request.query_params

        uid = params.get("uid")
        server = params.get("server", "bd")

        if not uid:
            return {
                "statusCode": 400,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"error": "uid parameter is required"})
            }

        await send_like(uid, server)
        await fetch_like_count(uid, server)

        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({
                "success": True,
                "uid": uid,
                "server": server,
                "timestamp": int(time.time())
            })
        }

    except Exception as e:
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({
                "success": False,
                "error": str(e)
            })
        }
