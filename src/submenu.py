import tkinter as tk

class SubMenu(tk.Toplevel):

    def __init__(self, master, x, y, all_tags, on_close=None):
        super().__init__(master)
        self.title("タグ更新メニュー")
        self.geometry(f"200x300+{x}+{y}")
        self.all_tags = all_tags.copy()
        self.on_close = on_close

        self.selected_tags = set() #写真を更新するタグ

        btn_ok = tk.Button(self, text="タグの更新", command=self.save_tags)
        btn_ok.pack(pady=5)
        # タグ入力用のフレーム
        input_frame = tk.Frame(self)
        input_frame.pack(fill="x", padx=10, pady=5)
        self.tag_entry = tk.Entry(input_frame)
        self.tag_entry.pack(side="left", fill="x", expand=True)

        add_btn = tk.Button(input_frame, text="追加", command=self.add_tag)
        add_btn.pack(side="right", padx=(5, 0))

        frame = tk.Frame(self)
        frame.pack(fill="x", padx=10, pady=5)

        self.listbox = tk.Listbox(frame, selectmode="multiple")
        self.listbox.pack(side="left", fill="both", expand=True)

        # スクロールバーの作成
        scrollbar = tk.Scrollbar(frame, orient="vertical", command=self.listbox.yview)
        scrollbar.pack(side="right", fill="y")
        
        # マウスホイールスクロール対応
        # self.listbox.bind_all("<MouseWheel>", self.on_mousewheel)  # Windows
        # self.listbox.bind_all("<Button-4>", self.on_mousewheel)    # Linux
        # self.listbox.bind_all("<Button-5>", self.on_mousewheel)    # Linux

        for item in self.all_tags:
            self.listbox.insert(tk.END, item)

        self.listbox.configure(yscrollcommand=scrollbar.set)

    # def on_mousewheel(self, event):
    #     if event.num == 4:
    #         self.listbox.yview_scroll(-1, "units")
    #     elif event.num == 5:
    #         self.listbox.yview_scroll(1, "units")
    #     elif hasattr(event, 'delta'):
    #         if event.delta > 0:
    #             self.listbox.yview_scroll(-1, "units")
    #         else:
    #             self.listbox.yview_scroll(1, "units")

    def add_tag(self):
        new_tag = self.tag_entry.get().strip()
        if new_tag and new_tag not in self.all_tags:
            self.listbox.insert(0, new_tag)
            # self.all_tags.add(new_tag)
            self.tag_entry.delete(0, tk.END)
            self.listbox.selection_set(0)

    def save_tags(self):
        selected_indices = self.listbox.curselection()
        selected_tags = [self.listbox.get(i) for i in selected_indices]

        if self.on_close:
            self.on_close(selected_tags)
            self.on_close = None
        super().destroy()


# if __name__ == "__main__":
#     root = tk.Tk()
#     app = DummyMenu(root, 100, 100, {"タグ1", "タグ2", "タグ3"})
#     root.mainloop()