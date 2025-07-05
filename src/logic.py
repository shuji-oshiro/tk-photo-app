# --- データ処理・ロジック専用 ---
# 例：タグスキャンやサムネイルフィルタなどのロジックをここに分離しても良い（将来的な拡張用）

import os
import json
import datetime
import collections
import constants  # 定数をインポート


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
                "tags": existing_tag_map[fname].get("tags", [])
            }
        else:
            # 新規データの作成
            image_tag_map[fname] = {
                "createday": mtime_str, 
                "tags": []
            }
        
        # タグ集計用の一時リストに追加
        temp_tags.extend(image_tag_map[fname]["tags"])
        
    
    # 3. タグ情報の集計
    tag_counter = collections.Counter(temp_tags)
    
    # 他のタグを追加更新
    all_tags.update(tag_counter)

    # 4. 更新されたJSONファイルを保存
    try:
        with open(tags_json_path, "w", encoding="utf-8") as f:
            json.dump(image_tag_map, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"{constants.PICTURE_TAGS_JSON} の保存に失敗: {e}")


    return image_tag_map, all_tags
