import ctypes
import threading
import time
import json
import os
import cv2
import numpy as np
import mss
import pydirectinput
import keyboard
import subprocess
from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *

try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    pass

pydirectinput.PAUSE = 0.01

CONFIG_FILE = "config.json"

COLOR_PRESETS = {
    "any": {"lower": [0, 30, 30], "upper": [179, 255, 255]},
    "blue": {"lower": [90, 80, 0], "upper": [150, 255, 255]},
    "green": {"lower": [35, 80, 0], "upper": [85, 255, 255]},
    "yellow": {"lower": [15, 80, 0], "upper": [45, 255, 255]},
    "purple": {"lower": [135, 80, 0], "upper": [175, 255, 255]},
    "red": {"lower": [0, 100, 100], "upper": [10, 255, 255], "lower2": [160, 100, 100], "upper2": [179, 255, 255]},
    "white": {"lower": [0, 0, 200], "upper": [179, 40, 255]}
}

I18N = {
    "ru": {
        "app_title": "Fishing Auto-Bot Pro",
        "tab_main": "Главная",
        "tab_settings": "Настройки",
        "status_stopped": "Остановлен",
        "status_running": "Сканирование...",
        "btn_calibrate": "Выделить Зону Экрана",
        "btn_start": "Запустить Бота",
        "btn_stop": "Остановить Бота",
        "set_language": "Язык (Language)",
        "set_color": "Цвет сейф-зоны",
        "set_delay": "Задержка клика (мс)",
        "set_hotkey_stop": "Клавиша остановки",
        "theme_toggle": "Темная тема",
        "colors": {
            "any": "Любой цвет (Авто)",
            "blue": "Синяя зона",
            "green": "Зеленая зона",
            "yellow": "Желтая зона",
            "purple": "Фиолетовая зона",
            "red": "Красная зона",
            "white": "Белая зона"
        },
        "debug_mode_toggle": "Режим отладки (Вид бота)",
        "set_sensitivity": "Чувствительность (%)",
        "set_auto_cast": "Авто-заброс и обработка улова",
        "set_cast_duration": "Время заброса (сек)",
        "set_success_color": "Цвет успеха",
        "set_fail_color": "Цвет провала",
        "btn_result_region": "Область результатов",
        "btn_success_coords": "Координаты: Успех",
        "btn_fail_coords": "Координаты: Провал",
        "snack_saved": "Зона успешно сохранена!",
        "snack_cancel": "Выделение отменено.",
        "card_fishing": "Рыбалка",
        "card_automation": "Автоматизация",
        "card_system": "Система"
    },
    "en": {
        "app_title": "Fishing Auto-Bot Pro",
        "tab_main": "Main",
        "tab_settings": "Settings",
        "status_stopped": "Stopped",
        "status_running": "Scanning...",
        "btn_calibrate": "Select Minigame Region",
        "btn_start": "Start Bot",
        "btn_stop": "Stop Bot",
        "set_language": "Language",
        "set_color": "Safe Zone Color",
        "set_delay": "Click Delay (ms)",
        "set_hotkey_stop": "Stop Hotkey",
        "theme_toggle": "Dark Theme",
        "colors": {
            "any": "Any Color (Auto)",
            "blue": "Blue Zone",
            "green": "Green Zone",
            "yellow": "Yellow Zone",
            "purple": "Purple Zone",
            "red": "Red Zone",
            "white": "White Zone"
        },
        "debug_mode_toggle": "Debug Mode (Bot View)",
        "set_sensitivity": "Sensitivity (%)",
        "set_auto_cast": "Auto-cast and Catch Handling",
        "set_cast_duration": "Cast Duration (sec)",
        "set_success_color": "Success Color",
        "set_fail_color": "Fail Color",
        "btn_result_region": "Result Region",
        "btn_success_coords": "Success Click",
        "btn_fail_coords": "Fail Click",
        "snack_saved": "Region successfully saved!",
        "snack_cancel": "Selection cancelled.",
        "card_fishing": "Fishing Options",
        "card_automation": "Automation",
        "card_system": "System"
    }
}

