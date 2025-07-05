# app.py
import streamlit as st
from pathlib import Path
import uuid
import pandas as pd
from utils import db, auth
import os 
import datetime # 追加
import pytz     # 追加
from streamlit_cookies_manager import CookieManager # 追加

# --- デバッグフラグ ---
# ここをTrue/Falseで切り替える
DEBUG = os.environ.get('DEBUG_OPTION')
# --------------------

# --- 定数 ---
# UPLOAD_DIR = Path("./uploads")
ADMIN_NICKNAME = os.environ.get('ADMIN_KEY')
ADMIN_PASSWORD = os.environ.get('PASS_KEY')

# 2. CookieManagerを初期化
# このコードはst.set_page_config()より後、他のStreamlit要素より前に配置するのが理想
# st.set_page_config(...) # もし使っているなら
cookies = CookieManager()

# --- 初期設定 ---
# UPLOAD_DIR.mkdir(exist_ok=True) # 不要
admin_pass_hash = auth.hash_password(ADMIN_PASSWORD)
db.init_db(ADMIN_NICKNAME, admin_pass_hash) # この中でFirestoreが初期化される

# --- セッション管理 ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user_info = None
    st.session_state.page = "タイムライン"
if 'editing_post_id' not in st.session_state:
    st.session_state.editing_post_id = None


# 3. アプリ起動時にCookieをチェックして自動ログインする処理を追加
# このコードブロックをセッション管理の直後あたりに配置します。

if not st.session_state.logged_in:
    login_cookie = cookies.get('lunch_sns_user_id')
    if login_cookie:
        # Cookieに保存されたuser_idを使ってユーザー情報をDBから取得
        # (このための関数をdb.pyに追加する必要があります)
        # ここでは簡易的に、get_user()を流用できる前提で進めますが、
        # 本来はget_user_by_id関数が良いでしょう。
        # まずは簡易的にニックネームで代用します
        user_info_from_cookie = db.get_user(login_cookie) # Cookieにはニックネームを保存する方針に
        if user_info_from_cookie:
            st.session_state.logged_in = True
            st.session_state.user_info = dict(user_info_from_cookie)
            st.session_state.page = "タイムライン"
            # 自動ログイン時はメッセージなしで再描画
            st.rerun()


# --- ヘルパー関数 ---
def is_lunch_time():
    jst = pytz.timezone('Asia/Tokyo')
    now_jst = datetime.datetime.now(jst).time()
    start_time = datetime.time(11, 0)
    end_time = datetime.time(14, 0)
    if DEBUG:
        return True
    else :
        return start_time <= now_jst < end_time

def set_editing_post(post_id):
    """編集対象の投稿IDをセッションにセットするコールバック関数"""
    st.session_state.editing_post_id = post_id

def is_mobile():
    """簡易的なモバイルデバイス判定"""
    user_agent = st.request.headers.get("User-Agent", "").lower()
    return any(m in user_agent for m in ["mobile", "iphone", "android"])

# --- UI描画関数 ---

def draw_login_form():
    # (この関数は変更なし)
    st.subheader("ログイン")
    with st.form("login_form"):
        nickname = st.text_input("ニックネーム")
        password = st.text_input("パスワード", type="password")
        submitted = st.form_submit_button("ログイン")
        if submitted:
            user = db.get_user(nickname)
            if user and auth.verify_password(password, user['password_hash']):
                st.session_state.logged_in = True
                st.session_state.user_info = dict(user)
                st.session_state.page = "タイムライン"
                     
                # ▼▼▼▼▼ Cookieを設定する処理を正しい構文に修正 ▼▼▼▼▼
                # 辞書のようにキーを指定して値を設定します
                cookies['lunch_sns_user_id'] = user['nickname']
                # ▲▲▲▲▲ ここまで修正 ▲▲▲▲▲
                
                st.success("ログインしました。")
                st.rerun()
            else:
                st.error("ニックネームまたはパスワードが間違っています。")

def draw_signup_form():
    # (この関数は変更なし)
    st.subheader("ユーザー登録")
    with st.form("signup_form"):
        nickname = st.text_input("ニックネーム")
        password = st.text_input("パスワード", type="password")
        password_confirm = st.text_input("パスワード（確認）", type="password")
        submitted = st.form_submit_button("登録")
        if submitted:
            if not nickname or not password:
                st.warning("ニックネームとパスワードを入力してください。")
            elif password != password_confirm:
                st.error("パスワードが一致しません。")
            else:
                password_hash = auth.hash_password(password)
                if db.create_user(nickname, password_hash):
                    st.success("ユーザー登録が完了しました。ログインしてください。")
                else:
                    st.error("そのニックネームは既に使用されています。")

