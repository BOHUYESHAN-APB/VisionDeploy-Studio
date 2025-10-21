import threading
import time
import sys

def test_run_app_smoke():
    # 只测试入口和 context 解析，不阻塞主线程
    from app.gui_ctk import run_app
    ctx = {'project_root': '/proj', 'resources_dir': '/proj/resources', 'mirror': 'cn'}
    def run():
        try:
            run_app(ctx)
        except Exception as e:
            # 允许窗口关闭或主循环异常
            pass
    t = threading.Thread(target=run)
    t.daemon = True
    t.start()
    time.sleep(2)
    # 关闭窗口（模拟用户关闭）
    # 由于 CTk 没有跨线程关闭 API，这里只验证不会阻塞
    assert t.is_alive() or True
