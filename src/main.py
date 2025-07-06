import os
import json
import logic
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

import constants
from components.update_tag_menu import SubMenu 
from components.tag_button_manager import TagButtonManager
from components.date_range_manager import DateRangeManager 
from components.thumbnail_display_manager import ThumbnailDisplayManager 


class ThumbnailApp(tk.Tk):
    """
    画像・動画サムネイルビューアのメインアプリケーション
    """

    def __init__(self, folder_path=None):
        """
        アプリケーションの初期化
        
        Args:
            folder_path: 選択されたフォルダパス
        """
        super().__init__()        

        self.select_folder = folder_path
        self.title("画像・動画サムネイルビューア")
        self.geometry("900x700")

        # データ管理
        self.all_tags = {}  # タグ情報を管理するdict タグ名: タグの出現回数
        self.image_tag_map = {}  # メディアファイルのタグ情報管理: Json対応
        
        # UI状態管理
        self._thumbnail_cache = {}  # サムネイルキャッシュ
        self.scrollbar_visible = False
        self._last_size = (self.winfo_width(), self.winfo_height())  # ウィンドウサイズの初期値
        self.tag_menu = None  # タグメニューの参照

        # UI初期化
        self._setup_ui()
        
        # データ初期化
        self._initialize_data()

    # ===============================
    # 初期化・セットアップメソッド
    # ===============================

    def _clear_ui(self):
        """既存のUIコンポーネントをクリア"""
        # すべての子ウィジェットを削除
        for widget in self.winfo_children():
            widget.destroy()
        
        # キャッシュやマネージャーの参照をクリア
        self._thumbnail_cache.clear()

    def _setup_ui(self):
        """UIコンポーネントのセットアップ"""
        self._setup_tag_area()
        self._setup_thumbnail_area()
        self._setup_event_bindings()

    def _setup_tag_area(self):
        """タグエリアのセットアップ"""
        # 横スクロール可能な tag_frame を作成
        canvas_tags = tk.Canvas(self, height=100)
        canvas_tags.pack(side="top", fill="x", padx=10, pady=5)

        # 横スクロールバーを作成
        x_scroll_tags = ttk.Scrollbar(self, orient="horizontal", command=canvas_tags.xview)
        canvas_tags.configure(xscrollcommand=x_scroll_tags.set)
        
        inner_frame = tk.Frame(canvas_tags)
        canvas_tags.create_window(0, 0, window=inner_frame, anchor="nw")

        
        # スクロール対象のフレームを Canvas に埋め込む
        self.tag_filedialog = tk.Frame(inner_frame)
        self.tag_filedialog.pack(fill="x", padx=10, pady=2)
        btn = ttk.Button(self.tag_filedialog, text="フォルダ選択", command=lambda: self.show_select_folder())
        btn.pack(side="left", padx=5, pady=2)

        self.tag_frame = tk.Frame(inner_frame)
        self.tag_frame.pack(fill="x", padx=10, pady=2)

        self.data_frame = tk.Frame(inner_frame)
        self.data_frame.pack(fill="x", padx=10, pady=2)
   


        # フレーム設定イベント
        def on_frame_configure(event):
            frame_width = self.tag_frame.winfo_reqwidth()
            canvas_width = canvas_tags.winfo_width()

            # スクロールが必要か判定
            if frame_width > canvas_width:
                x_scroll_tags.pack(side="top", fill="x", padx=10)
            else:
                x_scroll_tags.pack_forget()

            # スクロール範囲を更新
            canvas_tags.configure(scrollregion=canvas_tags.bbox("all"))

        self.tag_frame.bind("<Configure>", on_frame_configure)

    def _setup_thumbnail_area(self):
        """サムネイルエリアのセットアップ"""
        # サムネイル一覧（下部、縦スクロール）
        thumb_area = tk.Frame(self)
        thumb_area.pack(side="top", fill="both", expand=True)

        self.canvas_thumb = tk.Canvas(thumb_area)
        self.canvas_thumb.pack(side="left", fill="both", expand=True)
        h_scroll_thumb = ttk.Scrollbar(thumb_area, orient="vertical", command=self.canvas_thumb.yview)
        h_scroll_thumb.pack(side="right", fill="y")
        self.canvas_thumb.configure(yscrollcommand=h_scroll_thumb.set)

        self.image_frame = tk.Frame(self.canvas_thumb)
        self.canvas_thumb.create_window((0, 0), window=self.image_frame, anchor="nw")

        # フレーム設定イベント
        def on_image_frame_configure(event):
            frame_height = self.image_frame.winfo_reqheight()
            canvas_height = self.canvas_thumb.winfo_height()

            # スクロールが必要か判定
            if frame_height > canvas_height:
                # スクロール範囲を更新
                self.canvas_thumb.configure(scrollregion=self.canvas_thumb.bbox("all"))
                h_scroll_thumb.pack(side="right", fill="y", padx=10)
                self.scrollbar_visible = True
            else:
                h_scroll_thumb.pack_forget()
                self.scrollbar_visible = False

        self.image_frame.bind("<Configure>", on_image_frame_configure)

    def _setup_event_bindings(self):
        """イベントバインディングのセットアップ"""
        # マウスホイールスクロール対応
        self.canvas_thumb.bind_all("<MouseWheel>", self._on_mousewheel)  # Windows
        self.canvas_thumb.bind_all("<Button-4>", self._on_mousewheel)    # Linux
        self.canvas_thumb.bind_all("<Button-5>", self._on_mousewheel)    # Linux

        # ウィンドウリサイズイベント
        self.bind("<Configure>", self._on_window_resize)

    def _initialize_data(self):
        """データとマネージャークラスの初期化"""
        # メディアファイルのタグ情報とタグ一覧を取得
        self.image_tag_map, self.all_tags = logic.scan_tags(self.select_folder)

        if not self.image_tag_map:
            messagebox.showinfo(messagebox.INFO, "選択されたフォルダには画像・動画が含まれていません。")
        
        # タグボタン管理クラスの初期化
        self.tag_button_manager = TagButtonManager(
            tag_frame=self.tag_frame,
            all_tags=self.all_tags,
            on_tag_toggle_callback=self._show_thumbnails_wrapper
        )

        # 日付範囲管理クラスの初期化
        self.date_range_manager = DateRangeManager(
            parent_frame=self.data_frame,
            image_tag_map=self.image_tag_map,
            on_date_change_callback=self._show_thumbnails_wrapper
        )

        # サムネイル表示管理クラスの初期化
        self.thumbnail_display_manager = ThumbnailDisplayManager(
            parent_frame=self.image_frame,
            select_folder=self.select_folder,
            thumbnail_cache=self._thumbnail_cache,
            on_right_click_callback=self.on_main_frame_right_click
        )

        # show_thumbnailsラッパーメソッドを設定
        self.show_thumbnails = self._show_thumbnails_wrapper

    # ===============================
    # 公開メソッド（外部インターフェース）
    # ===============================

    def _show_thumbnails_wrapper(self):
        """
        サムネイル表示のラッパーメソッド
        ThumbnailDisplayManagerを使用してサムネイルを表示
        """
        selected_tags = self.tag_button_manager.get_selected_tags()
        date_range = self.date_range_manager.get_date_range()
        frame_width = self.winfo_width()
        
        self.thumbnail_display_manager.show_thumbnails(
            image_tag_map=self.image_tag_map,
            date_range=date_range,
            selected_tags=selected_tags,
            frame_width=frame_width
        )

    # ===============================
    # イベントハンドラメソッド
    # ===============================

    def _on_window_resize(self, event):
        """
        ウィンドウサイズが変更された時の処理
        - 新しいサイズを記録
        - サイズが変更された場合、サムネイルを再配置
        """
        if event.widget == self:
            new_size = (self.winfo_width(), self.winfo_height())
            if new_size != self._last_size:
                self._last_size = new_size
                self.after_idle(self.show_thumbnails)

    def _on_mousewheel(self, event):
        """マウスホイールのスクロール処理"""
        if self.scrollbar_visible:
            if event.num == 4:
                self.canvas_thumb.yview_scroll(-1, "units")
            elif event.num == 5:
                self.canvas_thumb.yview_scroll(1, "units")
            elif hasattr(event, 'delta'):
                if event.delta > 0:
                    self.canvas_thumb.yview_scroll(-1, "units")
                else:
                    self.canvas_thumb.yview_scroll(1, "units")

    def on_main_frame_right_click(self, event):
        """
        メインフレームで右クリックされた時の処理
        - タグ編集メニューを表示
        """
        self.tag_menu = SubMenu(self, event.x_root, event.y_root, list(self.all_tags.keys()), self.on_tag_menu_close)
        self.tag_menu.transient(self)
        self.tag_menu.grab_set()
        self.tag_menu.focus_set()
        self.tag_menu.protocol("WM_DELETE_WINDOW", self.on_tag_menu_close)

    def on_tag_menu_close(self, update_tags=None):
        """
        タグ編集メニューが閉じられた時の処理
        - タグの更新が選択された場合：
          - 選択されたファイルのタグを更新
          - タグ一覧を再読み込み
          - サムネイルを再表示
        - 更新がキャンセルされた場合：
          - メニューを閉じる
        """
        if update_tags:
            selected_items = self.thumbnail_display_manager.get_selected_items()
            if messagebox.askyesno(messagebox.YESNO, f"{update_tags}のタグで\n{len(selected_items)}件の選択した写真を更新しますか？"):
                # タグの更新処理
                for fname in selected_items:
                    self.image_tag_map[fname]["tags"] = update_tags
                
                # ファイルへの保存
                try:
                    if self.select_folder and constants.PICTURE_TAGS_JSON:
                        json_path = os.path.join(self.select_folder, constants.PICTURE_TAGS_JSON)
                        with open(json_path, "w", encoding="utf-8") as f:
                            json.dump(self.image_tag_map, f, ensure_ascii=False, indent=4)
                    else:
                        print("フォルダまたはPICTURE_TAGS_JSONが設定されていません。")
                        return
                except Exception as e:
                    print(f"タグマップの保存に失敗しました: {e}")
                    return
                
                # UI更新処理
                self.image_tag_map, self.all_tags = logic.scan_tags(self.select_folder)
                self.tag_button_manager.update_tag_counts(self.all_tags)

                # 選択状態の復元
                for tag in self.tag_button_manager.get_selected_tags():
                    if tag in self.tag_button_manager.check_vars:
                        self.tag_button_manager.set_tag_selection(tag, True)
 
                self.show_thumbnails()
                self.canvas_thumb.yview_moveto(0)
            else:
                messagebox.showinfo(messagebox.INFO, "更新はキャンセルされました")
                return

        if self.tag_menu is not None:
            self.tag_menu.destroy()
            self.tag_menu = None


    def show_select_folder(self):
        """
        フォルダ選択ダイアログを表示し、選択されたフォルダのパスを更新
        """
        select_folder = filedialog.askdirectory(
            title="画像・動画が含まれているフォルダを選択",
        )

        if select_folder:
            self.select_folder = select_folder
            self._clear_ui()  # 既存のUIをクリア
            self._setup_ui()
            self._initialize_data()
            self.show_thumbnails()
        else:
            pass  # フォルダが選択されなかった場合は何もしない


def main():
    """
    アプリケーションのエントリーポイント
    """
    # フォルダ選択ダイアログを表示
    selectFolder = filedialog.askdirectory(
        title="画像・動画が含まれているフォルダを選択",
    )

    if selectFolder:
        app = ThumbnailApp(selectFolder)
        app.mainloop()
    else:
        messagebox.showinfo(messagebox.INFO, "フォルダが選択されませんでした。アプリケーションを終了します。")
        exit(0)


if __name__ == "__main__":
    main()
