import os
import json
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.togglebutton import ToggleButton
from kivy.clock import Clock
from kivy.utils import platform

# تحديد مسار ملف البيانات في الأندرويد لضمان الصلاحيات
if platform == 'android':
    from android.storage import app_storage_path
    DATA_DIR = app_storage_path()
else:
    DATA_DIR = "."

CONFIG_FILE = os.path.join(DATA_DIR, "bot_config.json")
LOG_FILE = os.path.join(DATA_DIR, "bot_output.log")

class BotApp(App):
    def build(self):
        self.title = "Single-Coin Grid DCA Bot"
        self.load_config()
        
        # الواجهة الرئيسية
        root = BoxLayout(orientation='vertical', padding=10, spacing=10)
        
        # عنوان التطبيق
        root.add_widget(Label(text="⚙️ Bot Configurations", font_size=20, size_hint_y=None, height=40))
        
        # حقول الإدخال
        self.inputs = {}
        fields = [
            ('API_KEY', self.config_data.get('API_KEY', 'fff9bf53')),
            ('SECRET_KEY', self.config_data.get('SECRET_KEY', 'aac')),
            ('COIN_QUOTE', self.config_data.get('COIN_QUOTE', 'USDT')),
            ('SCREEN_REFRESH_INTERVAL', str(self.config_data.get('SCREEN_REFRESH_INTERVAL', 12000)))
        ]
        
        for field, value in fields:
            box = BoxLayout(orientation='horizontal', size_hint_y=None, height=40, spacing=10)
            box.add_widget(Label(text=field, size_hint_x=0.4))
            ti = TextInput(text=value, multiline=False)
            box.add_widget(ti)
            self.inputs[field] = ti
            root.add_widget(box)
            
        # زر إعادة استثمار الأرباح
        reinvest_box = BoxLayout(orientation='horizontal', size_hint_y=None, height=40)
        reinvest_box.add_widget(Label(text="AUTO_REINVEST", size_hint_x=0.4))
        self.reinvest_btn = ToggleButton(
            text="ON" if self.config_data.get('AUTO_REINVEST', True) else "OFF",
            state="down" if self.config_data.get('AUTO_REINVEST', True) else "normal"
        )
        self.reinvest_btn.bind(on_press=self.toggle_reinvest)
        reinvest_box.add_widget(self.reinvest_btn)
        root.add_widget(reinvest_box)
        
        # أزرار التحكم (حفظ، تشغيل، إيقاف)
        btn_box = BoxLayout(orientation='horizontal', size_hint_y=None, height=50, spacing=10)
        
        save_btn = Button(text="💾 Save Configs", background_color=(0.2, 0.6, 1, 1))
        save_btn.bind(on_press=self.save_config)
        btn_box.add_widget(save_btn)
        
        self.start_btn = Button(text="▶️ Start Bot", background_color=(0.2, 0.8, 0.2, 1))
        self.start_btn.bind(on_press=self.start_bot)
        btn_box.add_widget(self.start_btn)
        
        self.stop_btn = Button(text="⏹️ Stop Bot", background_color=(0.9, 0.2, 0.2, 1))
        self.stop_btn.bind(on_press=self.stop_bot)
        btn_box.add_widget(self.stop_btn)
        
        root.add_widget(btn_box)
        
        # شاشة عرض السجلات (الطباعة الذكية للبوت)
        root.add_widget(Label(text="📊 Live Bot Monitor", font_size=16, size_hint_y=None, height=30))
        self.scroll = ScrollView()
        self.log_label = Label(text="Bot is idle...\n", size_hint_y=None, halign='left', valign='top')
        self.log_label.bind(texture_size=self.log_label.setter('size'))
        self.scroll.add_widget(self.log_label)
        root.add_widget(self.scroll)
        
        # تحديث الشاشة دورياً لقراءة المخرجات من ملف السجل
        Clock.schedule_interval(self.update_logs, 2.0)
        
        return root

    def toggle_reinvest(self, instance):
        instance.text = "ON" if instance.state == 'down' else "OFF"

    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r') as f:
                self.config_data = json.load(f)
        else:
            self.config_data = {
                "API_KEY": "fff9bf53",
                "SECRET_KEY": "aac",
                "COIN_QUOTE": "USDT",
                "SCREEN_REFRESH_INTERVAL": 12000,
                "AUTO_REINVEST": True
            }

    def save_config(self, *args):
        self.config_data = {
            "API_KEY": self.inputs['API_KEY'].text,
            "SECRET_KEY": self.inputs['SECRET_KEY'].text,
            "COIN_QUOTE": self.inputs['COIN_QUOTE'].text,
            "SCREEN_REFRESH_INTERVAL": int(self.inputs['SCREEN_REFRESH_INTERVAL'].text),
            "AUTO_REINVEST": True if self.reinvest_btn.state == 'down' else False
        }
        with open(CONFIG_FILE, 'w') as f:
            json.dump(self.config_data, f)
        self.log_label.text += "[System]: Configurations saved successfully.\n"

    def start_bot(self, instance):
        self.save_config()
        if platform == 'android':
            from android import AndroidService
            service = AndroidService('Grid DCA Bot', 'Running trading bot')
            service.start('org.cryptobot.dca.ServiceService')
            self.log_label.text += "[System]: Background Service Started.\n"
        else:
            self.log_label.text += "[System]: Service start triggered (Android simulation).\n"

    def stop_bot(self, instance):
        if platform == 'android':
            from android import AndroidService
            service = AndroidService('Grid DCA Bot', 'Running trading bot')
            service.stop()
            self.log_label.text += "[System]: Background Service Stopped.\n"
        else:
            self.log_label.text += "[System]: Service stop triggered (Android simulation).\n"

    def update_logs(self, dt):
        if os.path.exists(LOG_FILE):
            with open(LOG_FILE, 'r') as f:
                lines = f.readlines()
                # عرض آخر 40 سطر لتفادي بطء التطبيق
                self.log_label.text = "".join(lines[-40:])
                self.scroll.scroll_y = 0

if __name__ == '__main__':
    BotApp().run()
