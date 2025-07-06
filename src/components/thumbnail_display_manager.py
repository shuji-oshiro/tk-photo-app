# --- サムネイル表示管理クラス ---
# サムネイルの表示・フィルタリング・選択状態の管理を担当

import os
import pandas as pd
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
import constants
import logic
from tkinter import messagebox


class ThumbnailDisplayManager:
    """
    サムネイル表示と管理を行うクラス
    """
    
    def __init__(self, parent_frame, 
                 select_folder, 
                 thumbnail_cache, 
                 on_right_click_callback=None):
        """
        初期化
        
        Args:
            parent_frame: サムネイルを表示するフレーム
            select_folder: 選択されたフォルダパス
            thumbnail_cache: サムネイルキャッシュ辞書
            on_right_click_callback: 右クリック時のコールバック
        """
        self.parent_frame = parent_frame
        self.select_folder = select_folder
        self.thumbnail_cache = thumbnail_cache
        
        # コールバック関数
        self.on_right_click_callback = on_right_click_callback
        
        # 表示管理
        self.thumbnails = []  # 参照保持用
        self.thumbnail_labels = {}  # サムネイルラベル保持
        self.selected_items = set()  # 選択中のファイル
        self.min_thumb_width = constants.THUMBNAIL_SIZE[0] + 20  # サムネイル1件分の最小幅
        self.current_columns = 1  # 画面に表示されるカラム数
        
        # スタイル設定
        self._setup_styles()
    
    # ===============================
    # セットアップ・設定メソッド
    # ===============================
    
    def _setup_styles(self):
        """サムネイルの表示スタイルを設定"""
        style = ttk.Style()
        style.configure("Selected.TLabel", background=constants.SELECTED_BACKGROUND_COLOR)
        style.configure("TLabel", background=constants.NORMAL_BACKGROUND_COLOR)
    
    # ===============================
    # 公開メソッド（外部インターフェース）
    # ===============================
    
    def show_thumbnails(self, image_tag_map, date_range, selected_tags, frame_width):
        """
        サムネイルを表示
        
        Args:
            image_tag_map: 画像タグマップ
            date_range: 日付範囲 (from_date, to_date)
            selected_tags: 選択されたタグリスト
            frame_width: フレームの幅
        """

        # 既存の選択状態をクリア
        self._clear_selection()

        # 既存のサムネイルをクリア
        self._clear_thumbnails()

        # データフレーム作成
        df = pd.DataFrame(image_tag_map).T
        df["createday"] = pd.to_datetime(df["createday"])

        # 日付範囲でファイルをフィルタリング
        from_date, to_date = date_range
        df = df[(df["createday"].dt.date >= from_date) & (df["createday"].dt.date <= to_date)]

        # タグでフィルタリング
        if selected_tags == [constants.NONE_TAG_TEXT]:
            df = df[df['tags'].apply(lambda x: len(x) == 0)]
        elif selected_tags:
            df = df[df['tags'].apply(lambda x: set(selected_tags).issubset(set(x)))]

        # 列数を計算
        columns = self._calculate_columns(frame_width)

        # サムネイルを表示
        idx = 0
        for file, row in df.iterrows():
            self._create_thumbnail_widget(file, row, idx, columns)
            idx += 1
    
    
    def add_to_selection(self, file):
        """ファイルを選択状態に追加"""
        self.selected_items.add(file)
        self._update_selection_style(file, True)
    
    def remove_from_selection(self, file):
        """ファイルを選択状態から削除"""
        self.selected_items.discard(file)
        self._update_selection_style(file, False)

    
    def get_selected_items(self):
        """選択中のファイル一覧を取得"""
        return self.selected_items.copy()
    
    def is_selected(self, file):
        """ファイルが選択されているかチェック"""
        return file in self.selected_items
    
    def toggle_selection(self, file):
        """ファイルの選択状態を切り替え"""
        if self.is_selected(file):
            self.remove_from_selection(file)
        else:
            self.add_to_selection(file)
    
    def open_with_default_app(self, path, file):
        """
        ファイルをデフォルトアプリケーションで開く処理
        - 指定されたパスのファイルを開く
        - ダブルクリック時はサムネイルの選択を解除
        - エラー発生時はエラーメッセージを表示
        """
        try:
            os.startfile(path)
            self.remove_from_selection(file)
        except Exception as e:
            print(f"{path} のオープンに失敗: {e}")
    
    # ===============================
    # 内部メソッド（プライベート）
    # ===============================
        
    def _clear_thumbnails(self):
        """表示中のサムネイルを全てクリア"""
        for widget in self.parent_frame.winfo_children():
            widget.destroy()
        self.thumbnails.clear()
        self.thumbnail_labels.clear()

    def _clear_selection(self):
        """全ての選択状態をクリア"""
        for file in list(self.selected_items):
            self.remove_from_selection(file)

    def _calculate_columns(self, frame_width):
        """
        表示可能な列数を計算
        
        Args:
            frame_width: フレームの幅
            
        Returns:
            int: 列数
        """
        columns = max(1, frame_width // self.min_thumb_width)
        self.current_columns = columns
        return columns
    
    def _create_thumbnail_widget(self, file, row, idx, columns):
        """
        個別のサムネイルウィジェットを作成
        
        Args:
            file: ファイル名
            row: データフレームの行
            idx: インデックス
            columns: 列数
        """
        try:
            # サムネイルキャッシュキーを生成
            cache_key = f"{file}_{constants.THUMBNAIL_SIZE[0]}_{constants.THUMBNAIL_SIZE[1]}"
            file_path = os.path.join(self.select_folder, file)

            # まずメモリキャッシュから取得を試行（最高速）
            if cache_key in self.thumbnail_cache:
                img = self.thumbnail_cache[cache_key]
            else:
                # メモリキャッシュにない場合、JSONキャッシュから取得
                img = logic.get_thumbnail_from_cache(row.to_dict() if hasattr(row, 'to_dict') else row)
                
                if img is None:
                    # JSONキャッシュからの取得に失敗した場合のフォールバック
                    print(f"警告: {file} のJSONキャッシュが見つかりません。新規生成します。")
                    img = self._generate_thumbnail(file_path)
                
                # メモリキャッシュに保存して次回の高速化
                self.thumbnail_cache[cache_key] = img

            # サムネイルを表示
            tk_img = ImageTk.PhotoImage(img)
            thumb_frame = ttk.Frame(self.parent_frame)
            thumb_frame.grid(row=idx // columns, column=idx % columns, padx=10, pady=10)

            # 選択状態に応じてスタイルを設定
            style_name = "Selected.TLabel" if file in self.selected_items else "TLabel"
            
            # ファイル名と日付を表示
            date_str = row.createday.strftime("%Y-%m-%d") if hasattr(row, 'createday') else row.get('createday', '')
            if isinstance(date_str, str) and date_str:
                try:
                    from datetime import datetime
                    date_obj = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
                    date_str = date_obj.strftime("%Y-%m-%d")
                except:
                    date_str = date_str[:10]  # 最初の10文字（YYYY-MM-DD）を取得
            
            lbl_text = f"{os.path.basename(file)}\n{date_str}"
            lbl = ttk.Label(thumb_frame, image=tk_img, text=lbl_text, compound="top", style=style_name)
            lbl.pack()
            
            self.thumbnail_labels[file] = lbl

            # イベントハンドラを設定
            self._bind_events(thumb_frame, lbl, file, file_path)
            self.thumbnails.append(tk_img)
            
        except Exception as e:
            print(f"{file} の読み込みに失敗: {e}")
    
    def _bind_events(self, thumb_frame, lbl, file, file_path):
        """
        サムネイルウィジェットにイベントをバインド
        
        Args:
            thumb_frame: サムネイルフレーム
            lbl: ラベルウィジェット
            file: ファイル名
            file_path: ファイルパス
        """
        for widget in [thumb_frame, lbl]:
            # ダブルクリック - 内部メソッドを直接呼び出し
            widget.bind("<Double-Button-1>", 
                       lambda e, path=file_path, f=file: self._on_thumbnail_double_click(e,path, f))
            
            # クリック - 内部メソッドを直接呼び出し
            widget.bind("<Button-1>", 
                       lambda e, f=file: self._on_thumbnail_click(e, f))
            
            # 右クリック
            widget.bind("<Button-3>", 
                       lambda e, f=file: self._on_thumbnail_right_click(e))
    
    def _generate_thumbnail(self, file_path):
        """
        ファイルからサムネイルを生成
        
        Args:
            file_path: ファイルパス
            
        Returns:
            PIL.Image: サムネイル画像
        """
        ext = os.path.splitext(file_path)[1].lower()
        if ext in constants.VIDEO_EXTS:
            return self._get_video_thumbnail(file_path)
        else:
            img = Image.open(file_path)
            img.thumbnail(constants.THUMBNAIL_SIZE)
            return img
    
    def _get_video_thumbnail(self, filepath):
        """
        動画ファイルの1フレーム目をサムネイル画像として取得
        
        Args:
            filepath: 動画ファイルのパス
            
        Returns:
            PIL.Image: サムネイル画像
        """
        try:
            import cv2
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
    
    def _update_selection_style(self, file, is_selected):
        """
        ファイルの選択状態に応じてスタイルを更新
        
        Args:
            file: ファイル名
            is_selected: 選択状態
        """
        if file in self.thumbnail_labels:
            style_name = "Selected.TLabel" if is_selected else "TLabel"
            self.thumbnail_labels[file].configure(style=style_name)
    
    # ===============================
    # イベントハンドラメソッド
    # ===============================
    
    def _on_thumbnail_click(self, event, file):
        """
        サムネイルがクリックされた時の処理
        - 選択状態を切り替え（選択/非選択）
        - 選択状態に応じてスタイルを変更
        - 選択状態は ThumbnailDisplayManager で管理
        """
        self.toggle_selection(file)

    def _on_thumbnail_double_click(self,event, path, file):
        """
        ダブルクリック時の処理
        - ファイルをデフォルトアプリケーションで開く
        - 選択状態を解除
        """
        self.open_with_default_app(path, file)
        self.remove_from_selection(file)
    
    def _on_thumbnail_right_click(self, event):
        """
        右クリック時の処理
        - 右クリックメニューを表示
        - メニュー項目は ThumbnailDisplayManager で管理
        """
        selected_items = self.get_selected_items()
        if not selected_items:
            messagebox.showinfo(messagebox.INFO, "選択されているファイルがありません")
            return
        
        if self.on_right_click_callback:
            self.on_right_click_callback(event)