# --- データ処理・ロジック専用 ---
# 例：タグスキャンやサムネイルフィルタなどのロジックをここに分離しても良い（将来的な拡張用）

import os
import json
import datetime
import collections
import hashlib
import base64
from PIL import Image
import constants  # 定数をインポート


def _calculate_file_hash(file_path):
    """ファイルのハッシュ値を計算してファイル変更検知に使用"""
    try:
        with open(file_path, 'rb') as f:
            # ファイルサイズが大きい場合は最初の1MBのみでハッシュ計算
            content = f.read(1024 * 1024)
            return hashlib.md5(content).hexdigest()
    except Exception:
        return ""


def _generate_thumbnail_base64(file_path):
    """ファイルからサムネイルを生成しBase64エンコードして返す"""
    try:
        ext = os.path.splitext(file_path)[1].lower()
        if ext in constants.VIDEO_EXTS:
            img = _get_video_thumbnail(file_path)
        else:
            img = Image.open(file_path)
            img.thumbnail(constants.THUMBNAIL_SIZE, Image.Resampling.LANCZOS)
        
        # Base64エンコード
        import io
        buffer = io.BytesIO()
        img.save(buffer, format=constants.THUMBNAIL_FORMAT, quality=constants.THUMBNAIL_QUALITY)
        thumbnail_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
        
        return {
            "data": thumbnail_base64,
            "size": constants.THUMBNAIL_SIZE,
            "format": constants.THUMBNAIL_FORMAT
        }
    except Exception as e:
        print(f"サムネイル生成エラー {file_path}: {e}")
        return {}


def _get_video_thumbnail(filepath):
    """動画ファイルの1フレーム目をサムネイル画像として取得"""
    try:
        import cv2
        cap = cv2.VideoCapture(filepath)
        ret, frame = cap.read()
        cap.release()
        if ret:
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(frame)
            img.thumbnail(constants.THUMBNAIL_SIZE, Image.Resampling.LANCZOS)
            return img
    except Exception as e:
        print(f"動画サムネイル生成エラー {filepath}: {e}")
    
    # エラー時はグレーの画像を返す
    return Image.new('RGB', constants.THUMBNAIL_SIZE, (128, 128, 128))


def get_thumbnail_from_cache(file_info):
    """JSONから保存されたサムネイル情報を取得してPIL.Imageオブジェクトを返す"""
    try:
        thumbnail_data = file_info.get("thumbnail", {})
        if not thumbnail_data or "data" not in thumbnail_data:
            return None
        
        # Base64デコード
        thumbnail_bytes = base64.b64decode(thumbnail_data["data"])
        import io
        img = Image.open(io.BytesIO(thumbnail_bytes))
        return img
    except Exception as e:
        print(f"サムネイルキャッシュ読み込みエラー: {e}")
        return None


def update_thumbnail_cache(folder_path, image_tag_map):
    """サムネイルキャッシュを更新する（ファイル変更検知とサムネイル生成）"""
    updated = False
    
    for filename, file_info in image_tag_map.items():
        file_path = os.path.join(folder_path, filename)
        
        if not os.path.exists(file_path):
            continue
            
        # ファイルハッシュをチェックしてファイル変更を検知
        current_hash = _calculate_file_hash(file_path)
        cached_hash = file_info.get("file_hash", "")
        
        # ファイルが変更されているか、サムネイルがない場合
        if current_hash != cached_hash or not file_info.get("thumbnail", {}):
            print(f"サムネイル生成中: {filename}")
            file_info["thumbnail"] = _generate_thumbnail_base64(file_path)
            file_info["file_hash"] = current_hash
            updated = True
    
    return updated


def scan_tags(forlder_path):
    # フォルダ内の画像・動画ファイルをスキャンし、タグ情報を初期化・読み込みする
    files = [f for f in os.listdir(forlder_path) if os.path.splitext(f)[1].lower() in constants.VIDEO_AND_IMAGE_EXTS]

    # タグマップファイルのパス
    tags_json_path = os.path.join(forlder_path, constants.PICTURE_TAGS_JSON)
    existing_tag_map = {}
    
    # 1. 既存のJSONファイルが存在する場合は読み込み
    if os.path.exists(tags_json_path):
        try:
            with open(tags_json_path, "r", encoding="utf-8") as f:
                existing_tag_map = json.load(f)
        except Exception as e:
            print(f"{constants.PICTURE_TAGS_JSON} の読み込みに失敗: {e}")
            existing_tag_map = {}
    
    # 2. 新しいimage_tag_mapを構築
    image_tag_map = {}
    temp_tags = []
    all_tags = collections.Counter()  # タグ集計用のCounterオブジェクト
    for fname in files:
        file_path = os.path.join(forlder_path, fname)
        mtime = os.path.getmtime(file_path)
        mtime_str = datetime.datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M:%S')
        
        # 既存のJSONにデータがある場合は既存のタグ情報を使用、ない場合は新規作成
        if fname in existing_tag_map:
            # 既存データの更新（日付は最新のファイル更新日時で更新、タグは既存を保持）
            image_tag_map[fname] = {
                "createday": mtime_str, 
                "tags": existing_tag_map[fname].get("tags", []),
                "thumbnail": existing_tag_map[fname].get("thumbnail", {}),
                "file_hash": _calculate_file_hash(file_path)
            }
        else:
            # 新規データの作成
            image_tag_map[fname] = {
                "createday": mtime_str, 
                "tags": [],
                "thumbnail": {},
                "file_hash": _calculate_file_hash(file_path)
            }
        
        # タグ集計用の一時リストに追加
        temp_tags.extend(image_tag_map[fname]["tags"])
        
    
    # 3. タグ情報の集計
    tag_counter = collections.Counter(temp_tags)
    
    # 他のタグを追加更新
    all_tags.update(tag_counter)

    # 4. サムネイルキャッシュの更新
    cache_updated = update_thumbnail_cache(forlder_path, image_tag_map)
    
    # 5. 更新されたJSONファイルを保存（タグまたはサムネイルが更新された場合）
    if cache_updated:
        try:
            with open(tags_json_path, "w", encoding="utf-8") as f:
                json.dump(image_tag_map, f, ensure_ascii=False, indent=4)
            print("サムネイルキャッシュが更新されました")
        except Exception as e:
            print(f"{constants.PICTURE_TAGS_JSON} の保存に失敗: {e}")


    return image_tag_map, all_tags
