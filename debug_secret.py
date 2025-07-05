# debug_secret.py

import streamlit as st
import os

st.set_page_config(layout="wide")

st.title("Secrets デバッグページ")
st.warning("このページはデバッグ専用です。問題解決後はこのファイルを削除するか、アプリの実行ファイルをapp.pyに戻してください。")

# Streamlit CloudのSecretsが環境変数として読み込めているかを確認
if 'FIREBASE_CREDENTIALS' in os.environ:
    st.success("✅ Secretsに `FIREBASE_CREDENTIALS` が見つかりました。")
    
    # Secretsの中身をそのままテキストエリアに表示
    # これで、目に見えない文字やフォーマットの問題がすべて明らかになります
    secret_content = os.environ['FIREBASE_CREDENTIALS']
    st.text_area("↓↓↓ os.environ['FIREBASE_CREDENTIALS'] の実際の中身（この内容をすべてコピーして教えてください）↓↓↓", secret_content, height=400)

    # JSONとしてパースできるか試してみる
    import json
    try:
        json.loads(secret_content)
        st.success("✅ JSONとして正常にパースできました。")
        st.info("もしJSONとしてパースできているのにエラーが起きる場合、他の問題が考えられます。")
    except json.JSONDecodeError as e:
        st.error(f"❌ JSONとしてパースできませんでした。これがエラーの直接的な原因です。")
        st.code(f"エラー内容: {e}", language="bash")

else:
    st.error("❌ Secretsに `FIREBASE_CREDENTIALS` が見つかりません。")
    st.info("Secretsのキー名が `FIREBASE_CREDENTIALS` になっているか、もう一度確認してください。")