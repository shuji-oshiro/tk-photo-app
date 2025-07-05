import os
import glob
import json
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from PIL import Image, ImageTk
from dotenv import load_dotenv
import numpy as np
from functools import partial
from submenu import SubMenu  # サブメニューをインポート 
import datetime
from tkcalendar import DateEntry  # 追加
import types
import logic
import constants  # 定数をインポート


load_dotenv()

class ThumbnailApp(tk.Tk):

    def __init__(self, folder_path=None):
        super().__init__()        

        self.select_folder = folder_path

        self.title("画像・動画サムネイルビューア")
        self.geometry("900x700")

        self.all_tags = {} # タグ情報を管理するdict タグ名: タグの出現回数
        self.image_tag_map = {} # メディアファイルのタグ情報管理: Json対応

        self.check_vars = {}  # タグフレーム：上部ツールバーに表示されるタグチェックボックス: tk.BooleanVar
        self.thumbnails = []  # 参照保持用
        self.min_thumb_width = constants.THUMBNAIL_SIZE[0] + 20  # サムネイル1件分の最小幅（パディング込み）
        self.current_columns = 1  # 画面に表示されるカラム数　特に使用はしていない　
        self._last_size = (self.winfo_width(), self.winfo_height()) # ウィンドウサイズの初期値
        self.selected_items = set()  # 選択中のファイル
        self.selected_tags = []  # 選択中のタグ

        self._thumbnail_cache = {}  # サムネイルキャッシュ
        self.thumbnail_labels = {}  # サムネイルラベル保持
        self.scrollbar_visible = False

        # --- 横スクロール可能な tag_frame を作成 ---
        canvas_tags = tk.Canvas(self, height=30)
        canvas_tags.pack(side="top", fill="x", padx=10, pady=5)
        x_scroll_tags = ttk.Scrollbar(self, orient="horizontal", command=canvas_tags.xview)
        # h_scroll.pack(side="top", fill="x", padx=10)
        canvas_tags.configure(xscrollcommand=x_scroll_tags.set)
        # スクロール対象のフレームを Canvas に埋め込む
        self.tag_frame = tk.Frame(canvas_tags)
        
        canvas_tags.create_window((0, 0), window=self.tag_frame, anchor="nw")

        # マウスホイールスクロール対応
        def on_frame_configure(event):
        # tag_frameのサイズ
            frame_width = self.tag_frame.winfo_reqwidth()
            # canvasの表示幅
            canvas_width = canvas_tags.winfo_width()

            # スクロールが必要か判定
            if frame_width > canvas_width:
                x_scroll_tags.pack(side="top", fill="x", padx=10)  # スクロールバーを表示
            else:
                x_scroll_tags.pack_forget()  # スクロールバーを非表示

            # スクロール範囲を更新
            canvas_tags.configure(scrollregion=canvas_tags.bbox("all"))

        self.tag_frame.bind("<Configure>",on_frame_configure)


        # 日付入力コントロール
        self.date_frame = ttk.Frame(self)
        self.date_frame.pack(side="top", fill="x", padx=10, pady=2)
        ttk.Label(self.date_frame, text="FROM").pack(side="left")
        self.from_date_entry = DateEntry(self.date_frame, width=12, date_pattern='yyyy-mm-dd')
        self.from_date_entry.pack(side="left", padx=(0, 10))
        
        self.from_date_entry.bind("<<DateEntrySelected>>", self.on_date_change)
        self.from_date_entry.bind("<FocusOut>", self.on_date_change)
        ttk.Label(self.date_frame, text="TO").pack(side="left")
        self.to_date_entry = DateEntry(self.date_frame, width=12, date_pattern='yyyy-mm-dd')
        self.to_date_entry.pack(side="left")
        self.to_date_entry.bind("<<DateEntrySelected>>", self.on_date_change)
        self.to_date_entry.bind("<FocusOut>", self.on_date_change)

        # サムネイル一覧（下部、縦スクロール）
        # 1. ラッパー用のフレームを作成
        thumb_area = tk.Frame(self)
        thumb_area.pack(side="top", fill="both", expand=True)


        self.canvas_thumb = tk.Canvas(thumb_area)
        self.canvas_thumb.pack(side="left", fill="both", expand=True)
        h_scroll_thumb = ttk.Scrollbar(thumb_area, orient="vertical", command=self.canvas_thumb.yview)
        h_scroll_thumb.pack(side="right", fill="y")
        self.canvas_thumb.configure(yscrollcommand=h_scroll_thumb.set)

        
        self.image_frame = tk.Frame(self.canvas_thumb)
        self.canvas_thumb.create_window((0, 0), window=self.image_frame, anchor="nw")

        # 2. canvasのサイズ変更時にスクロール範囲を更新する
        def on_image_frame_configure(event):
            # tag_frameのサイズ
            frame_height = self.image_frame.winfo_reqheight()
            # canvasの表示幅
            canvas_height = self.canvas_thumb.winfo_height()

            # スクロールが必要か判定
            if frame_height > canvas_height:
                # スクロール範囲を更新
                self.canvas_thumb.configure(scrollregion=self.canvas_thumb.bbox("all"))
                h_scroll_thumb.pack(side="right", fill="y", padx=10)  # スクロールバーを表示
                self.scrollbar_visible = True
            else:
                h_scroll_thumb.pack_forget()  # スクロールバーを非表示
                self.scrollbar_visible = False

        # スクロール範囲を更新
        self.image_frame.bind("<Configure>",on_image_frame_configure)


        # マウスホイールスクロール対応
        self.canvas_thumb.bind_all("<MouseWheel>", self.on_mousewheel)  # Windows
        self.canvas_thumb.bind_all("<Button-4>", self.on_mousewheel)    # Linux
        self.canvas_thumb.bind_all("<Button-5>", self.on_mousewheel)    # Linux

        self.bind("<Configure>", self.on_window_resize)


        self.scan_tags = types.MethodType(logic.scan_tags, self)
        self.get_video_thumbnail = types.MethodType(logic.get_video_thumbnail, self)
        self.create_tag_buttons = types.MethodType(logic.create_tag_buttons, self)
        self.show_thumbnails = types.MethodType(logic.show_thumbnails, self)

        # タグ編集メニューの初期化
        self.tag_menu = None

        self.scan_tags()
        self.create_tag_buttons()  

        # サイズ変更時に同様の処理が発生しているため、初期表示時は遅延実行しない
        # print("__init__","show_thumbnails")
        # self.after_idle(self.show_thumbnails)  # 初期表示時は遅延実行

        # サムネイルのcreatedayから最小・最大日付を取得
        createday_list = [
            datetime.datetime.strptime(self.image_tag_map[f]["createday"], "%Y-%m-%d %H:%M:%S")
            for f in self.image_tag_map
            if "createday" in self.image_tag_map[f]
        ]
        if createday_list:
            min_date = min(createday_list).date()
            max_date = max(createday_list).date()
        else:
            today = datetime.date.today()
            min_date = today
            max_date = today
        self.from_date_entry.set_date(min_date)
        self.to_date_entry.set_date(max_date)

    # 日付変更イベントのバインド
    def on_date_change(self, event=None):
        """
        日付が変更された時の処理
        選択された日付範囲に基づいてサムネイルを再表示
        """

        if self.from_date_entry.get_date() > self.to_date_entry.get_date():
            self.to_date_entry.set_date(self.from_date_entry.get_date())
            messagebox.showinfo(messagebox.INFO, "FROMの日付がTOの日付より新しい日付を選択してください")
            return

        print("on_date_change","show_thumbnails")
        self.show_thumbnails()


    # タグの選択状態が変更された時の処理
    def on_tag_toggle(self, tag=None):
        """
        タグの選択状態が変更された時の処理
        - タグなしと他のタグは排他的に動作
        - タグなしが選択された場合、他のタグを全て解除
        - 他のタグが選択された場合、タグなしを解除
        - 選択状態に基づいてサムネイルを再表示
        """

        if tag is None:
            # 他のタグを全て解除
            for _tag in self.check_vars.keys():
                if _tag != constants.NONE_TAG_TEXT:
                    self.check_vars[_tag].set(False)
        else:
            # 他のタグが選択された場合、タグなしを解除
            self.check_vars[constants.NONE_TAG_TEXT].set(False)

        self.selected_tags = [tag for tag, var in self.check_vars.items() if var.get()]
        self.selected_items.clear()
        print("on_tag_toggle","show_thumbnails")
        self.show_thumbnails()
 

    # ウィンドウサイズが変更された時の処理
    def on_window_resize(self, event):
        """
        ウィンドウサイズが変更された時の処理
        - 新しいサイズを記録
        - サイズが変更された場合、サムネイルを再配置
        """
        if event.widget == self:
            new_size = (self.winfo_width(), self.winfo_height())
            if new_size != self._last_size:
                self._last_size = new_size

                print("on_window_resize","show_thumbnails")
                self.after_idle(self.show_thumbnails)


    # マウスホイールのスクロール処理
    def on_mousewheel(self, event):
        # マウスホイールの上下方向のスクロール
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

    # サムネイルクリック時の処理
    def on_thumbnail_click(self, event, path):
        """
        サムネイルがクリックされた時の処理
        - 選択状態を切り替え（選択/非選択）
        - 選択状態に応じてスタイルを変更
        - 選択状態は self.selected_items で管理
        """
        if path in self.selected_items:
            self.selected_items.remove(path)
            style_name = "TLabel"
        else:
            self.selected_items.add(path)
            style_name = "Selected.TLabel"
        if path in self.thumbnail_labels:
            self.thumbnail_labels[path].configure(style=style_name)

    # タグ登録メニューが閉じたときの処理
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
            if messagebox.askyesno(messagebox.YESNO, f"{update_tags}のタグで\n{len(self.selected_items)}件の選択した写真を更新しますか？"):
                for fname in self.selected_items:
                    self.image_tag_map[fname]["tags"] = update_tags
                
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
                
                self.selected_items.clear()
                self.scan_tags()
                self.create_tag_buttons()

                for tag in self.selected_tags:

                    # タグが存在する場合は前の選択状態を維持する
                    if tag in self.check_vars:
                        self.check_vars[tag].set(True)

                    # 写真タグの更新により、未使用のタグが存在する場合は選択を解除する
                    else:
                        self.selected_tags.remove(tag)
 
                self.show_thumbnails()
                self.canvas_thumb.yview_moveto(0)
            else:
                messagebox.showinfo(messagebox.INFO, "更新はキャンセルされました")
                return

        if self.tag_menu is not None:
            self.tag_menu.destroy()


    # 画像・動画をWindows標準アプリで開く
    def open_with_default_app(self, event, path, file):
        """
        ファイルをデフォルトアプリケーションで開く処理
        - 指定されたパスのファイルを開く
        - ダブルクリック時はサムネイルの選択を解除
        - エラー発生時はエラーメッセージを表示
        """
        try:
            os.startfile(path)
            self.selected_items.remove(file)
            style_name = "TLabel"
            if file in self.thumbnail_labels:
                self.thumbnail_labels[file].configure(style=style_name)
        except Exception as e:
            print(f"{path} のオープンに失敗: {e}")


    # メインフレームで右クリックされた時の処理
    def on_main_frame_right_click(self, event):
        """
        メインフレームで右クリックされた時の処理
        - 選択されたファイルがある場合：
          - タグ編集メニューを表示
          - メニューをモーダルとして表示
        - 選択されたファイルがない場合：
          - ファイルを選択するよう促すメッセージを表示
        """
        if not self.selected_items:
            messagebox.showinfo(messagebox.INFO, "選択されているファイルがありません")
            return

        self.tag_menu = SubMenu(self, event.x_root, event.y_root, list(self.all_tags.keys()), self.on_tag_menu_close)
        self.tag_menu.transient(self)
        self.tag_menu.grab_set()
        self.tag_menu.focus_set()
        self.tag_menu.protocol("WM_DELETE_WINDOW", self.on_tag_menu_close)

# タグ編集メニューの選択状態を更新
def main():

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
