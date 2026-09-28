"""span01-eval 共通の環境読み込みとエラー処理。

汎用的な LLM_API_KEY / LLM_BASE_URL 方式（agent-framework-showdown と同じ約束）:
  LLM_API_KEY    APIキー（OpenAI互換/OpenRouter互換のどちらでも）
  LLM_BASE_URL   APIのベースURL（既定: https://openrouter.ai/api）

キーは次の順で探します（1つ見つかった時点で終わり）:
  1. 環境変数 LLM_API_KEY
  2. 環境変数 SPAN01_API_KEY / OPENROUTER_API_KEY（後方互換）
  3. リポジトリ直下の .env の同じキー

どれも無ければ、セットアップ手順を示して終了します。
"""
import os

ENV_NAMES = ("LLM_API_KEY", "SPAN01_API_KEY", "OPENROUTER_API_KEY")
BASE_NAMES = ("LLM_BASE_URL", "SPAN01_BASE_URL")
DEFAULT_BASE_URL = "https://openrouter.ai/api"
ENV_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".env")


def _read_env_file(path):
    out = {}
    try:
        for line in open(path, encoding="utf-8"):
            line = line.strip()
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                out[k.strip()] = v.strip().strip('"').strip("'")
    except OSError:
        pass
    return out


def _lookup(names):
    for name in names:
        v = os.getenv(name)
        if v:
            return v, f"env:{name}"
    file_env = _read_env_file(ENV_FILE)
    for name in names:
        if file_env.get(name):
            return file_env[name], f".env:{name}"
    return None, None


def get_key():
    """(key, source) を返す。見つからなければセットアップ手順を示して SystemExit。"""
    key, src = _lookup(ENV_NAMES)
    if key:
        return key, src
    raise SystemExit(
        "API key not found. Set LLM_API_KEY:\n"
        "  export LLM_API_KEY=sk-...         # or\n"
        "  echo 'LLM_API_KEY=sk-...' > .env   # repo root, git-ignored\n"
        "(SPAN01_API_KEY / OPENROUTER_API_KEY also work as fallbacks)"
    )


def get_base_url():
    """APIベースURL（LLM_BASE_URL で上書き可。末尾スラッシュは除去）。"""
    base, _ = _lookup(BASE_NAMES)
    return (base or DEFAULT_BASE_URL).rstrip("/")