class ConfigManager:
    @staticmethod
    def load_config():
        default_config = {
            "monitor_region": {"top": 0, "left": 0, "width": 800, "height": 600},
            "hotkey_stop": "f8",
            "color_preset": "any",
            "hsv_lower": [0, 50, 50],
            "hsv_upper": [179, 255, 255],
            "click_delay": 20,
            "sensitivity": 100,
            "auto_cast_enabled": False,
            "cast_duration": 1.5,
            "result_region": None,
            "success_color": "green",
            "fail_color": "red",
            "success_coords": {"x": 500, "y": 500},
            "fail_coords": {"x": 500, "y": 500},
            "language": "ru",
            "theme": "dark",
            "debug_mode": False
        }
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r") as f:
                    user_config = json.load(f)
                    default_config.update(user_config)
            except Exception:
                pass
        
        preset_key = default_config.get("color_preset", "any")
        if preset_key in COLOR_PRESETS:
            default_config["hsv_lower"] = COLOR_PRESETS[preset_key]["lower"]
            default_config["hsv_upper"] = COLOR_PRESETS[preset_key]["upper"]
            
        return default_config

    @staticmethod
    def save_config(config):
        with open(CONFIG_FILE, "w") as f:
            json.dump(config, f, indent=4)





class RegionCaptureOverlay(QWidget):
    region_selected = pyqtSignal(dict)
    
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setCursor(Qt.CursorShape.CrossCursor)
        self.start_pos = None
        self.current_pos = None
        rect = QApplication.primaryScreen().virtualGeometry()
        self.setGeometry(rect)
        self.show()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(0, 0, 0, 100))
        if self.start_pos and self.current_pos:
            x = min(self.start_pos.x(), self.current_pos.x())
            y = min(self.start_pos.y(), self.current_pos.y())
            w = abs(self.start_pos.x() - self.current_pos.x())
            h = abs(self.start_pos.y() - self.current_pos.y())
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
            painter.fillRect(x, y, w, h, Qt.GlobalColor.transparent)
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
            painter.setPen(QPen(Qt.GlobalColor.green, 2, Qt.PenStyle.SolidLine))
            painter.drawRect(x, y, w, h)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.start_pos = event.pos()
            
    def mouseMoveEvent(self, event):
        if self.start_pos:
            self.current_pos = event.pos()
            self.update()
            
    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.start_pos:
            x = min(self.start_pos.x(), event.pos().x())
            y = min(self.start_pos.y(), event.pos().y())
            w = abs(self.start_pos.x() - event.pos().x())
            h = abs(self.start_pos.y() - event.pos().y())
            if w > 10 and h > 10:
                self.region_selected.emit({"left": x, "top": y, "width": w, "height": h})
            else:
                self.region_selected.emit({})
            self.close()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.region_selected.emit({})
            self.close()


class ClickCaptureOverlay(QWidget):
    click_selected = pyqtSignal(dict)
    
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setCursor(Qt.CursorShape.CrossCursor)
        rect = QApplication.primaryScreen().virtualGeometry()
        self.setGeometry(rect)
        self.show()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(0, 0, 0, 100))

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.click_selected.emit({"x": int(event.globalPosition().x()), "y": int(event.globalPosition().y())})
            self.close()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.click_selected.emit({})
            self.close()

class BotSignals(QObject):
    stopped = pyqtSignal()

