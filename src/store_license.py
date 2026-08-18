# -*- coding: utf-8 -*-
"""
微软商店 Pro License 检测和购买模块。
仅商店版（MSIX）可用，exe 版会返回检测失败。
"""
import asyncio
import threading

# pro_version 加载项的 Store ID
PRO_STORE_ID = "9NN1JB5S2Q0Q"

# 缓存检测结果，避免频繁调用异步 API
_cached_result = None  # None=未检测, True=已购买, False=未购买, "error"=检测失败


def _run_async(coro):
    """在新线程中运行异步函数"""
    result = [None]
    def run():
        try:
            result[0] = asyncio.run(coro)
        except Exception as e:
            result[0] = ("error", str(e))
    t = threading.Thread(target=run, daemon=True)
    t.start()
    t.join(timeout=10)
    return result[0]


def _check_license_inner(window_handle=None):
    """检测 pro_version 加载项是否已购买"""
    try:
        from winsdk.windows.services.store import StoreContext
        if window_handle:
            ctx = StoreContext.get_for_window(window_handle)
        else:
            ctx = StoreContext.get_default()
        if ctx is None:
            return "error"

        async def check():
            license = await ctx.get_app_license_async()
            add_ons = license.add_on_licenses
            for i in range(add_ons.size):
                key = add_ons.get_at(i)
                val = add_ons.lookup(key)
                if val.is_active:
                    return True
            return False

        return _run_async(check())
    except ImportError:
        return "error"
    except Exception:
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
    if _cached_result is not None:
        return _cached_result
    _cached_result = _check_license_inner(window_handle)
    return _cached_result


def refresh_license():
    """清除缓存，重新检测"""
    global _cached_result
    _cached_result = None


def request_purchase(callback=None, window_handle=None):
    """
    弹出微软商店购买窗口。
    callback: 购买完成后的回调函数，参数为 True(成功)/False(失败)/"error"(异常)
    window_handle: Qt 窗口句柄（int），用于弹出购买对话框
    """
    try:
        from winsdk.windows.services.store import StoreContext, StorePurchaseStatus
        import winsdk._winrt as winrt

        async def purchase():
            ctx = StoreContext.get_default()
            if ctx is None:
                return "error"

            # 设置窗口句柄
            if window_handle:
                try:
                    winrt.initialize_with_window(ctx, window_handle)
                except Exception:
                    pass

            result = await ctx.request_purchase_async(PRO_STORE_ID)
            status = result.status
            if status == StorePurchaseStatus.SUCCEEDED:
                refresh_license()
                return True
            elif status == StorePurchaseStatus.ALREADY_PURCHASED:
                refresh_license()
                return True
            else:
                return False

        def run():
            r = _run_async(purchase())
            if callback:
                callback(r)

        t = threading.Thread(target=run, daemon=True)
        t.start()
    except ImportError:
        if callback:
            callback("error")
    except Exception as e:
        print(f"[Store] request_purchase error: {e}")
        if callback:
            callback("error")
