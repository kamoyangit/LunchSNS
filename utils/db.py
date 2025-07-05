# utils/db.py

import firebase_admin
from firebase_admin import credentials, firestore, storage
import datetime
import pytz
import os
import json

# --- Firestore 初期化 ---
# この関数は app.py から一度だけ呼び出される
_db_initialized = False
db = None
bucket = None

def initialize_firestore():
    """Firestoreデータベースを初期化します。"""
    global _db_initialized, db, bucket
    if _db_initialized:
        return

    import base64 # base64をインポート
    
    try:    
        # Streamlit CloudのSecretsを使用する場合
        if 'FIREBASE_CREDENTIALS' in os.environ:
            # creds_json = json.loads(os.environ['FIREBASE_CREDENTIALS'])
            # cred = credentials.Certificate(creds_json)
            b64_creds = os.environ['FIREBASE_CREDENTIALS']
            decoded_creds = base64.b64decode(b64_creds)
            creds_json = json.loads(decoded_creds)
            cred = credentials.Certificate(creds_json)
        # ローカルのJSONファイルを使用する場合
        else:
            cred = credentials.Certificate("firebase-credentials.json")

        # ▼▼▼▼▼ ここから修正 ▼▼▼▼▼
        # プロジェクトIDを取得
        project_id = cred.project_id
    
        # !!!! 実際のバケット名に合わせてドメインを修正 !!!!
        # ".appspot.com" ではなく、コンソールで確認した ".firebasestorage.app" を使用
        bucket_name = f'{project_id}.firebasestorage.app'

        # アプリの初期化
        firebase_admin.initialize_app(cred, {
            'storageBucket': bucket_name
        })
    
        db = firestore.client()
        # バケット名を明示的に指定して取得する
        bucket = storage.bucket(name=bucket_name) 
        _db_initialized = True
        print(f"Firebase initialized. Using bucket: {bucket_name}") # 確認用のログを更新
        # ▲▲▲▲▲ ここまで修正 ▲▲▲▲▲
        
    except Exception as e:
        print(f"!!!!!!!!!! FIREBASE INITIALIZATION FAILED !!!!!!!!!!")
        print(f"Error: {e}")
        # エラー時にもアプリが停止しないように、ダミーの値を設定するなどしても良いが、
        # ここではエラーを明確にするためにraiseする
        raise e

# --- Helper Functions ---
def _doc_to_dict(doc):
    """Firestoreのドキュメントを辞書に変換し、IDを追加します。"""
    # docがNoneの場合、またはドキュメントが存在しない場合に対応
    if not doc or not doc.exists:
        return None
    data = doc.to_dict()
    data['id'] = doc.id
    return data

# --- User Functions ---
def create_user(nickname, password_hash):
    """新規ユーザーを作成します。"""
    # ニックネームの重複チェック
    users_ref = db.collection('users')
    existing_user = users_ref.where('nickname', '==', nickname).limit(1).stream()
    if len(list(existing_user)) > 0:
        return False # ニックネームが既に存在

    users_ref.add({
        'nickname': nickname,
        'password_hash': password_hash,
        'created_at': firestore.SERVER_TIMESTAMP
    })
    return True

def get_user(nickname):
    """ニックネームでユーザーを取得します。"""
    users_ref = db.collection('users')
    docs = users_ref.where('nickname', '==', nickname).limit(1).stream()
    user_doc = next(docs, None)
    return _doc_to_dict(user_doc)

def get_user_by_id(user_id):
    """IDでユーザーを取得します。"""
    doc_ref = db.collection('users').document(user_id)
    return _doc_to_dict(doc_ref.get())

# --- Post Functions ---
def create_post(user_id, nickname, comment, image_path, shop_name, price):
    """新規投稿を作成します。"""
    db.collection('posts').add({
        'user_id': user_id,
        'nickname': nickname, # 非正規化: ユーザーのニックネームを投稿に含める
        'comment': comment,
        'image_path': image_path, # Firebase Storageのパス or URL
        'shop_name': shop_name,
        'price': price,
        'like_count': 0, # 非正規化: いいね数を投稿に含める
        'created_at': firestore.SERVER_TIMESTAMP
    })

def get_all_posts():
    """全ての投稿を取得します。"""
    docs = db.collection('posts').order_by('created_at', direction=firestore.Query.DESCENDING).stream()
    return [_doc_to_dict(doc) for doc in docs]

# --- Like Functions ---
@firestore.transactional
def _update_like_count(transaction, post_ref, increment):
    """トランザクション内でいいね数をアトミックに更新します。"""
    snapshot = post_ref.get(transaction=transaction)
    new_count = snapshot.get('like_count') + increment
    transaction.update(post_ref, {'like_count': new_count})

def check_like(user_id, post_id):
    """ユーザーが既に投稿にいいねしているか確認します。"""
    # ドキュメントIDを複合キーのように扱うことで高速にチェック
    like_ref = db.collection('likes').document(f"{user_id}_{post_id}")
    return like_ref.get().exists

def add_like(user_id, post_id):
    """投稿にいいねを追加し、投稿のいいね数をインクリメントします。"""
    like_ref = db.collection('likes').document(f"{user_id}_{post_id}")
    # 既にいいね済みかチェック
    if like_ref.get().exists:
        return

    like_ref.set({
        'user_id': user_id,
        'post_id': post_id,
        'created_at': firestore.SERVER_TIMESTAMP
    })
    
    # 投稿のlike_countをインクリメント
    post_ref = db.collection('posts').document(post_id)
    transaction = db.transaction()
    _update_like_count(transaction, post_ref, 1)

