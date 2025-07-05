# --- 日付範囲管理クラス ---
# 日付範囲の選択・検証・変更通知を担当

import datetime
import tkinter as tk
from tkinter import ttk, messagebox


class DateRangeManager:
    """
    日付範囲の選択と管理を行うクラス
    """

    
    def __init__(self, parent_frame, image_tag_map=None, on_date_change_callback=None):
        """
        初期化
        
        Args:
            parent_frame: 日付コントロールを配置するフレーム
            image_tag_map: 画像タグマップ辞書（指定時は自動で日付範囲を設定）
            on_date_change_callback: 日付変更時のコールバック関数
        """
        self.parent_frame = parent_frame
        self.on_date_change_callback = on_date_change_callback
        self.image_tag_map = image_tag_map or {}

        # 日付入力コントロールフレームを作成
        self.date_frame = ttk.Frame(self.parent_frame)
        self.date_frame.pack(side="top", fill="x", padx=10, pady=2)
        
        self._create_date_controls()
        
        # ウィジェットの更新を強制実行
        self.parent_frame.update_idletasks()
        
        # 画像データが指定されている場合は日付範囲を自動設定
        if self.image_tag_map:
            self.set_date_range_from_image_data(self.image_tag_map)

    def _create_date_controls(self):
        """日付入力コントロールを作成"""
        # ラベル
        ttk.Label(self.date_frame, text="抽出期間：").pack(side="left")
        
        # 開始日フレーム
        from_frame = ttk.Frame(self.date_frame)
        from_frame.pack(side="left", padx=(5, 5))
        
        self.from_year_var = tk.StringVar()
        self.from_month_var = tk.StringVar()
        self.from_day_var = tk.StringVar()
        
        # 年
        self.from_year_combo = ttk.Combobox(from_frame, textvariable=self.from_year_var, width=6, state="readonly")
        self.from_year_combo['values'] = [str(y) for y in range(2000, 2030)]
        self.from_year_combo.pack(side="left", padx=1)
        self.from_year_combo.bind('<<ComboboxSelected>>', self._on_date_change)
        
        # 月
        self.from_month_combo = ttk.Combobox(from_frame, textvariable=self.from_month_var, width=4, state="readonly")
        self.from_month_combo['values'] = [f"{m:02d}" for m in range(1, 13)]
        self.from_month_combo.pack(side="left", padx=1)
        self.from_month_combo.bind('<<ComboboxSelected>>', self._on_date_change)
        
        # 日
        self.from_day_combo = ttk.Combobox(from_frame, textvariable=self.from_day_var, width=4, state="readonly")
        self.from_day_combo['values'] = [f"{d:02d}" for d in range(1, 32)]
        self.from_day_combo.pack(side="left", padx=1)
        self.from_day_combo.bind('<<ComboboxSelected>>', self._on_date_change)
        
        # 区切り文字
        ttk.Label(self.date_frame, text="～").pack(side="left", padx=5)
        
        # 終了日フレーム
        to_frame = ttk.Frame(self.date_frame)
        to_frame.pack(side="left", padx=(5, 0))
        

        self.to_year_var = tk.StringVar()
        self.to_month_var = tk.StringVar()
        self.to_day_var = tk.StringVar()
        
        # 年
        self.to_year_combo = ttk.Combobox(to_frame, textvariable=self.to_year_var, width=6, state="readonly")
        self.to_year_combo['values'] = [str(y) for y in range(2000, 2030)]
        self.to_year_combo.pack(side="left", padx=1)
        self.to_year_combo.bind('<<ComboboxSelected>>', self._on_date_change)
        
        # 月
        self.to_month_combo = ttk.Combobox(to_frame, textvariable=self.to_month_var, width=4, state="readonly")
        self.to_month_combo['values'] = [f"{m:02d}" for m in range(1, 13)]
        self.to_month_combo.pack(side="left", padx=1)
        self.to_month_combo.bind('<<ComboboxSelected>>', self._on_date_change)
        
        # 日
        self.to_day_combo = ttk.Combobox(to_frame, textvariable=self.to_day_var, width=4, state="readonly")
        self.to_day_combo['values'] = [f"{d:02d}" for d in range(1, 32)]
        self.to_day_combo.pack(side="left", padx=1)
        self.to_day_combo.bind('<<ComboboxSelected>>', self._on_date_change)


        self.reset_btn = ttk.Button(self.date_frame, text="リセット", command=self.reset_date_range)
        self.reset_btn.pack(side="left", padx=(10, 0))
    
    def _on_date_change(self, event=None):
        """
        日付が変更された時の内部処理
        - 日付の妥当性をチェック
        - コールバック関数を呼び出し
        """
        try:
            from_date = self.get_from_date()
            to_date = self.get_to_date()
            
            # 開始日が終了日より後の場合は修正
            if from_date > to_date:
                self.set_to_date(from_date)
                messagebox.showinfo(
                    messagebox.INFO, 
                    "FROMの日付がTOの日付より新しい日付を選択してください"
                )
                return
        except ValueError:
            # 不正な日付の場合は何もしない
            return
        
        # コールバック関数を呼び出し
        if self.on_date_change_callback:
            self.on_date_change_callback()
    
    def get_date_range(self):
        """
        選択されている日付範囲を取得
        
        Returns:
            tuple: (開始日, 終了日) のタプル
        """
        return (
            self.get_from_date(),
            self.get_to_date()
        )
    
    def set_date_range(self, min_date, max_date):
        """
        日付範囲を設定
        
        Args:
            min_date: 最小日付
            max_date: 最大日付
        """
        self.set_from_date(min_date)
        self.set_to_date(max_date)
    
    def set_date_range_from_data(self, date_list):
        """
        データから日付範囲を自動設定
        
        Args:
            date_list: datetime オブジェクトのリスト
        """
        if date_list:
            min_date = min(date_list).date()
            max_date = max(date_list).date()
        else:
            today = datetime.date.today()
            min_date = today
            max_date = today
        
        self.set_date_range(min_date, max_date)
    
    def set_date_range_from_image_data(self, image_tag_map):
        """
        画像タグマップから日付範囲を自動設定
        
        Args:
            image_tag_map: 画像タグマップ辞書
        """
        import datetime
        
        createday_list = [
            datetime.datetime.strptime(image_tag_map[f]["createday"], "%Y-%m-%d %H:%M:%S")
            for f in image_tag_map
            if "createday" in image_tag_map[f]
        ]
        self.set_date_range_from_data(createday_list)
    
    def get_from_date(self):
        """開始日を取得"""
        try:
            year = int(self.from_year_var.get())
            month = int(self.from_month_var.get())
            day = int(self.from_day_var.get())
            return datetime.date(year, month, day)
        except (ValueError, TypeError):
            return datetime.date.today()
    
    def get_to_date(self):
        """終了日を取得"""
        try:
            year = int(self.to_year_var.get())
            month = int(self.to_month_var.get())
            day = int(self.to_day_var.get())
            return datetime.date(year, month, day)
        except (ValueError, TypeError):
            return datetime.date.today()
    
    def set_from_date(self, date_obj):
        """開始日を設定"""
        self.from_year_var.set(str(date_obj.year))
        self.from_month_var.set(f"{date_obj.month:02d}")
        self.from_day_var.set(f"{date_obj.day:02d}")
    
    def set_to_date(self, date_obj):
        """終了日を設定"""
        self.to_year_var.set(str(date_obj.year))
        self.to_month_var.set(f"{date_obj.month:02d}")
        self.to_day_var.set(f"{date_obj.day:02d}")

    def reset_date_range(self):
        """日付範囲をリセット（インスタンス生成時の初期値に設定）"""
        self.set_date_range_from_image_data(self.image_tag_map)

        # コールバックを呼び出して日付変更を通知
        if self.on_date_change_callback:
            self.on_date_change_callback()