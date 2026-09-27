import argparse
import json
import os
import sys
import time
from datetime import date
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

try:
    import truststore

    truststore.inject_into_ssl()
except Exception:
    pass

ROOT = Path(__file__).parent
CONTENT_PATH = ROOT / "content" / "posts.json"
STATE_PATH = ROOT / "state" / "published.json"
ENV_PATH = ROOT / ".env"

MEDIA_SLUG = "INSTAGRAM_POST_IG_USER_MEDIA"
CAROUSEL_SLUG = "INSTAGRAM_CREATE_CAROUSEL_CONTAINER"
PUBLISH_SLUG = "INSTAGRAM_POST_IG_USER_MEDIA_PUBLISH"
WHOAMI_SLUG = "INSTAGRAM_GET_USER_INFO"


def load_env():
    if ENV_PATH.exists():
        for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def required_env(name):
    value = os.environ.get(name)
    if not value:
        raise SystemExit(f"Variavel obrigatoria ausente: {name}")
    return value


def should_wait_for_start_date():
    start_date = os.environ.get("PUBLISH_START_DATE", "").strip()
    if not start_date:
        return False
    try:
        first_day = date.fromisoformat(start_date)
    except ValueError:
        raise SystemExit("PUBLISH_START_DATE precisa estar no formato YYYY-MM-DD.")
    today = date.today()
    if today < first_day:
        print(f"Publicacao ainda nao começou. Hoje: {today.isoformat()} | inicio: {first_day.isoformat()}")
        return True
    return False


def client():
    from composio import Composio

    load_env()
    return Composio(
        api_key=required_env("COMPOSIO_API_KEY"),
        toolkit_versions={"instagram": "latest"},
    )


def execute(tools, slug, arguments, user_id, retries=4):
    delay = 2
    last_error = None
    for attempt in range(retries):
        try:
            return tools.execute(
                slug,
                user_id=user_id,
                arguments=arguments,
                dangerously_skip_version_check=True,
            )
        except Exception as exc:
            last_error = exc
            if attempt == retries - 1:
                break
            time.sleep(delay)
            delay *= 2
    raise last_error


def find_id(value):
    if isinstance(value, dict):
        for key in ("id", "creation_id", "container_id", "media_id"):
            if value.get(key):
                return str(value[key])
        for nested in value.values():
            found = find_id(nested)
            if found:
                return found
    if isinstance(value, list):
        for item in value:
            found = find_id(item)
            if found:
                return found
    return None


def load_data():
    return json.loads(CONTENT_PATH.read_text(encoding="utf-8"))


def load_state():
    if not STATE_PATH.exists():
        return {"published": []}
    return json.loads(STATE_PATH.read_text(encoding="utf-8"))


def save_state(state):
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def next_post(data, state, requested_id=None):
    published = {int(item["id"] if isinstance(item, dict) else item) for item in state.get("published", [])}
    for post in data["posts"]:
        if requested_id and post["id"] != requested_id:
            continue
        if requested_id or post["id"] not in published:
            return post
    return None


def hashtags_for(data, pilar):
    tags = []
    for tag in data["hashtags"]["base"] + data["hashtags"].get(pilar, []):
        if tag not in tags:
            tags.append(tag)
    return " ".join(tags)


def caption_for(data, post):
    return f"{post['caption']}\n\n👉 {post['cta']}\n\n{hashtags_for(data, post['pilar'])}"


def slide_urls(post, total, base_url):
    if not 2 <= total <= 10:
        raise SystemExit(f"Carrossel invalido: {total} imagens. Instagram aceita de 2 a 10.")
    base = base_url.rstrip("/")
    return [f"{base}/post_{post['id']:02d}/slide_{i:02d}.jpg" for i in range(1, total + 1)]


def inspect_tools(comp):
    for slug in (MEDIA_SLUG, CAROUSEL_SLUG, PUBLISH_SLUG, WHOAMI_SLUG):
        tool = comp.tools.get_raw_composio_tool_by_slug(slug)
        print(json.dumps(tool, indent=2, ensure_ascii=False, default=str))


def publish(post, data, dry_run=False):
    load_env()
    user_id = required_env("COMPOSIO_USER_ID")
    ig_user_id = required_env("IG_USER_ID")
    base_url = required_env("IMAGE_BASE_URL")
    total = len(post["slides"]) + 2
    urls = slide_urls(post, total, base_url)
    caption = caption_for(data, post)
    print(f"Post selecionado: {post['id']:02d}")
    print("Imagens:")
    for url in urls:
        print(f"- {url}")
    print("\nLegenda:\n" + caption)
    if dry_run:
        print("\nDry-run: nada foi publicado.")
        return None
    comp = client()
    children = []
    for url in urls:
        result = execute(
            comp.tools,
            MEDIA_SLUG,
            {"ig_user_id": ig_user_id, "image_url": url, "is_carousel_item": True},
            user_id,
        )
        media_id = find_id(result)
        if not media_id:
            raise RuntimeError(f"Nao encontrei id na resposta: {result}")
        children.append(media_id)
    carousel = execute(
        comp.tools,
        CAROUSEL_SLUG,
        {"ig_user_id": ig_user_id, "children": children, "caption": caption},
        user_id,
    )
    creation_id = find_id(carousel)
    if not creation_id:
        raise RuntimeError(f"Nao encontrei creation_id na resposta: {carousel}")
    time.sleep(8)
    result = execute(
        comp.tools,
        PUBLISH_SLUG,
        {"ig_user_id": ig_user_id, "creation_id": creation_id},
        user_id,
    )
    published_id = find_id(result) or creation_id
    return published_id


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--id", type=int)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--inspect", action="store_true")
    parser.add_argument("--whoami", action="store_true")
    args = parser.parse_args()

    load_env()
    if should_wait_for_start_date() and not args.dry_run and not args.inspect and not args.whoami:
        return

    if args.inspect:
        inspect_tools(client())
        return
    if args.whoami:
        comp = client()
        result = execute(comp.tools, WHOAMI_SLUG, {"ig_user_id": required_env("IG_USER_ID")}, required_env("COMPOSIO_USER_ID"))
        print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
        return

    data = load_data()
    state = load_state()
    post = next_post(data, state, args.id)
    if not post:
        print("Nenhum post pendente.")
        return
    published_id = publish(post, data, dry_run=args.dry_run)
    if published_id:
        state.setdefault("published", []).append({"id": post["id"], "instagram_id": published_id, "published_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())})
        save_state(state)
        print(f"Publicado e salvo no state: {published_id}")


if __name__ == "__main__":
    main()
