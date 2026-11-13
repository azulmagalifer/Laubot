import base64
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request

from nacl.public import PublicKey, SealedBox

# =========================================================
# CONFIGURACIÓN
# =========================================================
BROADCASTER_ID = os.getenv("KICK_BROADCASTER_USER_ID", "19129162")
CLIENT_ID = os.environ["KICK_CLIENT_ID"]
CLIENT_SECRET = os.environ["KICK_CLIENT_SECRET"]
REPOSITORY = os.environ["GITHUB_REPOSITORY"]
GH_TOKEN = os.environ["GH_SECRETS_TOKEN"]
GITHUB_API = os.getenv("GITHUB_API_URL", "https://api.github.com")

CASINO_INTERVAL = 300       # 5 minutos
INSTAGRAM_INTERVAL = 900    # 15 minutos
TABLA_INTERVAL = 600        # 10 minutos

# =========================================================
# MENSAJES
# =========================================================
MESSAGES = {
    "BETONWIN": (
        "Registrate con este link : "
        "https://betonwin.co/?serial=61354992&creative_id=4524&anid=eldelfox&tsrc=banner "
        "y disfruta de los grande beneficios que te da el casino por tu registro."
    ),
    "1WIN": (
        "Registrate con este link : https://lkaj.cc/20adfd "
        "y obtené un bono de bienvenida de hasta el 600% "
        "en tu primer deposito utilizando mi código: ELDELFOX500🍀"
    ),
    "SLOTICO": (
        "Registrate con este link : "
        "https://slotico.vip/?serial=61354992&creative_id=9079&anid=eldelfox&tsrc=social "
        "y disfruta de los grande beneficios que te da el casino por tu registro."
    ),
    "BIGGERZ": (
        "😎Registrate con este link: https://www.biggerz.com/?ref=ELDELFOX "
        "Utilizando mi codigo: ELDELFOX || obtené un bono de bienvenida "
        "en tu primer deposito y disfruta de todos los beneficios del casino😎"
    ),
    "GOLDRUSH": (
        "🎰Registrate con este link: "
        "https://goldclick.mom/kHz19sNf?sub2=eldelfox "
        "y disfrutá de los grandes beneficios que te ofrece GOLDRUSH por tu registro. "
        "🎰🍀 No hay codigo promocional 🍀"
    ),
}

INSTAGRAM_MESSAGE = (
    "Te invito a seguirme en mi instagram para no perderte de nada! "
    "https://www.instagram.com/eldelfox 💙"
)

TABLA_MESSAGE_1 = (
    "🏆 LEADERBOARD ELDELFOX: 6 premios: "
    "1.º $500 | 2.º $400 | 3.º $320 | 4.º $250 | 5.º $180 | 6.º $150. "
    "📅 Del 14/10/2026 20:00 UTC al 14/11/2026 23:00 UTC. "
    "¿Cómo funciona el wager? Las apuestas que hacés en los juegos habilitados "
    "se suman a tu wager y te ayudan a subir en la tabla. "
    "🎁 Los premios se acreditan en la cuenta del juego."
)
TABLA_MESSAGE_2 = (
    "🔗 Participá: "
    "https://one-vv2329.com/v3/8429/streamer-leaderboard-wager-race?p=kdx1 "
    "|| Código promocional: ELDELFOX500"
)

# =========================================================
# SECRETOS Y ESTADO PERSISTENTE
# =========================================================
def github_request(path, method="GET", payload=None):
    url = f"{GITHUB_API}/repos/{REPOSITORY}/{path}"
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {GH_TOKEN}",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "LauBot",
    }
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    if data is not None:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=25) as response:
            body = response.read().decode("utf-8")
            return response.status, json.loads(body) if body else {}
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"GitHub API {exc.code}: {body}") from exc


def update_github_secret(name, value):
    """Actualiza un Actions Secret usando la clave pública del repositorio."""
    _, key_data = github_request("actions/secrets/public-key")
    public_key = PublicKey(base64.b64decode(key_data["key"]))
    encrypted = SealedBox(public_key).encrypt(value.encode("utf-8"))
    payload = {
        "encrypted_value": base64.b64encode(encrypted).decode("ascii"),
        "key_id": key_data["key_id"],
    }
    github_request(f"actions/secrets/{name}", method="PUT", payload=payload)
    print(f"🔐 Se actualizó el secreto {name}.")


def load_json_secret(env_name, default):
    raw = os.getenv(env_name, "").strip()
    if not raw:
        return default
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"El secreto {env_name} no contiene JSON válido.") from exc


# =========================================================
# KICK API Y TOKENS
# =========================================================
def kick_request(url, tokens, method="GET", payload=None):
    headers = {
        "Authorization": f"Bearer {tokens['access_token']}",
        "Client-Id": CLIENT_ID,
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": "LauBot/2.0",
    }
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=25) as response:
            body = response.read().decode("utf-8")
            return response.status, json.loads(body) if body else {}
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        try:
            parsed = json.loads(body)
        except Exception:
            parsed = body
        return exc.code, parsed


