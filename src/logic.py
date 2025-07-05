# --- データ処理・ロジック専用 ---
# 例：タグスキャンやサムネイルフィルタなどのロジックをここに分離しても良い（将来的な拡張用）

import os
import cv2
import json
import datetime
import functools
import pandas as pd
import tkinter as tk
import collections
from tkinter import ttk
from PIL import Image, ImageTk
import constants  # 定数をインポート


def scan_tags(self):
    # フォルダ内の画像・動画ファイルをスキャンし、タグ情報を初期化・読み込みする
    files = [f for f in os.listdir(self.select_folder) if os.path.splitext(f)[1].lower() in constants.VIDEO_AND_IMAGE_EXTS]

    # タグマップファイルのパス
    tags_json_path = os.path.join(self.select_folder, constants.PICTURE_TAGS_JSON)
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
    self.image_tag_map = {}
    temp_tags = []
    
    for fname in files:
        file_path = os.path.join(self.select_folder, fname)
        mtime = os.path.getmtime(file_path)
        mtime_str = datetime.datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M:%S')
        
        # 既存のJSONにデータがある場合は既存のタグ情報を使用、ない場合は新規作成
        if fname in existing_tag_map:
            # 既存データの更新（日付は最新のファイル更新日時で更新、タグは既存を保持）
            self.image_tag_map[fname] = {
                "createday": mtime_str, 
                "tags": existing_tag_map[fname].get("tags", [])
            }
        else:
            # 新規データの作成
            self.image_tag_map[fname] = {
                "createday": mtime_str, 
                "tags": []
            }
        
        # タグ集計用の一時リストに追加
        temp_tags.extend(self.image_tag_map[fname]["tags"])
        
    
    # 3. タグ情報の集計
    tag_counter = collections.Counter(temp_tags)
    
    # 他のタグを追加更新
    self.all_tags.update(tag_counter)

    # 4. 更新されたJSONファイルを保存
    try:
        with open(tags_json_path, "w", encoding="utf-8") as f:
            json.dump(self.image_tag_map, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"{constants.PICTURE_TAGS_JSON} の保存に失敗: {e}")



# 画像・動画ファイルの1フレーム目をサムネイル画像（PIL.Image）として返す
def get_video_thumbnail(self, filepath):
    try:
        cap = cv2.VideoCapture(filepath)
        ret, frame = cap.read()
        cap.release()
        if ret:
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(frame)
            img.thumbnail(constants.THUMBNAIL_SIZE)
            return img
    except Exception as e:
        print(f"{filepath} の動画サムネイル生成に失敗: {e}")
    return Image.new('RGB', constants.THUMBNAIL_SIZE, (128, 128, 128))



def show_thumbnails(self):
    # 選択中のタグ・日付範囲でサムネイルをフィルタし、一覧表示する
    for widget in self.image_frame.winfo_children():
        widget.destroy()
    self.thumbnails.clear()
    self.thumbnail_labels.clear()

    df = pd.DataFrame(self.image_tag_map).T
    df["createday"] = pd.to_datetime(df["createday"])

    # 日付範囲でファイルをフィルタリング
    from_date, to_date = self.date_range_manager.get_date_range()
    
    df = df[(df["createday"].dt.date >= from_date) & (df["createday"].dt.date <= to_date)] 

    # df = df.reset_index(drop=False)
    # 選択中のタグがある場合は、そのタグを含むファイルをフィルタリング
    if self.selected_tags == [constants.NONE_TAG_TEXT]:
        df = df[df['tags'].apply(lambda x: len(x) == 0)]

    elif self.selected_tags:
        df = df[df['tags'].apply(lambda x: set(self.selected_tags).issubset(set(x)))]
 
   
    # サムネイル表示の列数を計算    
    frame_width = self.winfo_width()

    columns = max(1, frame_width // self.min_thumb_width)
    self.current_columns = columns

    # サムネイルが選択されている状態と選択されていない状態の表示スタイル
    style = ttk.Style()
    style.configure("Selected.TLabel", background="#0066cc") # 選択中のサムネイルの背景色
    style.configure("TLabel", background="#ffffff") # 選択中でないサムネイルの背景色
    
    idx = 0
    for file, row in df.iterrows():
        try:
            # サムネイルキャッシュキーを生成
            cache_key = f"{file}_{constants.THUMBNAIL_SIZE[0]}_{constants.THUMBNAIL_SIZE[1]}"
            file_path = os.path.join(self.select_folder, file)

            # サムネイルキャッシュがない場合は、サムネイルを生成
            if cache_key not in self._thumbnail_cache:
                ext = os.path.splitext(file_path)[1].lower()
                if ext in constants.VIDEO_EXTS:
                    # 動画の場合は、サムネイルを生成
                    img = self.get_video_thumbnail(file_path)
                else:
                    # 画像の場合は、サムネイルを生成
                    img = Image.open(file_path)
                    img.thumbnail(constants.THUMBNAIL_SIZE)
                self._thumbnail_cache[cache_key] = img

            # サムネイルキャッシュがある場合は、キャッシュからサムネイルを取得
            else:
                img = self._thumbnail_cache[cache_key]

            # サムネイルを表示
            tk_img = ImageTk.PhotoImage(img)
            thumb_frame = ttk.Frame(self.image_frame)
            thumb_frame.grid(row=idx // columns, column=idx % columns, padx=10, pady=10)
            idx += 1

            # サムネイルが選択されている状態と選択されていない状態で表示方法を変える
            style_name = "Selected.TLabel" if file in self.selected_items else "TLabel"
            # lbl = ttk.Label(thumb_frame, image=tk_img, text=os.path.basename(file), compound="top", style=style_name)
            
            date_str = row.createday.strftime("%Y-%m-%d")
            lbl_text = f"{os.path.basename(file)}\n{date_str}"

            # ファイル名と日付を表示
            lbl = ttk.Label(thumb_frame, image=tk_img, text=lbl_text, compound="top", style=style_name)
            lbl.pack()
            
            self.thumbnail_labels[file] = lbl

            # イベントハンドラを設定
             
            for widget in [thumb_frame, lbl]:
                # サムネイルをダブルクリックしたときに標準アプリで開く
                widget.bind("<Double-Button-1>", lambda e, path=file_path, file=file: self.open_with_default_app(e, path, file))
                # サムネイルをクリックしたときの選択・解除処理
                widget.bind("<Button-1>", functools.partial(self.on_thumbnail_click, path=file))
                # サムネイルを右クリックしたときのコンテキストメニュー
                widget.bind("<Button-3>", self.on_main_frame_right_click)
            self.thumbnails.append(tk_img)
        except Exception as e:
            print(f"{file} の読み込みに失敗: {e}")