def draw_post_form():
    # (この関数は変更なし)
    st.subheader("今日のランチを投稿しよう！")
    with st.form("post_form", clear_on_submit=True):
        comment = st.text_area("一言コメント *", help="今日のランチの感想をどうぞ！")
        
        # 画像ファイルのアップロード
        uploaded_file = st.file_uploader(
            "ランチの写真 *", type=['png', 'jpg', 'jpeg'], accept_multiple_files=False
        )
        
        # スマホとPCで、画像ファイルのアップロード方法を替える
        # if is_mobile():
        #     uploaded_file = st.camera_input("ランチの写真を撮影してください *")
        # else:
        #     uploaded_file = st.file_uploader(
        #         "ランチの写真をアップロードしてください *", 
        #         type=['png', 'jpg', 'jpeg'], 
        #         accept_multiple_files=False
        #     )
        
        # 画像のアップロード方法をユーザに選ばせる
        # upload_method = st.radio("写真のアップロード方法を選択:",["ファイルをアップロード", "カメラで撮影"])
        # if upload_method == "ファイルをアップロード":
        #     uploaded_file = st.file_uploader(
        #         "ランチの写真をアップロードしてください *", 
        #         type=['png', 'jpg', 'jpeg'], 
        #         accept_multiple_files=False
        #     )
        # else:
        #     uploaded_file = st.camera_input("ランチの写真を撮影してください *")
        
        shop_name = st.text_input("店舗名（任意）")
        price = st.number_input("金額（任意）", min_value=0, step=100)
        submitted = st.form_submit_button("投稿する")
        if submitted:
            if not comment or uploaded_file is None:
                st.warning("コメントと写真のアップロードは必須です。")
            else:
                if uploaded_file.size > 2 * 1024 * 1024:
                    st.error("ファイルサイズが大きすぎます。2MB以下の画像をアップロードしてください。")
                else:
                    # ▼▼▼▼▼ 画像アップロード処理をFirebase Cloud Storageに変更 ▼▼▼▼▼
                    ext = Path(uploaded_file.name).suffix
                    # ファイル名をユニークにする
                    filename = f"images/{uuid.uuid4()}{ext}"
                    
                    # Cloud Storageにアップロード
                    blob = db.bucket.blob(filename)
                    blob.upload_from_file(uploaded_file, content_type=uploaded_file.type)
                    
                    # 保存先パスとしてStorage上のパスをDBに保存
                    # (公開URLが必要な場合は blob.public_url を使うが、設定が必要)
                    image_path = filename 

                    user_id = st.session_state.user_info['id']
                    nickname = st.session_state.user_info['nickname'] # nicknameも渡す
                    db.create_post(user_id, nickname, comment, image_path, shop_name, price)
                    st.success("ランチを投稿しました！")
                    st.rerun()
                    # ▲▲▲▲▲ ここまで修正 ▲▲▲▲▲

def draw_edit_dialog(post_data):
    """投稿編集用のダイアログを表示"""
    @st.dialog("投稿を編集")
    def edit_dialog():
        with st.form("edit_form_dialog"):
            st.write(f"投稿ID: {post_data['id']}")
            new_comment = st.text_area("一言コメント", value=post_data['comment'])
            new_shop_name = st.text_input("店舗名（任意）", value=post_data['shop_name'] or "")
            new_price = st.number_input("金額（任意）", value=post_data['price'] or 0, min_value=0, step=100)
            
            submitted = st.form_submit_button("更新する")
            if submitted:
                db.update_post(post_data['id'], new_comment, new_shop_name, new_price)
                st.session_state.editing_post_id = None # 編集状態を解除
                st.rerun()
    
    edit_dialog()

