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
CONTENT_PATH = ROOT / "content" / "stories.json"
STATE_PATH = ROOT / "state" / "stories_published.json"
ENV_PATH = ROOT / ".env"

MEDIA_SLUG = "INSTAGRAM_POST_IG_USER_MEDIA"
PUBLISH_SLUG = "INSTAGRAM_POST_IG_USER_MEDIA_PUBLISH"


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
        raise SystemExit(f"Variável obrigatória ausente: {name}")
    return value


def should_wait_for_start_date():
    start_date = os.environ.get("PUBLISH_START_DATE", "").strip()
    if not start_date:
        return False
    first_day = date.fromisoformat(start_date)
    today = date.today()
    if today < first_day:
        print(f"Publicação ainda não começou. Hoje: {today.isoformat()} | início: {first_day.isoformat()}")
        return True
    return False


def client():
    from composio import Composio

    load_env()
    return Composio(api_key=required_env("COMPOSIO_API_KEY"), toolkit_versions={"instagram": "latest"})


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


def next_story(data, state, requested_id=None):
    published = {int(item["id"] if isinstance(item, dict) else item) for item in state.get("published", [])}
    for story in data["stories"]:
        if requested_id and story["id"] != requested_id:
            continue
        if requested_id or story["id"] not in published:
            return story
    return None


def story_url(story, base_url):
    return f"{base_url.rstrip('/')}/stories/story_{story['id']:02d}.jpg"


def publish(story, dry_run=False):
    load_env()
    user_id = required_env("COMPOSIO_USER_ID")
    ig_user_id = required_env("IG_USER_ID")
    image_url = story_url(story, required_env("IMAGE_BASE_URL"))
    print(f"Story selecionado: {story['id']:02d}")
    print(f"Imagem: {image_url}")
    print(f"Prompt manual: {story['prompt']}")
    if dry_run:
        print("\nDry-run: nada foi publicado.")
        return None
    comp = client()
    media = execute(
        comp.tools,
        MEDIA_SLUG,
        {"ig_user_id": ig_user_id, "image_url": image_url, "media_type": "STORIES"},
        user_id,
    )
    creation_id = find_id(media)
    if not creation_id:
        raise RuntimeError(f"Não encontrei creation_id na resposta: {media}")
    time.sleep(8)
    result = execute(comp.tools, PUBLISH_SLUG, {"ig_user_id": ig_user_id, "creation_id": creation_id}, user_id)
    return find_id(result) or creation_id


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--id", type=int)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    load_env()
    if should_wait_for_start_date() and not args.dry_run:
        return
    data = load_data()
    state = load_state()
    story = next_story(data, state, args.id)
    if not story:
        print("Nenhum story pendente.")
        return
    published_id = publish(story, dry_run=args.dry_run)
    if published_id:
        state.setdefault("published", []).append({"id": story["id"], "instagram_id": published_id, "published_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())})
        save_state(state)
        print(f"Story publicado e salvo no state: {published_id}")


if __name__ == "__main__":
    main()
