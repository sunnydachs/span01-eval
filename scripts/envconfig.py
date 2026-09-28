"""span01-eval 共通の環境読み込みとエラー処理。

APIキーは次の順で探します（1つ見つかった時点で終わり）:
  1. 環境変数 SPAN01_API_KEY
  2. 環境変数 OPENROUTER_API_KEY
  3. リポジトリ直下の .env の SPAN01_API_KEY / OPENROUTER_API_KEY

どれも無ければ、セットアップ手順を示して終了します。
"""
import os

ENV_NAMES = ("SPAN01_API_KEY", "OPENROUTER_API_KEY")
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


def get_key():
    """(key, source) を返す。見つからなければセットアップ手順を示して SystemExit。"""
    for name in ENV_NAMES:
        v = os.getenv(name)
        if v:
            return v, f"env:{name}"
    file_env = _read_env_file(ENV_FILE)
    for name in ENV_NAMES:
        if file_env.get(name):
            return file_env[name], f".env:{name}"
    raise SystemExit(
        "API key not found. Set SPAN01_API_KEY (or OPENROUTER_API_KEY):\n"
        "  export SPAN01_API_KEY=sk-or-...        # or\n"
        "  echo 'SPAN01_API_KEY=sk-or-...' > .env # repo root, git-ignored"
    )