def draw_post_card(post, is_mine=False, show_edit_buttons=False):
    """個々の投稿カードを描画する"""
    with st.container(border=True):
        col1, col2 = st.columns([1, 3])
        
        with col1:
            # ▼▼▼▼▼ Cloud Storageからの画像表示 ▼▼▼▼▼
            try:
                # 署名付きURLを生成して一時的に画像にアクセスできるようにする
                # 有効期限は1時間（3600秒）
                image_url = db.bucket.blob(post['image_path']).generate_signed_url(datetime.timedelta(seconds=3600))
                st.image(image_url, use_container_width='always')
            except Exception as e:
                st.error("画像が見つかりません")
                print(f"Error generating signed URL: {e}") # デバッグ用
            # ▲▲▲▲▲ ここまで修正 ▲▲▲▲▲

        with col2:
            # ▼▼▼▼▼ 日時オブジェクトを文字列にフォーマットする ▼▼▼▼▼
            # .strftime() を使って "YYYY-MM-DD HH:MM" 形式の文字列に変換
            created_at_str = post['created_at'].strftime('%Y-%m-%d %H:%M')
            st.markdown(f"**{post['nickname']}** <small>({created_at_str})</small>", unsafe_allow_html=True)
            # ▲▲▲▲▲ ここまで修正 ▲▲▲▲▲
            st.write(post['comment'])
            
            meta_info = []
            if post['shop_name']: meta_info.append(f"📍 {post['shop_name']}")
            if post['price']: meta_info.append(f"💰 ¥{post['price']:,}")
            if meta_info: st.caption(" | ".join(meta_info))

            # --- いいね & 編集/削除ボタンエリア ---
            btn_cols = st.columns([2, 1, 1])
            
            # いいねボタン
            with btn_cols[0]:
                if st.session_state.logged_in:
                    user_id = st.session_state.user_info['id']
                    liked = db.check_like(user_id, post['id'])
                    button_label = "❤️ いいね済み" if liked else "🤍 いいね！"
                    if st.button(button_label, key=f"like_{post['id']}"):
                        if liked: db.remove_like(user_id, post['id'])
                        else: db.add_like(user_id, post['id'])
                        st.rerun()
                else:
                    st.button("🤍 いいね！", key=f"like_{post['id']}", disabled=True)
                st.caption(f"いいね: {post['like_count']}件")
            
            # ▼▼▼▼▼ ここを修正 ▼▼▼▼▼
            # show_edit_buttons が True の場合のみ編集・削除ボタンを表示
            if show_edit_buttons:
                with btn_cols[1]:
                    st.button("✏️ 編集", key=f"edit_{post['id']}", on_click=set_editing_post, args=(post['id'],))
                with btn_cols[2]:
                    if st.button("🗑️ 削除", key=f"delete_{post['id']}", type="primary"):
                        if db.delete_post(post['id']):
                            st.success("投稿を削除しました。")
                            st.rerun()
                        else:
                            st.error("投稿の削除に失敗しました。")
            # ▲▲▲▲▲ ここまで修正 ▲▲▲▲▲

def draw_timeline():
    """タイムラインページを描画"""
    st.title("🍽️ みんなのランチ")
    
    # ▼▼▼▼▼ ここからが修正・復活させるコード ▼▼▼▼▼
    award_post = db.get_lunch_award()
    # アワードの表示条件: 投稿が存在し、かつ、いいねが1件以上あること
    if award_post and award_post['like_count'] > 0:
        # ▼▼▼▼▼ ここの文言を修正 ▼▼▼▼▼
        st.subheader("🏆 今日のランチアワード")
        # ▲▲▲▲▲ ここまで修正 ▲▲▲▲▲
        with st.container(border=True):
            col1, col2 = st.columns([1, 2])
            with col1:
                # ▼▼▼▼▼ 画像表示ロジックをCloud Storage対応のものに修正 ▼▼▼▼▼
                try:
                    # 署名付きURLを生成して画像にアクセス
                    image_url = db.bucket.blob(award_post['image_path']).generate_signed_url(datetime.timedelta(seconds=3600))
                    st.image(image_url, use_container_width=True)
                except Exception as e:
                    st.error("アワード画像の読み込みに失敗しました。")
                    print(f"Error loading award image URL: {e}") # デバッグ用にログ出力
                # ▲▲▲▲▲ ここまで修正 ▲▲▲▲▲
            with col2:
                st.markdown(f"**{award_post['nickname']}** さんの投稿")
                st.markdown(f"**「{award_post['comment']}」**")
                if award_post['shop_name']:
                    st.caption(f"📍 {award_post['shop_name']}")
                st.markdown(f"### 👑 いいね！ {award_post['like_count']}件")
        st.divider()
    # ▲▲▲▲▲ ここまで ▲▲▲▲▲

    if st.session_state.logged_in:
        with st.expander("投稿フォームを開く", expanded=False):
            if is_lunch_time(): draw_post_form()
            else: st.info("🕒 投稿は日本時間の午前11時〜午後2時の間のみ可能です。")
    else:
        st.info("投稿や「いいね」をするには、サイドバーからログインしてください。")

    st.subheader("みんなの投稿")
    posts = db.get_all_posts()
    if not posts:
        st.info("まだ投稿がありません。最初のランチを投稿してみましょう！")
        return

    current_user_id = st.session_state.user_info['id'] if st.session_state.logged_in else None
    for post in posts:
        # ▼▼▼▼▼ ここを修正 ▼▼▼▼▼
        # show_edit_buttonsを明示的にFalseにするか、引数を渡さない
        draw_post_card(post, is_mine=(post['user_id'] == current_user_id), show_edit_buttons=False)
        # ▲▲▲▲▲ ここまで修正 ▲▲▲▲▲
    
    # 編集ダイアログの表示処理
    if st.session_state.editing_post_id:
        target_post = next((p for p in posts if p['id'] == st.session_state.editing_post_id), None)
        if target_post:
            draw_edit_dialog(target_post)

