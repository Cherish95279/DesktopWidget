from PyQt6.QtCore import QSettings
from PyQt6.QtGui import QColor, QPainter
from PyQt6.QtWidgets import QWidget


class ThemeMixin:
    """主题管理混入：背景缓存、着色"""

    def update_theme_cache(self, force=False):
        """更新主题缓存（背景图颜色叠加+透明度）
        Args:
            force: 是否强制重建，忽略缓存比较
        """
        settings = QSettings("MyDesktopApp", "WeatherSettings")
        theme_opacity = int(settings.value("theme_opacity", 100))
        theme_color = settings.value("theme_color", "#a8c7dc")
        theme_tint_alpha = int(settings.value("theme_tint_alpha", 80))

        # 如果不强制，且缓存存在且一致，则跳过
        if not force and (self._cached_bg is not None and
                          self._cached_theme_color == theme_color and
                          self._cached_theme_opacity == theme_opacity and
                          self._cached_tint_alpha == theme_tint_alpha):
            return

        self._cached_theme_color = theme_color
        self._cached_theme_opacity = theme_opacity
        self._cached_tint_alpha = theme_tint_alpha

        # 重建背景图
        if not self.bg.isNull():
            bg_pixmap = self.bg.copy()
            if not bg_pixmap.isNull():
                color = QColor(theme_color)
                color.setAlpha(theme_tint_alpha)
                temp_painter = QPainter(bg_pixmap)
                temp_painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceAtop)
                temp_painter.fillRect(bg_pixmap.rect(), color)
                temp_painter.end()
                self._cached_bg = bg_pixmap
            else:
                self._cached_bg = self.bg
        else:
            self._cached_bg = QPixmap(400, 297)
            self._cached_bg.fill(QColor(theme_color))

        self.update()

    def apply_theme(self):
        """应用主题（外部调用接口）"""
        self.update_theme_cache()