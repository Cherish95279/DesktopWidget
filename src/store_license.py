# -*- coding: utf-8 -*-
"""
微软商店 Pro License 检测和购买模块。
仅商店版（MSIX）可用，exe 版会返回检测失败。
"""
import threading
import time

# pro_version 加载项的 Store ID
PRO_STORE_ID = "9NN1JB5S2Q0Q"

def _log(msg):
    import os, tempfile
    try:
        with open(os.path.join(tempfile.gettempdir(), "dw_store_debug.log"), "a", encoding="utf-8") as f:
            f.write(str(msg) + "\n")
    except Exception:
        pass


# 缓存检测结果，避免频繁调用异步 API
_cached_result = None  # None=未检测, True=已购买, False=未购买, "error"=检测失败
_cached_time = 0.0  # 缓存写入时间（monotonic）
# True/False 缓存 5 分钟过期，"error" 仅缓存 30 秒，避免临时故障被长期锁定
_CACHE_TTL = 300
_ERROR_CACHE_TTL = 30
# 是否已订阅商店许可证变更事件
_license_subscribed = False


def _wait_async(async_op, timeout=30):
    """同步等待 winsdk 异步操作完成，不依赖 asyncio"""
    import threading as _t
    done = _t.Event()
    box = {}

    def _on_completed(op, status):
        box["status"] = status
        box["result"] = None
        try:
            box["result"] = op.get_results()
        except Exception as e:
            box["error"] = e
        done.set()

    async_op.completed = _on_completed
    done.wait(timeout=timeout)
    if not done.is_set():
        return ("error", "timeout")
    if "error" in box:
        return ("error", str(box["error"]))
    return box.get("result")


def _check_license_inner(window_handle=None):
    """检测 pro_version 加载项是否已购买"""
    try:
        from winsdk.windows.services.store import StoreContext
        if window_handle:
            ctx = StoreContext.get_for_window(window_handle)
        else:
            ctx = StoreContext.get_default()
        _log(f"check_pro_license ctx_ok={ctx is not None} wh={window_handle}")
        if ctx is None:
            return "error"

        op = ctx.get_app_license_async()
        license = _wait_async(op)
        if isinstance(license, tuple) and license[0] == "error":
            _log(f"check_pro_license license_error: {license[1]}")
            return "error"

        add_ons = license.add_on_licenses
        for i in range(add_ons.size):
            key = add_ons.get_at(i)
            val = add_ons.lookup(key)
            if val.is_active:
                return True
        return False
    except ImportError as e:
        _log(f"check_pro_license ImportError: {e}")
        return "error"
    except Exception as e:
        _log(f"check_pro_license exception: {type(e).__name__}: {e}")
        return "error"


def check_pro_license(window_handle=None):
    """
    检测 pro_version 加载项是否已购买。
    返回值:
        True  = 已购买 Pro
        False = 明确未购买
        "error" = 检测失败（网络/API异常）
    """
    global _cached_result
    global _cached_time
    now = time.monotonic()
    if _cached_result is not None:
        ttl = _ERROR_CACHE_TTL if _cached_result == "error" else _CACHE_TTL
        if (now - _cached_time) < ttl:
            return _cached_result
    # 首次或缓存过期：订阅许可证变更事件（仅一次）
    subscribe_license_changes()
    _cached_result = _check_license_inner(window_handle)
    _cached_time = now
    return _cached_result


def refresh_license():
    """清除缓存，重新检测"""
    global _cached_result
    _cached_result = None
    global _cached_time
    _cached_time = 0.0


def subscribe_license_changes():
    """订阅商店许可证变更事件。
    系统后台同步许可证（如内购完成后）时会触发，自动清除缓存，
    使下次检测拿到最新状态，无需重启应用。
    """
    global _license_subscribed
    if _license_subscribed:
        return
    try:
        from winsdk.windows.services.store import StoreContext
        ctx = StoreContext.get_default()
        if ctx is None:
            return

        def _on_changed(sender, args):
            _log("offline_licenses_changed")
            refresh_license()

        ctx.add_offline_licenses_changed(_on_changed)
        _license_subscribed = True
        _log("subscribe_license_changes ok")
    except ImportError:
        pass
    except Exception as e:
        _log(f"subscribe_license_changes exception: {type(e).__name__}: {e}")


def request_purchase(callback=None, window_handle=None):
    """
    弹出微软商店购买窗口。
    callback: 购买完成后的回调函数，参数为 True(成功)/False(失败)/"error"(异常)
    window_handle: Qt 窗口句柄（int），用于弹出购买对话框
    """
    try:
        from winsdk.windows.services.store import StoreContext, StorePurchaseStatus
        import winsdk._winrt as winrt

        def purchase():
            ctx = StoreContext.get_default()
            _log(f"request_purchase ctx_ok={ctx is not None} wh={window_handle}")
            if ctx is None:
                return "error"

            # 设置窗口句柄
            if window_handle:
                try:
                    winrt.initialize_with_window(ctx, window_handle)
                    _log("initialize_with_window ok")
                except Exception as e:
                    _log(f"initialize_with_window failed: {type(e).__name__}: {e}")

            try:
                op = ctx.request_purchase_async(PRO_STORE_ID)
                result = _wait_async(op, timeout=120)
            except Exception as e:
                _log(f"request_purchase_async exception: {type(e).__name__}: {e}")
                return "error"

            if isinstance(result, tuple) and result[0] == "error":
                _log(f"purchase_wait_error: {result[1]}")
                return "error"

            status = result.status
            _log(f"purchase_status={status}")
            if status == StorePurchaseStatus.SUCCEEDED:
                refresh_license()
                return True
            elif status == StorePurchaseStatus.ALREADY_PURCHASED:
                refresh_license()
                return True
            else:
                return False

        def run():
            r = purchase()
            _log(f"purchase_callback_result={r!r}")
            if callback:
                callback(r)

        t = threading.Thread(target=run, daemon=True)
        t.start()
    except ImportError:
        _log("request_purchase ImportError")
        if callback:
            callback("error")
    except Exception as e:
        _log(f"request_purchase outer_exception: {type(e).__name__}: {e}")
        if callback:
            callback("error")