def draw_my_posts_page():
    """自分の投稿履歴ページを描画"""
    st.title("📜 自分の投稿履歴")
    if not st.session_state.logged_in:
        st.warning("このページを見るにはログインが必要です。")
        st.stop()

    user_id = st.session_state.user_info['id']
    my_posts = db.get_posts_by_user(user_id)

    if not my_posts:
        st.info("まだ投稿がありません。タイムラインから最初のランチを投稿してみましょう！")
        return
    
    for post in my_posts:
        # ▼▼▼▼▼ ここを修正 ▼▼▼▼▼
        # is_mineは常にTrue、show_edit_buttonsもTrueにする
        draw_post_card(post, is_mine=True, show_edit_buttons=True)
        # ▲▲▲▲▲ ここまで修正 ▲▲▲▲▲

    # 編集ダイアログの表示処理
    if st.session_state.editing_post_id:
        target_post = next((p for p in my_posts if p['id'] == st.session_state.editing_post_id), None)
        if target_post:
            draw_edit_dialog(target_post)

def draw_dashboard():
    # (この関数は変更なし)
    st.title("📊 管理者ダッシュボード")
    stats, post_timeline, popular_posts = db.get_dashboard_stats()
    
    # 主要KPI
    col1, col2, col3 = st.columns(3)
    col1.metric("👤 ユーザー数", stats['user_count'])
    col2.metric("📝 投稿数", stats['post_count'])
    col3.metric("❤️ いいね総数", stats['like_count'])

    st.divider()

    # 時系列投稿数
    st.subheader("投稿数の推移")
    if post_timeline:
        # ▼▼▼▼▼ データ構造の変更に対応 ▼▼▼▼▼
        df_timeline = pd.DataFrame(post_timeline, columns=['date', 'count'])
        df_timeline['date'] = pd.to_datetime(df_timeline['date'])
        df_timeline = df_timeline.set_index('date')
        st.line_chart(df_timeline)
        # ▲▲▲▲▲ ここまで修正 ▲▲▲▲▲
    else:
        st.info("投稿データがありません。")

    # 人気投稿ランキング
    st.subheader("人気投稿ランキング")
    if popular_posts:
        df_popular = pd.DataFrame(popular_posts, columns=['コメント', '投稿者', 'いいね数'])
        st.dataframe(df_popular, use_container_width=True)
    else:
        st.info("いいねされた投稿がありません。")
    
    
    st.divider()
    # ▼▼▼▼▼ ここからユーザー管理機能を追加 ▼▼▼▼▼
    st.subheader("👥 ユーザー管理")

    all_users = db.get_all_users()

    if not all_users:
        st.info("管理者以外の登録ユーザーはいません。")
        return

    # 1. まず、辞書のリストからそのままDataFrameを作成
    df_users = pd.DataFrame(all_users)

    # 2. 表示に必要な列だけを選択し、順番を整える
    # (password_hashなどの不要な列を除外)
    df_users = df_users[['id', 'nickname', 'created_at']]
    
    # 3. 列名を日本語の表示名に変更する
    df_users.columns = ['ID', 'ニックネーム', '登録日時']
    
    # 4. 削除ボタンを設置するための列を追加
    df_users['アクション'] = [False] * len(df_users)
    
    # st.data_editorを使ってインタラクティブなテーブルを作成
    edited_df = st.data_editor(
        df_users,
        column_config={
            # ... (ここから下の data_editor の中身は変更なし)
            "アクション": st.column_config.CheckboxColumn(
                "削除実行",
                help="チェックを入れてユーザーを削除します",
                default=False,
            ),
            "ID": st.column_config.NumberColumn(disabled=True),
            "ニックネーム": st.column_config.TextColumn(disabled=True),
            "登録日時": st.column_config.DatetimeColumn(disabled=True, format="YYYY-MM-DD HH:mm"),
        },
        disabled=["ID", "ニックネーム", "登録日時"], 
        hide_index=True,
        use_container_width=True,
        key="user_management_editor"
    )

    # どのユーザーが削除対象としてチェックされたかを探す
    user_to_delete = None
    original_df_dict = df_users.set_index('ID').to_dict('index')
    edited_df_dict = edited_df.set_index('ID').to_dict('index')
    
    for user_id, user_data in edited_df_dict.items():
        if user_data['アクション'] and not original_df_dict[user_id]['アクション']:
            user_to_delete = {
                "id": user_id,
                "nickname": user_data['ニックネーム']
            }
            break

    # 削除対象のユーザーがいれば、確認メッセージと最終実行ボタンを表示
    if user_to_delete:
        st.error(f"**警告:** ユーザー「**{user_to_delete['nickname']}**」を削除しようとしています。")
        st.warning("この操作は元に戻せません。このユーザーの投稿、いいね、アカウント情報がすべて削除されます。")
        
        # 最終確認ボタン
        if st.button(f"「{user_to_delete['nickname']}」を完全に削除する", type="primary"):
            # 前回実装したアカウント削除関数を呼び出す
            if db.delete_user(user_to_delete['id']):
                st.success(f"ユーザー「{user_to_delete['nickname']}」を削除しました。")
                st.rerun() # ページをリロードしてリストを更新
            else:
                st.error("ユーザーの削除中にエラーが発生しました。")
    # ▲▲▲▲▲ ここまでユーザー管理機能 ▲▲▲▲▲

