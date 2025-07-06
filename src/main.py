import os
import json
import logic
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

import constants
from update_tag_menu import SubMenu 
from tag_button_manager import TagButtonManager
from date_range_manager import DateRangeManager 
from thumbnail_display_manager import ThumbnailDisplayManager 


class ThumbnailApp(tk.Tk):

    # アプリケーションの初期化
    def __init__(self, folder_path=None):
        super().__init__()        

        self.select_folder = folder_path

        self.title("画像・動画サムネイルビューア")
        self.geometry("900x700")

        self.all_tags = {} # タグ情報を管理するdict タグ名: タグの出現回数
        self.image_tag_map = {} # メディアファイルのタグ情報管理: Json対応
        
        # サムネイル表示関連
        self._thumbnail_cache = {}  # サムネイルキャッシュ
        self.scrollbar_visible = False
        self._last_size = (self.winfo_width(), self.winfo_height()) # ウィンドウサイズの初期値

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

        # show_thumbnailsは新しいクラスで管理するため、ラッパーメソッドを作成
        self.show_thumbnails = self._show_thumbnails_wrapper

        # メディアファイルのタグ情報とタグ一覧を取得
        self.image_tag_map, self.all_tags = logic.scan_tags(self.select_folder)

        # タグボタン管理クラスの初期化
        self.tag_button_manager = TagButtonManager(
            tag_frame=self.tag_frame,
            all_tags=self.all_tags,
            on_tag_toggle_callback=self.on_tag_toggle
        )

        # 日付範囲管理クラスの初期化（画像データから自動で日付範囲を設定）
        self.date_range_manager = DateRangeManager(
            parent_frame=self,
            image_tag_map=self.image_tag_map,
            on_date_change_callback=self.on_date_change
        )

        
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

        # サムネイル表示管理クラスの初期化
        self.thumbnail_display_manager = ThumbnailDisplayManager(
            parent_frame=self.image_frame,
            select_folder=self.select_folder,
            thumbnail_cache=self._thumbnail_cache,
            on_thumbnail_click_callback=self.on_thumbnail_click,
            on_thumbnail_double_click_callback=self.open_with_default_app,
            on_right_click_callback=self.on_main_frame_right_click
        )

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

        # サイズ変更時に同様の処理が発生しているため、初期表示時は遅延実行しない
        # print("__init__","show_thumbnails")
        # self.after_idle(self.show_thumbnails)  # 初期表示時は遅延実行


    # 日付変更イベントのバインド
    def on_date_change(self):
        """
        日付が変更された時の処理
        選択された日付範囲に基づいてサムネイルを再表示
        """
        self.show_thumbnails()


    # タグの選択状態が変更された時の処理
    def on_tag_toggle(self, tag=None):
        """
        タグの選択状態が変更された時の処理
        - 選択されたタグに基づいてサムネイルを再表示
        - thumbnail_display_managerのshow_thumbnailsメソッドを呼び出す
        """
        
        self.thumbnail_display_manager.clear_selection()
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
        - 選択状態は ThumbnailDisplayManager で管理
        """
        self.thumbnail_display_manager.toggle_selection(path)


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
            selected_items = self.thumbnail_display_manager.get_selected_items()
            if messagebox.askyesno(messagebox.YESNO, f"{update_tags}のタグで\n{len(selected_items)}件の選択した写真を更新しますか？"):
                for fname in selected_items:
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
                
                self.thumbnail_display_manager.clear_selection()
                self.image_tag_map, self.all_tags = logic.scan_tags(self.select_folder)  # タグマップを再読み込み
                self.tag_button_manager.update_tag_counts(self.all_tags)

                for tag in self.tag_button_manager.get_selected_tags():

                    # タグが存在する場合は前の選択状態を維持する
                    if tag in self.tag_button_manager.check_vars:
                        self.tag_button_manager.set_tag_selection(tag, True)

                    # 写真タグの更新により、未使用のタグが存在する場合は選択を解除する
                    else:
                        pass
                        # self.selected_tags.remove(tag)
 
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
            self.thumbnail_display_manager.remove_from_selection(file)
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
        selected_items = self.thumbnail_display_manager.get_selected_items()
        if not selected_items:
            messagebox.showinfo(messagebox.INFO, "選択されているファイルがありません")
            return

        self.tag_menu = SubMenu(self, event.x_root, event.y_root, list(self.all_tags.keys()), self.on_tag_menu_close)
        self.tag_menu.transient(self)
        self.tag_menu.grab_set()
        self.tag_menu.focus_set()
        self.tag_menu.protocol("WM_DELETE_WINDOW", self.on_tag_menu_close)


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
