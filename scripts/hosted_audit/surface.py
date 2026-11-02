"""Keep browser events on the page and UI queries inside the actual app frame."""
import time
from urllib.parse import urlsplit


class AppSurface:
    def __init__(self, host):
        self.host = host
        self.app = host.main_frame

    def goto(self, *args, **kwargs):
        # Reloading during deployment polling detaches the old child frame.
        # Until bind_app runs again, queries must target the current main frame.
        self.app = self.host.main_frame
        try:
            return self.host.goto(*args, **kwargs)
        finally:
            self.app = self.host.main_frame

    def bind_app(self, timeout=45000):
        """Cloud embeds the UI at /~/+/; localhost normally uses the main frame."""
        self.app = self.host.main_frame
        deadline = time.monotonic() + timeout/1000
        hostname = urlsplit(self.host.url).hostname
        while True:
            for frame in self.host.frames:
                # Ignore third-party status/advertising frames, even if their
                # text happens to resemble an application navigation label.
                if urlsplit(frame.url).hostname != hostname:
                    continue
                if frame.get_by_text('Home/Overview', exact=True).is_visible():
                    self.app = frame
                    return frame.url.split('?')[0]
            if time.monotonic() >= deadline:
                raise TimeoutError('Home/Overview not visible in a same-host application frame')
            self.host.wait_for_timeout(250)

    def __getattr__(self, name):
        if name.startswith('get_by_') or name in {'locator', 'evaluate', 'wait_for_function'}:
            return getattr(self.app, name)
        # Downloads, screenshots, navigation and event listeners belong to the
        # real Page, including downloads initiated by an embedded frame.
        return getattr(self.host, name)