def refresh_tokens(tokens):
    print("🔄 Renovando autorización de Kick...")
    form = urllib.parse.urlencode({
        "grant_type": "refresh_token",
        "refresh_token": tokens["refresh_token"],
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
    }).encode("utf-8")
    req = urllib.request.Request(
        "https://id.kick.com/oauth/token",
        data=form,
        headers={"Content-Type": "application/x-www-form-urlencoded", "Accept": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=25) as response:
            new_tokens = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"No se pudo renovar el token de Kick (HTTP {exc.code}): {detail}") from exc

    new_tokens["expires_at"] = int(time.time()) + int(new_tokens.get("expires_in", 3600)) - 60
    # Kick rota el refresh token: se guarda el nuevo inmediatamente.
    update_github_secret("KICK_TOKENS_JSON", json.dumps(new_tokens, separators=(",", ":")))
    tokens.clear()
    tokens.update(new_tokens)
    return tokens


def kick_request_with_refresh(url, tokens, method="GET", payload=None):
    status, response = kick_request(url, tokens, method, payload)
    if status == 401:
        refresh_tokens(tokens)
        status, response = kick_request(url, tokens, method, payload)
    return status, response


def send_chat_message(tokens, message):
    url = "https://api.kick.com/public/v1/chat"
    payload = {
        "broadcaster_user_id": int(BROADCASTER_ID),
        "content": message,
        "type": "user",
    }
    status, response = kick_request_with_refresh(url, tokens, "POST", payload)
    print(f"📨 Chat Kick: HTTP {status} | {response}")
    return status in (200, 201, 204)


def get_live_title(tokens):
    url = f"https://api.kick.com/public/v1/livestreams?broadcaster_user_id={BROADCASTER_ID}"
    status, data = kick_request_with_refresh(url, tokens)
    if status != 200:
        raise RuntimeError(f"Error consultando LIVE en Kick: HTTP {status} | {data}")
    streams = data.get("data", [])
    if not streams:
        return False, ""
    stream = streams[0]
    return True, stream.get("stream_title") or stream.get("title") or ""


def get_casino_command(title):
    upper = (title or "").upper()
    for command in ("BETONWIN", "1WIN", "SLOTICO", "BIGGERZ", "GOLDRUSH"):
        if f"!{command}" in upper:
            return command
    return None


def send_tabla_messages(tokens):
    if not send_chat_message(tokens, TABLA_MESSAGE_1):
        return False
    time.sleep(2)
    return send_chat_message(tokens, TABLA_MESSAGE_2)


# =========================================================
# UNA EJECUCIÓN: GITHUB ACTIONS LA INICIA CADA 5 MINUTOS
# =========================================================
def main():
    tokens = load_json_secret("KICK_TOKENS_JSON", {})
    if not tokens.get("access_token") or not tokens.get("refresh_token"):
        raise RuntimeError("Falta KICK_TOKENS_JSON o no contiene access_token y refresh_token.")

    state = load_json_secret("LAUBOT_STATE_JSON", {
        "last_casino_send_times": {},
        "last_instagram_send_time": 0,
        "last_tabla_send_time": 0,
        "was_live": False,
        "tabla_was_active": False,
    })
    state.setdefault("last_casino_send_times", {})
    state.setdefault("last_instagram_send_time", 0)
    state.setdefault("last_tabla_send_time", 0)
    state.setdefault("was_live", False)
    state.setdefault("tabla_was_active", False)

    live, title = get_live_title(tokens)
    now = time.time()

    if not live:
        print("⚪ Lau está offline. No se envían mensajes.")
        state["was_live"] = False
        state["tabla_was_active"] = False
        state["last_tabla_send_time"] = 0
        update_github_secret("LAUBOT_STATE_JSON", json.dumps(state, separators=(",", ":")))
        return

    print("🟢 Lau está LIVE. Título:", title or "(sin título)")
    if not state["was_live"]:
        print("🆕 Inicio de sesión LIVE detectado.")
        state["last_casino_send_times"] = {}
        state["last_instagram_send_time"] = 0
        state["last_tabla_send_time"] = 0
    state["was_live"] = True

    upper_title = (title or "").upper()
    tabla_active = "!LINKTABLA" in upper_title
    casino_command = get_casino_command(title)

    # Leaderboard independiente de los comandos de casino.
    if tabla_active:
        if not state["tabla_was_active"]:
            state["last_tabla_send_time"] = 0
            print("🏆 !LINKTABLA detectado.")
        if now - float(state["last_tabla_send_time"]) >= TABLA_INTERVAL:
            print("📢 Enviando leaderboard...")
            if send_tabla_messages(tokens):
                state["last_tabla_send_time"] = time.time()
    elif state["tabla_was_active"]:
        print("ℹ️ !LINKTABLA ya no está en el título.")
        state["last_tabla_send_time"] = 0
    state["tabla_was_active"] = tabla_active

    if casino_command:
        print(f"🎰 Comando detectado: !{casino_command}")
        last_sent = float(state["last_casino_send_times"].get(casino_command, 0))
        if time.time() - last_sent >= CASINO_INTERVAL:
            if send_chat_message(tokens, MESSAGES[casino_command]):
                state["last_casino_send_times"][casino_command] = time.time()
        # Igual que el bot original: el mensaje de Instagram espera 15 min
        # desde la última detección de un comando de casino.
        state["last_instagram_send_time"] = time.time()
    else:
        if not tabla_active and time.time() - float(state["last_instagram_send_time"]) >= INSTAGRAM_INTERVAL:
            print("📸 No hay comando de casino: enviando Instagram...")
            if send_chat_message(tokens, INSTAGRAM_MESSAGE):
                state["last_instagram_send_time"] = time.time()

    update_github_secret("LAUBOT_STATE_JSON", json.dumps(state, separators=(",", ":")))
    print("✅ Ejecución finalizada.")


if __name__ == "__main__":
    main()