class FishingBot:
    def __init__(self, config):
        self.config = config
        self.is_running = False
        self.bot_thread = None
        self.on_stop_callback = None
        self.prev_white_x = None
        self.last_click_time = 0

    def start(self):
        self.is_running = True
        self.prev_white_x = None
        self.last_click_time = 0
        self.bot_thread = threading.Thread(target=self.loop, daemon=True)
        self.bot_thread.start()

    def stop(self):
        self.is_running = False

    def sleep(self, duration):
        start = time.time()
        while time.time() - start < duration:
            if not self.is_running: return False
            time.sleep(0.05)
        return True

    def on_success(self):
        coords = self.config.get("success_coords")
        if coords:
            pydirectinput.click(x=int(coords["x"]), y=int(coords["y"]), clicks=2, interval=0.1)
        else:
            pydirectinput.click(clicks=2, interval=0.1)
        if not self.sleep(1.0): return
        self.cast()
        
    def on_fail_event(self):
        coords = self.config.get("fail_coords", {"x": 500, "y": 500})
        pydirectinput.click(x=int(coords["x"]), y=int(coords["y"]))
        if not self.sleep(1.0): return
        self.cast()
        
    def cast(self):
        duration = self.config.get("cast_duration", 1.5)
        pydirectinput.mouseDown(button='left')
        if not self.sleep(duration):
            pydirectinput.mouseUp(button='left')
            return
        pydirectinput.mouseUp(button='left')
        self.sleep(1.0)

    def loop(self):
        hotkey_stop = self.config["hotkey_stop"]
        region = self.config["monitor_region"]
        click_delay = self.config.get("click_delay", 20) / 1000.0
        
        kernel = np.ones((5, 20), np.uint8)
        last_frame_time = time.time()
        
        state = "IDLE"
        state_timer = time.time()

        with mss.mss() as sct:
            while self.is_running:
                if keyboard.is_pressed(hotkey_stop):
                    self.stop()
                    if self.on_stop_callback:
                        self.on_stop_callback()
                    break

                current_time = time.time()
                dt = current_time - last_frame_time
                if dt <= 0:
                    dt = 0.001
                last_frame_time = current_time

                img = np.array(sct.grab(region))[:,:,:3]
                hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

                sensitivity = self.config.get("sensitivity", 100)
                
                white_v_min = int(250 - (sensitivity * 1.0))
                white_mask = cv2.inRange(hsv, np.array([0, 0, white_v_min]), np.array([179, 60, 255]))
                contours_white, _ = cv2.findContours(white_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                
                white_marker = None
                for c in contours_white:
                    x, y, w, h = cv2.boundingRect(c)
                    if 10 < h < 150 and w < 50 and h > w * 1.5:
                        if white_marker is None or h > white_marker[3]:
                            white_marker = (x, y, w, h)
                            
                lower_color = np.array(self.config["hsv_lower"])
                upper_color = np.array(self.config["hsv_upper"])
                
                s_boost = int((100 - sensitivity) * 1.5)
                v_boost = int((100 - sensitivity) * 1.5)
                
                adjusted_lower = lower_color.copy()
                adjusted_lower[1] = min(255, adjusted_lower[1] + s_boost)
                adjusted_lower[2] = min(255, adjusted_lower[2] + v_boost)
                
                safe_mask = cv2.inRange(hsv, adjusted_lower, upper_color)
                safe_mask = cv2.morphologyEx(safe_mask, cv2.MORPH_CLOSE, kernel)
                
                contours_safe, _ = cv2.findContours(safe_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                
                safe_zone = None
                for c in contours_safe:
                    x, y, w, h = cv2.boundingRect(c)
                    if w > 10 and 2 < h < 150: 
                        if safe_zone is None or w * h > safe_zone[2] * safe_zone[3]:
                            safe_zone = (x, y, w, h)

                if white_marker:
                    wx, wy, ww, wh = white_marker
                    white_center_x = wx + ww // 2

                    if safe_zone:
                        sx, sy, sw, sh = safe_zone
                        
                        if abs((wy + wh // 2) - (sy + sh // 2)) < 40:
                            target_min = sx - 2
                            target_max = sx + sw + 2
                            
                            current_time = time.time()
                            should_click = False
                            
                            predicted_x = white_center_x
                            if self.prev_white_x is not None:
                                velocity_sec = (white_center_x - self.prev_white_x) / dt
                                predicted_x += velocity_sec * 0.025
                                
                            if target_min <= predicted_x <= target_max:
                                should_click = True
                                
                            if self.prev_white_x is not None:
                                if self.prev_white_x < target_min and white_center_x > target_max:
                                    should_click = True
                                elif self.prev_white_x > target_max and white_center_x < target_min:
                                    should_click = True
                            
                            if should_click and (current_time - self.last_click_time > 0.2):
                                self.last_click_time = time.time()
                                
                                def perform_click(delay):
                                    if delay > 0:
                                        time.sleep(delay)
                                    pydirectinput.mouseDown(button='left')
                                    time.sleep(0.01)
                                    pydirectinput.mouseUp(button='left')
                                    
                                threading.Thread(target=perform_click, args=(click_delay,), daemon=True).start()
                                
                    self.prev_white_x = white_center_x
                else:
                    self.prev_white_x = None
                if self.config.get("auto_cast_enabled", False):
                    if safe_zone and white_marker:
                        state = "MINIGAME"
                        state_timer = current_time
                    elif state == "MINIGAME":
                        if current_time - state_timer > 0.5:
                            state = "RESULT"
                            state_timer = current_time
                    elif state == "RESULT":
                        res_region = self.config.get("result_region")
                        if res_region:
                            res_img = np.array(sct.grab(res_region))[:,:,:3]
                            res_hsv = cv2.cvtColor(res_img, cv2.COLOR_BGR2HSV)
                            
                            def get_mask(hsv, preset_name):
                                preset = COLOR_PRESETS.get(preset_name)
                                if not preset: return np.zeros(hsv.shape[:2], dtype=np.uint8)
                                m = cv2.inRange(hsv, np.array(preset["lower"]), np.array(preset["upper"]))
                                if "lower2" in preset:
                                    m2 = cv2.inRange(hsv, np.array(preset["lower2"]), np.array(preset["upper2"]))
                                    m = cv2.bitwise_or(m, m2)
                                return m
                                
                            succ_mask = get_mask(res_hsv, self.config.get("success_color", "green"))
                            fail_mask = get_mask(res_hsv, self.config.get("fail_color", "red"))
                            
                            if cv2.countNonZero(succ_mask) > 10:
                                self.on_success()
                                state = "IDLE"
                            elif cv2.countNonZero(fail_mask) > 10:
                                self.on_fail_event()
                                state = "IDLE"
                            elif current_time - state_timer > 3.0:
                                self.on_success()
                                state = "IDLE"
                        else:
                            if current_time - state_timer > 1.0:
                                self.on_success()
                                state = "IDLE"
                
                if self.config.get("debug_mode", False):
                    debug_img = img.copy()
                    
                    mask_bool = safe_mask > 0
                    if np.any(mask_bool):
                        green_tint = np.zeros_like(debug_img)
                        green_tint[mask_bool] = (0, 255, 0)
                        debug_img = cv2.addWeighted(debug_img, 0.7, green_tint, 0.3, 0)

                    if white_marker:
                        wx, wy, ww, wh = white_marker
                        cv2.rectangle(debug_img, (wx, wy), (wx+ww, wy+wh), (0, 0, 255), 2)
                        cv2.putText(debug_img, f"White: {wx+ww//2}", (wx, wy - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)
                    if safe_zone:
                        sx, sy, sw, sh = safe_zone
                        cv2.rectangle(debug_img, (sx, sy), (sx+sw, sy+sh), (0, 255, 0), 2)
                        cv2.putText(debug_img, f"Safe: {sx} - {sx+sw}", (sx, sy - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
                        
                    hsv_l = self.config.get('hsv_lower', [0,0,0])
                    hsv_u = self.config.get('hsv_upper', [0,0,0])
                    cv2.putText(debug_img, f"HSV: {hsv_l} -> {hsv_u}", (5, 15), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                    
                    cv2.imshow("Debug View", debug_img)
                    cv2.waitKey(1)
                else:
                    try:
                        cv2.destroyWindow("Debug View")
                    except:
                        pass
                
        try:
            cv2.destroyWindow("Debug View")
        except:
            pass



class BrandWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(120)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.lbl = QLabel(self)
        self.lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.lbl)
        
        import os
        if os.path.exists("effect.gif"):
            self.movie = QMovie("effect.gif")
            self.lbl.setScaledContents(True)
            self.lbl.setMovie(self.movie)
            self.movie.start()
        else:
            self.lbl.setText("KREKERDM")
            self.lbl.setStyleSheet("font-family: 'Georgia', serif; font-size: 50px; font-weight: 900; font-style: italic; color: #888888;")

class MainWindow(QMainWindow):
    def __init__(self, config, bot):
        super().__init__()
        self.config = config
        self.bot = bot
        self.signals = BotSignals()
        self.bot.on_stop_callback = lambda: self.signals.stopped.emit()
        self.signals.stopped.connect(self.on_bot_stopped)
        self.initUI()
        
    def initUI(self):
        self.setWindowTitle("AutoFish")
        self.setFixedSize(500, 750)
        self.setStyleSheet(self.get_stylesheet())
        
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)
        
        self.init_main_tab()
        self.init_settings_tab()
        self.brand_widget = BrandWidget()
        layout.addWidget(self.brand_widget)
        
        self.update_lang()

    def get_stylesheet(self):
        is_dark = self.config.get("theme", "dark") == "dark"
        if is_dark:
            return """
                QWidget { background-color: #1a1a1a; color: #f0f0f0; font-family: 'Segoe UI', Arial, sans-serif; font-size: 13px; }
                QLabel, QCheckBox { background: transparent; }
                QTabWidget::pane { border: 1px solid #333333; background: #1a1a1a; }
                QTabBar::tab { background: #262626; color: #aaaaaa; padding: 10px 25px; margin-right: 2px; font-weight: bold; border: 1px solid #333333; border-bottom: none; border-top-left-radius: 2px; border-top-right-radius: 2px; }
                QTabBar::tab:selected { background: #333333; color: #ffffff; border-top: 2px solid #ffffff; }
                QTabBar::tab:hover:!selected { background: #2e2e2e; }
                QGroupBox { border: 1px solid #444444; border-radius: 2px; margin-top: 25px; padding: 15px; background: #222222; }
                QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top left; left: 0px; top: 0px; padding: 0px; color: #ffffff; font-weight: bold; background: transparent; }
                QPushButton { background-color: #333333; border-radius: 2px; padding: 8px 12px; border: 1px solid #555555; color: #ffffff; font-weight: bold; }
                QPushButton:hover { background-color: #444444; border: 1px solid #777777; }
                QPushButton:pressed { background-color: #222222; }
                QPushButton#actionBtn { background-color: #e0e0e0; color: #111111; font-size: 14px; border: 1px solid #ffffff; border-radius: 2px; padding: 12px; font-weight: bold; }
                QPushButton#actionBtn:hover { background-color: #ffffff; }
                QPushButton#stopBtn { background-color: #444444; color: #ffffff; font-size: 14px; border: 1px solid #888888; border-radius: 2px; padding: 12px; font-weight: bold; }
                QPushButton#stopBtn:hover { background-color: #666666; }
                QSlider { background: transparent; }
                QSlider::groove:horizontal { border: 1px solid #444444; height: 6px; background: #222222; border-radius: 0px; }
                QSlider::sub-page:horizontal { background: #777777; }
                QSlider::handle:horizontal { background: #dddddd; width: 12px; height: 16px; margin: -5px 0; border: 1px solid #555555; border-radius: 0px; }
                QSlider::handle:horizontal:hover { background: #ffffff; border: 1px solid #ffffff; }
                QComboBox, QLineEdit { background: #222222; border: 1px solid #555555; border-radius: 2px; padding: 6px; color: #ffffff; min-width: 150px; }
                QComboBox:hover, QLineEdit:hover { border: 1px solid #888888; }
                QComboBox::drop-down { border: none; width: 20px; }
                QCheckBox::indicator { width: 16px; height: 16px; border-radius: 2px; border: 1px solid #666666; background: #222222; }
                QCheckBox::indicator:hover { border: 1px solid #888888; }
                QCheckBox::indicator:checked { background: #777777; border: 1px solid #aaaaaa; }
                QScrollArea { border: none; background: transparent; }
                QScrollBar:vertical { background: #1a1a1a; width: 12px; margin: 0px; }
                QScrollBar::handle:vertical { background: #444444; min-height: 20px; border-radius: 2px; }
                QScrollBar::handle:vertical:hover { background: #555555; }
                QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
                QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: none; }
            """
        else:
            return """
                QWidget { background-color: #f0f0f0; color: #111111; font-family: 'Segoe UI', Arial, sans-serif; font-size: 13px; }
                QLabel, QCheckBox { background: transparent; }
                QTabWidget::pane { border: 1px solid #cccccc; background: #f0f0f0; }
                QTabBar::tab { background: #e0e0e0; color: #555555; padding: 10px 25px; margin-right: 2px; font-weight: bold; border: 1px solid #cccccc; border-bottom: none; border-top-left-radius: 2px; border-top-right-radius: 2px; }
                QTabBar::tab:selected { background: #ffffff; color: #000000; border-top: 2px solid #333333; }
                QTabBar::tab:hover:!selected { background: #ebebeb; }
                QGroupBox { border: 1px solid #bbbbbb; border-radius: 2px; margin-top: 25px; padding: 15px; background: #ffffff; }
                QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top left; left: 0px; top: 0px; padding: 0px; color: #333333; font-weight: bold; background: transparent; }
                QPushButton { background-color: #e0e0e0; border-radius: 2px; padding: 8px 12px; border: 1px solid #bbbbbb; color: #111111; font-weight: bold; }
                QPushButton:hover { background-color: #d0d0d0; border: 1px solid #888888; }
                QPushButton:pressed { background-color: #cccccc; }
                QPushButton#actionBtn { background-color: #333333; color: #ffffff; font-size: 14px; border: 1px solid #111111; border-radius: 2px; padding: 12px; font-weight: bold; }
                QPushButton#actionBtn:hover { background-color: #111111; }
                QPushButton#stopBtn { background-color: #dddddd; color: #111111; font-size: 14px; border: 1px solid #aaaaaa; border-radius: 2px; padding: 12px; font-weight: bold; }
                QPushButton#stopBtn:hover { background-color: #cccccc; }
                QSlider { background: transparent; }
                QSlider::groove:horizontal { border: 1px solid #cccccc; height: 6px; background: #ffffff; border-radius: 0px; }
                QSlider::sub-page:horizontal { background: #888888; }
                QSlider::handle:horizontal { background: #555555; width: 12px; height: 16px; margin: -5px 0; border: 1px solid #333333; border-radius: 0px; }
                QSlider::handle:horizontal:hover { background: #333333; }
                QComboBox, QLineEdit { background: #ffffff; border: 1px solid #cccccc; border-radius: 2px; padding: 6px; color: #111111; min-width: 150px; }
                QComboBox:hover, QLineEdit:hover { border: 1px solid #888888; }
                QComboBox::drop-down { border: none; width: 20px; }
                QCheckBox::indicator { width: 16px; height: 16px; border-radius: 2px; border: 1px solid #aaaaaa; background: #ffffff; }
                QCheckBox::indicator:hover { border: 1px solid #888888; }
                QCheckBox::indicator:checked { background: #888888; border: 1px solid #555555; }
                QScrollArea { border: none; background: transparent; }
                QScrollBar:vertical { background: #f0f0f0; width: 12px; margin: 0px; }
                QScrollBar::handle:vertical { background: #cccccc; min-height: 20px; border-radius: 2px; }
                QScrollBar::handle:vertical:hover { background: #aaaaaa; }
                QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
                QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: none; }
            """
            
    def init_main_tab(self):
        self.main_tab = QWidget()
        lay = QVBoxLayout(self.main_tab)
        lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.lbl_status = QLabel()
        self.lbl_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_status.setStyleSheet("font-size: 28px; font-weight: 900; color: #CF6679;")
        lay.addWidget(self.lbl_status)
        
        lay.addSpacing(40)
        
        self.btn_calibrate = QPushButton()
        self.btn_calibrate.clicked.connect(self.set_region)
        lay.addWidget(self.btn_calibrate)
        
        lay.addSpacing(20)
        
        self.btn_toggle = QPushButton()
        self.btn_toggle.setObjectName("actionBtn")
        self.btn_toggle.clicked.connect(self.toggle_bot)
        lay.addWidget(self.btn_toggle)
        
        self.tabs.addTab(self.main_tab, "")

    def init_settings_tab(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        content = QWidget()
        scroll.setWidget(content)
        lay = QVBoxLayout(content)
        lay.setSpacing(20)
        
        self.grp_fishing = QGroupBox()
        fish_lay = QFormLayout(self.grp_fishing)
        fish_lay.setSpacing(15)
        fish_lay.setContentsMargins(15, 25, 15, 15)
        
        self.cb_color = QComboBox()
        self.cb_color.currentIndexChanged.connect(self.save_settings)
        self.lbl_color = QLabel()
        fish_lay.addRow(self.lbl_color, self.cb_color)
        
        self.sl_delay = QSlider(Qt.Orientation.Horizontal)
        self.sl_delay.setRange(5, 100)
        self.sl_delay.setValue(self.config.get("click_delay", 20))
        self.sl_delay.valueChanged.connect(self.save_settings)
        self.lbl_delay = QLabel()
        fish_lay.addRow(self.lbl_delay, self.sl_delay)
        
        self.sl_sens = QSlider(Qt.Orientation.Horizontal)
        self.sl_sens.setRange(10, 100)
        self.sl_sens.setValue(self.config.get("sensitivity", 100))
        self.sl_sens.valueChanged.connect(self.save_settings)
        self.lbl_sens = QLabel()
        fish_lay.addRow(self.lbl_sens, self.sl_sens)
        lay.addWidget(self.grp_fishing)
        
        self.grp_auto = QGroupBox()
        auto_lay = QVBoxLayout(self.grp_auto)
        auto_lay.setSpacing(15)
        auto_lay.setContentsMargins(15, 25, 15, 15)
        
        self.chk_autocast = QCheckBox()
        self.chk_autocast.setChecked(self.config.get("auto_cast_enabled", False))
        self.chk_autocast.stateChanged.connect(self.save_settings)
        auto_lay.addWidget(self.chk_autocast)
        
        cast_form = QFormLayout()
        cast_form.setSpacing(15)
        self.sl_cast_dur = QSlider(Qt.Orientation.Horizontal)
        self.sl_cast_dur.setRange(5, 30) 
        self.sl_cast_dur.setValue(int(self.config.get("cast_duration", 1.5) * 10))
        self.sl_cast_dur.valueChanged.connect(self.save_settings)
        self.lbl_cast = QLabel()
        cast_form.addRow(self.lbl_cast, self.sl_cast_dur)
        
        self.cb_succ_color = QComboBox()
        self.cb_succ_color.currentIndexChanged.connect(self.save_settings)
        self.lbl_succ_color = QLabel()
        cast_form.addRow(self.lbl_succ_color, self.cb_succ_color)
        
        self.cb_fail_color = QComboBox()
        self.cb_fail_color.currentIndexChanged.connect(self.save_settings)
        self.lbl_fail_color = QLabel()
        cast_form.addRow(self.lbl_fail_color, self.cb_fail_color)
        
        auto_lay.addLayout(cast_form)
        
        self.btn_res_reg = QPushButton()
        self.btn_res_reg.clicked.connect(self.set_res_region)
        auto_lay.addWidget(self.btn_res_reg)
        
        hlay = QHBoxLayout()
        hlay.setSpacing(15)
        self.btn_win_coords = QPushButton()
        self.btn_win_coords.clicked.connect(self.set_win)
        hlay.addWidget(self.btn_win_coords)
        
        self.btn_fail_coords = QPushButton()
        self.btn_fail_coords.clicked.connect(self.set_fail)
        hlay.addWidget(self.btn_fail_coords)
        auto_lay.addLayout(hlay)
        lay.addWidget(self.grp_auto)
        
        self.grp_sys = QGroupBox()
        sys_lay = QFormLayout(self.grp_sys)
        sys_lay.setSpacing(15)
        sys_lay.setContentsMargins(15, 25, 15, 15)
        
        self.cb_lang = QComboBox()
        self.cb_lang.addItems(["ru", "en"])
        self.cb_lang.setCurrentText(self.config.get("language", "ru"))
        self.cb_lang.currentIndexChanged.connect(lambda: (self.save_settings(), self.update_lang()))
        self.lbl_lang = QLabel()
        sys_lay.addRow(self.lbl_lang, self.cb_lang)
        
        self.le_hotkey = QLineEdit(self.config.get("hotkey_stop", "delete"))
        self.le_hotkey.textChanged.connect(self.save_settings)
        self.lbl_hotkey = QLabel()
        sys_lay.addRow(self.lbl_hotkey, self.le_hotkey)
        
        self.chk_theme = QCheckBox()
        self.chk_theme.setChecked(self.config.get("theme", "dark") == "dark")
        self.chk_theme.stateChanged.connect(lambda: (self.save_settings(), self.setStyleSheet(self.get_stylesheet())))
        self.lbl_theme_stub = QLabel("")
        sys_lay.addRow(self.lbl_theme_stub, self.chk_theme)
        self.lbl_theme_stub.hide()
        
        self.chk_debug = QCheckBox()
        self.chk_debug.setChecked(self.config.get("debug_mode", False))
        self.chk_debug.stateChanged.connect(self.save_settings)
        self.lbl_debug_stub = QLabel("")
        sys_lay.addRow(self.lbl_debug_stub, self.chk_debug)
        self.lbl_debug_stub.hide()
        
        lay.addWidget(self.grp_sys)
        lay.addStretch()
        
        self.sl_delay.valueChanged.connect(self.update_slider_labels)
        self.sl_sens.valueChanged.connect(self.update_slider_labels)
        self.sl_cast_dur.valueChanged.connect(self.update_slider_labels)
        
        self.tabs.addTab(scroll, "")

    def t(self, key):
        keys = key.split('.')
        val = I18N[self.config.get("language", "ru")]
        for k in keys:
            val = val[k]
        return val

    def update_slider_labels(self):
        self.lbl_delay.setText(self.t("set_delay") + f": {self.sl_delay.value()}")
        self.lbl_sens.setText(self.t("set_sensitivity") + f": {self.sl_sens.value()}")
        self.lbl_cast.setText(self.t("set_cast_duration") + f": {self.sl_cast_dur.value() / 10.0}")

    def update_lang(self):
        self.tabs.setTabText(0, self.t("tab_main"))
        self.tabs.setTabText(1, self.t("tab_settings"))
        self.btn_calibrate.setText(self.t("btn_calibrate"))
        self.grp_fishing.setTitle(self.t("card_fishing"))
        self.grp_auto.setTitle(self.t("card_automation"))
        self.grp_sys.setTitle(self.t("card_system"))
        self.chk_autocast.setText(self.t("set_auto_cast"))
        self.btn_res_reg.setText(self.t("btn_result_region"))
        self.btn_win_coords.setText(self.t("btn_success_coords"))
        self.btn_fail_coords.setText(self.t("btn_fail_coords"))
        self.chk_theme.setText(self.t("theme_toggle"))
        self.chk_debug.setText(self.t("debug_mode_toggle"))
        
        self.lbl_color.setText(self.t("set_color"))
        self.lbl_succ_color.setText(self.t("set_success_color"))
        self.lbl_fail_color.setText(self.t("set_fail_color"))
        self.lbl_lang.setText(self.t("set_language"))
        self.lbl_hotkey.setText(self.t("set_hotkey_stop"))
        
        self.update_slider_labels()
        current = self.config.get("color_preset", "any")
        current_s = self.config.get("success_color", "green")
        current_f = self.config.get("fail_color", "red")
        
        self.cb_color.blockSignals(True)
        self.cb_succ_color.blockSignals(True)
        self.cb_fail_color.blockSignals(True)
        
        self.cb_color.clear()
        self.cb_succ_color.clear()
        self.cb_fail_color.clear()
        
        for k, v in self.t("colors").items():
            self.cb_color.addItem(v, k)
            self.cb_succ_color.addItem(v, k)
            self.cb_fail_color.addItem(v, k)
            
        idx = self.cb_color.findData(current)
        if idx >= 0: self.cb_color.setCurrentIndex(idx)
        
        idx_s = self.cb_succ_color.findData(current_s)
        if idx_s >= 0: self.cb_succ_color.setCurrentIndex(idx_s)
        
        idx_f = self.cb_fail_color.findData(current_f)
        if idx_f >= 0: self.cb_fail_color.setCurrentIndex(idx_f)
        
        self.cb_color.blockSignals(False)
        self.cb_succ_color.blockSignals(False)
        self.cb_fail_color.blockSignals(False)
        
        if self.bot.is_running:
            self.lbl_status.setText(self.t("status_running"))
            self.btn_toggle.setText(self.t("btn_stop"))
        else:
            self.lbl_status.setText(self.t("status_stopped"))
            self.btn_toggle.setText(self.t("btn_start"))

    def save_settings(self):
        self.config["language"] = self.cb_lang.currentText()
        if self.cb_color.currentData():
            selected_key = self.cb_color.currentData()
            self.config["color_preset"] = selected_key
            preset = COLOR_PRESETS[selected_key]
            self.config["hsv_lower"] = preset["lower"]
            self.config["hsv_upper"] = preset["upper"]
        if self.cb_succ_color.count() > 0:
            self.config["success_color"] = self.cb_succ_color.currentData() or "green"
        if self.cb_fail_color.count() > 0:
            self.config["fail_color"] = self.cb_fail_color.currentData() or "red"
            
        self.config["click_delay"] = self.sl_delay.value()
        self.config["sensitivity"] = self.sl_sens.value()
        self.config["auto_cast_enabled"] = self.chk_autocast.isChecked()
        self.config["cast_duration"] = self.sl_cast_dur.value() / 10.0
        self.config["hotkey_stop"] = self.le_hotkey.text().lower()
        self.config["theme"] = "dark" if self.chk_theme.isChecked() else "light"
        self.config["debug_mode"] = self.chk_debug.isChecked()
        ConfigManager.save_config(self.config)

    def on_bot_stopped(self):
        self.lbl_status.setText(self.t("status_stopped"))
        self.lbl_status.setStyleSheet("font-size: 28px; font-weight: 900; color: #CF6679;")
        self.btn_toggle.setObjectName("actionBtn")
        self.btn_toggle.setText(self.t("btn_start"))
        self.setStyleSheet(self.get_stylesheet())

    def toggle_bot(self):
        if not self.bot.is_running:
            self.bot.start()
            self.lbl_status.setText(self.t("status_running"))
            self.lbl_status.setStyleSheet("font-size: 28px; font-weight: 900; color: #03DAC6;")
            self.btn_toggle.setObjectName("stopBtn")
            self.btn_toggle.setText(self.t("btn_stop"))
        else:
            self.bot.stop()
            self.on_bot_stopped()
        self.setStyleSheet(self.get_stylesheet())

    def set_region(self):
        self.hide()
        QThread.msleep(200)
        self.overlay = RegionCaptureOverlay()
        self.overlay.region_selected.connect(self.on_region)
        
    def on_region(self, region):
        self.show()
        if region:
            self.config["monitor_region"] = region
            ConfigManager.save_config(self.config)

    def set_res_region(self):
        self.hide()
        QThread.msleep(200)
        self.overlay = RegionCaptureOverlay()
        self.overlay.region_selected.connect(self.on_res_region)
        
    def on_res_region(self, region):
        self.show()
        if region:
            self.config["result_region"] = region
            ConfigManager.save_config(self.config)

    def set_win(self):
        self.hide()
        QThread.msleep(200)
        self.overlay = ClickCaptureOverlay()
        self.overlay.click_selected.connect(self.on_win)
        
    def on_win(self, coords):
        self.show()
        if coords:
            self.config["success_coords"] = coords
            ConfigManager.save_config(self.config)
            
    def set_fail(self):
        self.hide()
        QThread.msleep(200)
        self.overlay = ClickCaptureOverlay()
        self.overlay.click_selected.connect(self.on_fail)
        
    def on_fail(self, coords):
        self.show()
        if coords:
            self.config["fail_coords"] = coords
            ConfigManager.save_config(self.config)

def main():
    import sys
    app = QApplication(sys.argv)
    config = ConfigManager.load_config()
    bot = FishingBot(config)
    win = MainWindow(config, bot)
    win.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
