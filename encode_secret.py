# encode_secret.py
import base64
from pathlib import Path

try:
    # JSONファイルを読み込む
    file_path = Path("firebase-credentials.json")
    json_content = file_path.read_text(encoding="utf-8")

    # Base64でエンコード
    encoded_content = base64.b64encode(json_content.encode("utf-8"))

    # エンコードされた文字列を表示
    print("----------- ↓↓↓ この下の行の文字列をすべてコピーしてください ↓↓↓ -----------")
    print(encoded_content.decode("utf-8"))
    print("----------- ↑↑↑ この上の行の文字列をすべてコピーしてください ↑↑↑ -----------")

except FileNotFoundError:
    print("エラー: firebase-credentials.json が見つかりません。このファイルと同じ階層で実行してください。")