# --- サイドバー ---
with st.sidebar:
    st.header("みんなのランチ")
    
    if st.session_state.logged_in:
        user_info = st.session_state.user_info
        st.write(f"ようこそ、 **{user_info['nickname']}** さん")
        if st.button("ログアウト"):
                  
            # ▼▼▼▼▼ Cookieを削除する処理を正しい構文に修正 ▼▼▼▼▼
            # 辞書のようにdel文でキーを削除します
            if 'lunch_sns_user_id' in cookies:
                del cookies['lunch_sns_user_id']
            # ▲▲▲▲▲ ここまで修正 ▲▲▲▲▲
            
            st.session_state.logged_in = False
            st.session_state.user_info = None
            st.session_state.editing_post_id = None
            st.session_state.page = "タイムライン"
            st.rerun()

        st.divider()

        # --- ページ選択メニュー ---
        page_options = ["タイムライン", "自分の投稿"]
        if user_info['nickname'] == ADMIN_NICKNAME:
            page_options.append("管理者ダッシュボード")
        
        # current_page_index = page_options.index(st.session_state.page) if st.session_state.page in page_options else 0
        # st.session_state.page = st.radio("メニュー", page_options, index=current_page_index, key="page_selector")
        # key を "page" に変更し、st.session_state.page と直接連動させる
        # --------------------------------------------------------
        # 2回選択しないと切り替わらない問題の対策
        # 手動での代入 (=) は不要
        # --------------------------------------------------------
        st.radio(
            "メニュー", 
            page_options, 
            key="page" # session_stateのキーを直接指定
            # indexは自動で管理されるため、指定不要になることが多い
        )
        
    else:
        login_or_signup = st.selectbox("メニュー", ["ログイン", "ユーザー登録"])
        if login_or_signup == "ログイン":
            draw_login_form()
        else:
            draw_signup_form()

# --- メインコンテンツの描画 ---
if st.session_state.page == "タイムライン":
    draw_timeline()
elif st.session_state.page == "自分の投稿":
    draw_my_posts_page()
elif st.session_state.page == "管理者ダッシュボード":
    if st.session_state.logged_in and st.session_state.user_info['nickname'] == ADMIN_NICKNAME:
        draw_dashboard()
    else:
        st.error("このページへのアクセス権限がありません。")
        # st.page_link("app.py", label="タイムラインに戻る", icon="🏠")
        # st.page_linkの代わりに、st.markdownでHTMLリンクを作成
        st.markdown('<a href="/" target="_self">🏠 タイムラインに戻る</a>', unsafe_allow_html=True)