def remove_like(user_id, post_id):
    """投稿のいいねを解除し、投稿のいいね数をデクリメントします。"""
    like_ref = db.collection('likes').document(f"{user_id}_{post_id}")
    # いいねが存在するかチェック
    if not like_ref.get().exists:
        return
        
    like_ref.delete()
    
    # 投稿のlike_countをデクリメント
    post_ref = db.collection('posts').document(post_id)
    transaction = db.transaction()
    _update_like_count(transaction, post_ref, -1)


# --- Award Function ---
def get_lunch_award():
    """今日の投稿でいいね数が最も多い投稿を取得します。"""
    jst = pytz.timezone('Asia/Tokyo')
    today = datetime.datetime.now(jst).date()
    start_of_day = jst.localize(datetime.datetime.combine(today, datetime.time.min))
    end_of_day = jst.localize(datetime.datetime.combine(today, datetime.time.max))

    query = db.collection('posts') \
        .where('created_at', '>=', start_of_day) \
        .where('created_at', '<=', end_of_day) \
        .order_by('like_count', direction=firestore.Query.DESCENDING) \
        .limit(1)
        
    docs = query.stream()
    award_post_doc = next(docs, None)
    return _doc_to_dict(award_post_doc)

# --- Admin Dashboard Functions ---
def get_dashboard_stats():
    """ダッシュボード用の統計情報を取得します。"""
    # .count()はFirestoreの比較的新しい機能で、ドキュメント全体を読み込むより効率的
    # ただし無料枠の読み取り回数にはカウントされる
    stats = {}
    stats['user_count'] = db.collection('users').count().get()[0][0].value
    stats['post_count'] = db.collection('posts').count().get()[0][0].value
    stats['like_count'] = db.collection('likes').count().get()[0][0].value
    
    # 時系列データは全件取得してPython側で処理する
    all_posts = get_all_posts()
    post_timeline = {}
    for post in all_posts:
        if 'created_at' in post and isinstance(post['created_at'], datetime.datetime):
            date_str = post['created_at'].strftime('%Y-%m-%d')
            post_timeline[date_str] = post_timeline.get(date_str, 0) + 1
    
    # list of [date, count]
    post_timeline_list = sorted(post_timeline.items())

    # 人気投稿ランキング
    popular_posts_docs = db.collection('posts').order_by('like_count', direction=firestore.Query.DESCENDING).limit(10).stream()
    popular_posts = [
        (p.get('comment'), p.get('nickname'), p.get('like_count')) 
        for p in popular_posts_docs
    ]
    
    return stats, post_timeline_list, popular_posts


def get_all_users():
    """管理者以外の全ユーザーを取得します。"""
    docs = db.collection('users').where('nickname', '!=', 'admin').order_by('created_at', direction=firestore.Query.DESCENDING).stream()
    return [_doc_to_dict(doc) for doc in docs]

# --- 自分の投稿履歴 & 編集・削除 ---

def get_posts_by_user(user_id):
    """特定のユーザーの投稿をすべて取得します。"""
    docs = db.collection('posts').where('user_id', '==', user_id).order_by('created_at', direction=firestore.Query.DESCENDING).stream()
    return [_doc_to_dict(doc) for doc in docs]

def update_post(post_id, comment, shop_name, price):
    """投稿の内容を更新します。"""
    db.collection('posts').document(post_id).update({
        'comment': comment,
        'shop_name': shop_name,
        'price': price
    })

def delete_post(post_id):
    """投稿と関連データを削除します。"""
    post_ref = db.collection('posts').document(post_id)
    post_doc = post_ref.get()
    if not post_doc.exists:
        return False

    # 1. 画像ファイルをCloud Storageから削除
    image_path = post_doc.get('image_path')
    if image_path:
        blob = bucket.blob(image_path)
        if blob.exists():
            blob.delete()

    # 2. 投稿に紐づく「いいね」を削除
    likes_query = db.collection('likes').where('post_id', '==', post_id).stream()
    batch = db.batch()
    for like in likes_query:
        batch.delete(like.reference)
    batch.commit()

    # 3. 投稿本体を削除
    post_ref.delete()
    return True

# --- ユーザー削除 ---
def delete_user(user_id):
    """ユーザーアカウントと関連データをすべて削除します。"""
    try:
        # 1. ユーザーの投稿を取得
        user_posts = get_posts_by_user(user_id)
        post_ids = [post['id'] for post in user_posts]

        # 2. ユーザーの投稿と、それに付随するいいね、画像を削除
        for post in user_posts:
            delete_post(post['id']) # 既存の関数を再利用

        # 3. ユーザー自身が付けた「いいね」を削除 & 関連投稿のいいね数も減らす
        likes_by_user_query = db.collection('likes').where('user_id', '==', user_id).stream()
        batch = db.batch()
        for like in likes_by_user_query:
            # いいねを削除
            batch.delete(like.reference)
            # 関連投稿のいいね数をデクリメント
            post_id = like.get('post_id')
            if post_id:
                 post_ref = db.collection('posts').document(post_id)
                 # トランザクションはバッチと併用できないため、直接更新
                 # ここは厳密にはアトミックではないが、削除処理なので許容する
                 batch.update(post_ref, {'like_count': firestore.Increment(-1)})
        batch.commit()

        # 4. ユーザー自身を削除
        db.collection('users').document(user_id).delete()
        
        return True
    except Exception as e:
        print(f"An error occurred during user deletion: {e}")
        return False

# --- Admin User初期化 ---
def init_db(admin_nickname, admin_password_hash):
    """Firestoreの初期化と管理者ユーザーの存在確認・作成"""
    initialize_firestore()
    # 管理者ユーザーが存在するかチェック
    user = get_user(admin_nickname)
    if not user:
        print("Creating admin user...")
        create_user(admin_nickname, admin_password_hash)