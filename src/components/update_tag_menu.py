import tkinter as tk
from tkinter import messagebox

class SubMenu(tk.Toplevel):

    def __init__(self, master, x, y, all_tags, on_close=None):
        super().__init__(master)
        self.title("タグ更新メニュー")
        self.geometry(f"200x300+{x}+{y}")
        self.all_tags = all_tags.copy()
        self.on_close = on_close

        self.selected_tags = set() #写真を更新するタグ

        label = tk.Label(self, text="新規タグを入力し追加してください")
        label.pack(pady=5)

        # 新規タグ入力用のフレーム
        input_frame = tk.Frame(self)
        input_frame.pack(fill="x", padx=10, pady=5)
        self.tag_entry = tk.Entry(input_frame)
        self.tag_entry.pack(side="left", fill="x", expand=True)
        
        # テキストボックスの内容変更を監視
        self.tag_entry.bind('<KeyRelease>', self.on_entry_change)

        # 新規タグの追加ボタン
        self.add_btn = tk.Button(input_frame, text="追加", command=self.add_tag, state="disabled")
        self.add_btn.pack(side="right", padx=(5, 0))

        frame = tk.Frame(self)
        frame.pack(fill="x", padx=10, pady=5)

        # タグ一覧を表示するリストボックス
        self.listbox = tk.Listbox(frame, selectmode="multiple")
        self.listbox.pack(side="left", fill="both", expand=True)

        frame_btn = tk.Frame(self)
        frame_btn.pack(anchor="center")
        
        # タグの更新用のボタン
        self.btn_ok = tk.Button(frame_btn, text="選択したタグで更新", command=self.save_tags, state="disabled")
        self.btn_ok.pack(side="left", padx=(0, 10))

        # キャンセルボタン
        btn_cancel = tk.Button(frame_btn, text="キャンセル", command=self.destroy)
        btn_cancel.pack(side="left")
    
        # スクロールバーの作成
        scrollbar = tk.Scrollbar(frame, orient="vertical", command=self.listbox.yview)
        scrollbar.pack(side="right", fill="y")
        
        for item in self.all_tags:
            self.listbox.insert(tk.END, item)

        self.listbox.configure(yscrollcommand=scrollbar.set)
        
        # リストボックスの選択状態変更を監視
        self.listbox.bind('<<ListboxSelect>>', self.on_selection_change)

    def add_tag(self):
        new_tag = self.tag_entry.get().strip()
        # リストボックス内での重複もチェック
        existing_tags = [self.listbox.get(i) for i in range(self.listbox.size())]
        
        # リストボックスにも含まれていないタグを追加
        if new_tag in self.all_tags or new_tag in existing_tags:
            messagebox.showwarning(messagebox.WARNING, "既に存在するタグです。")
            return
        self.listbox.insert(0, new_tag)
        self.tag_entry.delete(0, tk.END)
        self.listbox.selection_set(0)
        # 新しいタグが選択されたのでOKボタンを有効化
        self.btn_ok.config(state="normal")
        # テキストボックスが空になったので追加ボタンを無効化
        self.add_btn.config(state="disabled")

    def save_tags(self):
        selected_indices = self.listbox.curselection()
        selected_tags = [self.listbox.get(i) for i in selected_indices]

        if self.on_close:
            self.on_close(selected_tags)
            self.on_close = None
        super().destroy()

    def on_selection_change(self, event):
        """リストボックスの選択状態が変更された時の処理"""
        selected_indices = self.listbox.curselection()
        if selected_indices:
            self.btn_ok.config(state="normal")
        else:
            self.btn_ok.config(state="disabled")

    def on_entry_change(self, event):
        """テキストボックスの内容が変更された時の処理"""
        text = self.tag_entry.get().strip()
        if text:
            self.add_btn.config(state="normal")
        else:
            self.add_btn.config(state="disabled")


# if __name__ == "__main__":
#     root = tk.Tk()
#     app = DummyMenu(root, 100, 100, {"タグ1", "タグ2", "タグ3"})
#     root.mainloop()