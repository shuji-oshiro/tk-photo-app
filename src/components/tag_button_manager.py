# --- タグボタン管理クラス ---
# タグボタンの作成・配置・状態管理を担当

import tkinter as tk
from tkinter import ttk
import constants


class TagButtonManager:
    """
    タグボタンを作成し、画面上部に配置・管理するクラス
    """
    
    def __init__(self, tag_frame, all_tags, on_tag_toggle_callback=None):
        """
        初期化
        
        Args:
            tag_frame: タグボタンを配置するフレーム（tkinter.Frame）
            all_tags: 全タグの辞書（タグ名: カウント）
            on_tag_toggle_callback: タグトグル時のコールバック関数
        """
        self.tag_frame = tag_frame
        self.all_tags = all_tags
        self.on_tag_toggle_callback = on_tag_toggle_callback
        self.check_vars = {}
        self.create_tag_buttons()

    def create_tag_buttons(self):
        """
        タグ一覧からトグルボタン（Checkbutton）を作成し、画面上部に並べる
        """
        # 既存のタグボタンを削除
        self._clear_existing_buttons()
        
        # タグフレームの初期化 
        self.check_vars = {}
        
        # タグフレームの最初の行に「タグなし」のボタンを配置
        self._create_none_tag_button()
        
        # 各タグのボタンを作成
        self._create_tag_buttons()
        
        # タグフレームのレイアウトを更新し、ウィジェットの配置を確定させる
        self.tag_frame.update_idletasks()
    
    def _clear_existing_buttons(self):
        """既存のタグボタンを削除"""
        for widget in self.tag_frame.winfo_children():
            widget.destroy()
    
    def _create_none_tag_button(self):
        """「タグなし」ボタンを作成"""
        var = tk.BooleanVar()
        btn = ttk.Checkbutton(
            self.tag_frame, 
            text=constants.NONE_TAG_TEXT, 
            variable=var, 
            command=lambda: self._on_tag_toggle()
        )
        btn.grid(row=0, column=0, padx=5, pady=2, sticky="w")
        self.check_vars[constants.NONE_TAG_TEXT] = var
    
    def _create_tag_buttons(self):
        """各タグのボタンを作成"""
        col = 1
        for tag, cnt in self.all_tags.items():
            var = tk.BooleanVar()
            btn = ttk.Checkbutton(
                self.tag_frame, 
                text=f"{tag} ({cnt})", 
                variable=var, 
                command=lambda t=tag: self._on_tag_toggle(t)
            )
            btn.grid(row=0, column=col, padx=5, pady=2, sticky="w")
            self.check_vars[tag] = var
            col += 1
    
    def _on_tag_toggle(self, tag=None):
        """
        タグの選択状態が変更された時の処理
        - タグなしと他のタグは排他的に動作
        - タグなしが選択された場合、他のタグを全て解除
        - 他のタグが選択された場合、タグなしを解除
        - コールバック関数を呼び出す
        """

        if tag is None:
            # 他のタグを全て解除
            for _tag in self.check_vars.keys():
                if _tag != constants.NONE_TAG_TEXT:
                    self.set_tag_selection(_tag, False)
        else:
            # 他のタグが選択された場合、タグなしを解除
            self.set_tag_selection(constants.NONE_TAG_TEXT, False)


        if self.on_tag_toggle_callback:
            self.on_tag_toggle_callback(tag)
    
    def get_selected_tags(self):
        """
        選択中のタグリストを取得
        
        Returns:
            list: 選択中のタグ名のリスト
        """
        selected_tags = []
        for tag, var in self.check_vars.items():
            if var.get():
                selected_tags.append(tag)
        return selected_tags
    
    # まだ呼び出しされていないメソッド
    # ここでの実装は、全てのタグ選択を解除する
    def clear_selection(self):
        """全てのタグ選択を解除"""
        for var in self.check_vars.values():
            var.set(False)
    
    def set_tag_selection(self, tag, selected):
        """
        指定したタグの選択状態を設定
        
        Args:
            tag: タグ名
            selected: 選択状態（True/False）
        """
        if tag in self.check_vars:
            self.check_vars[tag].set(selected)
    
    def update_tag_counts(self, new_all_tags):
        """
        タグの件数を更新して再描画
        
        Args:
            new_all_tags: 新しい全タグの辞書（タグ名: カウント）
        """
        self.all_tags = new_all_tags
        self.create_tag_buttons()
