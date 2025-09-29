__all__ = []

"""
    Importing this script in Python 3.x x64 on Windows overwrites
    Pillow"s default (slow) "Image.show()" implementation based on
    temporary PNGs with a faster implementation that instead shows
    the image in a native resizable viewer window, without creating
    any temporary files. While the window is shown, other image files
    can be dropped into it from Explorer to view them.
    In addition to Pillow the script only uses ctypes and the Win API,
    no 3rd-party modules involved.

    Usage:
    ======

    from PIL import Image
    import WinImageShowPlugin  # import overwrites Image.show() method

    img = Image.open("lena.png")
    img.show()  # Blocks code execution until viewer window is closed
    ...
"""

from ctypes import *
from ctypes.wintypes import *
import io
from PIL import Image

########################################
# Used Winapi structs
########################################
class PAINTSTRUCT(Structure):
    _fields_ = [
        ("hdc",            HDC),
        ("fErase",         BOOL),
        ("rcPaint",        RECT),
        ("fRestore",       BOOL),
        ("fIncUpdate",     BOOL),
        ("rgbReserved",    BYTE * 32),
    ]

LONG_PTR = c_longlong  # for x64 only!
WNDPROC = WINFUNCTYPE(LONG_PTR, HWND, UINT, WPARAM, LPARAM)

class WNDCLASSEX(Structure):
    def __init__(self, *args, **kwargs):
        super(WNDCLASSEX, self).__init__(*args, **kwargs)
        self.cbSize = sizeof(self)
    _fields_ = [
        ("cbSize",          UINT),
        ("style",           UINT),
        ("lpfnWndProc",     WNDPROC),
        ("cbClsExtra",      INT),
        ("cbWndExtra",      INT),
        ("hInstance",       HANDLE),
        ("hIcon",           HANDLE),
        ("hCursor",         HANDLE),
        ("hBrush",          HANDLE),
        ("lpszMenuName",    LPCWSTR),
        ("lpszClassName",   LPCWSTR),
        ("hIconSm",         HANDLE)
    ]

# https://learn.microsoft.com/en-us/windows/win32/api/wingdi/ns-wingdi-bitmapinfoheader
class BITMAPINFOHEADER(Structure):
    def __init__(self, *args, **kwargs):
        super(BITMAPINFOHEADER, self).__init__(*args, **kwargs)
        self.biSize = sizeof(self)
    _fields_ = [
        ("biSize", DWORD),
        ("biWidth", LONG),
        ("biHeight", LONG),
        ("biPlanes", WORD),
        ("biBitCount", WORD),
        ("biCompression", DWORD),
        ("biSizeImage", DWORD),
        ("biXPelsPerMeter", LONG),
        ("biYPelsPerMeter", LONG),
        ("biClrUsed", DWORD),
        ("biClrImportant", DWORD)
    ]

########################################
# Used Winapi functions
########################################
gdi32 = windll.Gdi32
gdi32.CreateCompatibleDC.argtypes = (HDC,)
gdi32.CreateCompatibleDC.restype = HDC
gdi32.CreateDIBSection.argtypes = (HDC, LPVOID, UINT, LPVOID, HANDLE, DWORD)
gdi32.CreateDIBSection.restype = HBITMAP
gdi32.DeleteDC.argtypes = (HDC,)
gdi32.GetStockObject.restype = HANDLE
gdi32.SelectObject.argtypes = (HDC, HANDLE)
gdi32.SelectObject.restype = HANDLE
gdi32.SetDIBits.argtypes = (HDC, HBITMAP, UINT, UINT, LPVOID, LPVOID, UINT)
gdi32.SetStretchBltMode.argtypes = (HDC, INT)
gdi32.StretchBlt.argtypes = (HDC, INT, INT, INT, INT, HDC, INT, INT, INT, INT, DWORD)

kernel32 = windll.Kernel32
kernel32.GetModuleHandleW.argtypes = (LPCWSTR,)
kernel32.GetModuleHandleW.restype = HINSTANCE

shell32 = windll.shell32
shell32.DragAcceptFiles.argtypes = (HWND, BOOL)
shell32.DragFinish.argtypes = (WPARAM, )
shell32.DragQueryFileW.argtypes = (WPARAM, UINT, LPWSTR, UINT)

user32 = windll.user32
user32.BeginPaint.argtypes = (HWND, POINTER(PAINTSTRUCT))
user32.CreateWindowExW.argtypes = (DWORD, LPCWSTR, LPCWSTR, DWORD, INT, INT, INT, INT, HWND, HMENU, HINSTANCE, LPVOID)
user32.DefWindowProcW.argtypes = (HWND, UINT, WPARAM, LPARAM)
user32.DestroyWindow.argtypes = (HWND,)
user32.DispatchMessageW.argtypes = (POINTER(MSG),)
user32.EndPaint.argtypes = (HWND, POINTER(PAINTSTRUCT))
user32.GetMessageW.argtypes = (POINTER(MSG),HWND,UINT,UINT)
user32.LoadCursorW.argtypes = (HINSTANCE, LPVOID)
user32.LoadCursorW.restype = HANDLE
user32.LoadIconW.argtypes = (HINSTANCE, LPCWSTR)
user32.LoadIconW.restype = HICON
user32.PostMessageW.argtypes = (HWND, UINT, LPVOID, LPVOID)
user32.SystemParametersInfoA.argtypes = (UINT, UINT, LPVOID, UINT)
user32.TranslateMessage.argtypes = (POINTER(MSG),)

########################################
# Used Winapi constants
########################################
BI_RGB = 0
BLACK_BRUSH = 4
CS_HREDRAW = 2
CS_VREDRAW = 1
CW_USEDEFAULT = -2147483648
DIB_RGB_COLORS = 0
HALFTONE = 4
IDC_ARROW = 32512
RDW_ERASE = 4
RDW_INVALIDATE = 1
SM_CYCAPTION = 4
SPI_GETWORKAREA = 48
SRCCOPY = 13369376
WM_CLOSE = 16
WM_DROPFILES = 563
WM_PAINT = 15
WM_QUIT = 18
WS_OVERLAPPEDWINDOW = 13565952
WS_VISIBLE = 268435456

########################################
#
########################################
def img_to_hbitmap(img):
    if img.mode in ("LA", "PA"):
        img = img.convert(img.mode[:-1])
    elif img.mode not in ("RGB", "RGBA", "L", "1", "P"):
        img = img.convert("RGB")
    pal_size = 0
    if img.mode == "1":
        pal_size = 8
        pal = [0, 0, 0, 0, 255, 255, 255, 0]
        bbp = 1
    elif img.mode == "L":
        pal_size = 1024
        pal = [0] * 1024
        for i in range(256):
            pal[4 * i:4 * i + 3] = i, i, i
        bbp = 8
    elif img.mode == "P":   #bbp <= 8:
        pal = img.getpalette("BGRX")
        pal_size = len(pal)
        bbp = 8
    elif img.mode == "RGB":
        bbp = 24
    elif img.mode == "RGBA":
        bbp = 32

    f = io.BytesIO()
    img.save(f, "DIB")
    biClrUsed = pal_size // 4

    class BITMAPINFO(Structure):
        _pack_ = 1
        _fields_ = [
            ("bmiHeader", BITMAPINFOHEADER),
            ("bmiColors", c_ubyte * pal_size),
        ]

    bmi = BITMAPINFO()
    bmi.bmiHeader.biSize = sizeof(BITMAPINFOHEADER)
    bmi.bmiHeader.biWidth = img.width
    bmi.bmiHeader.biHeight = img.height
    bmi.bmiHeader.biPlanes = 1
    bmi.bmiHeader.biBitCount = bbp
    bmi.bmiHeader.biCompression = BI_RGB
    bmi.bmiHeader.biSizeImage = ((((img.width * bmi.bmiHeader.biBitCount) + 31) & ~31) >> 3) * img.height
    bmi.bmiHeader.biClrUsed = biClrUsed
    if biClrUsed:
        bmi.bmiColors = (c_ubyte * pal_size)(*pal)

    hdc = gdi32.CreateCompatibleDC(0)
    h_bitmap = gdi32.CreateDIBSection(None, byref(bmi), DIB_RGB_COLORS, None, None, 0)
    gdi32.SetDIBits(
        0, h_bitmap, 0, img.height,
        f.getvalue()[sizeof(BITMAPINFOHEADER) + pal_size:],
        byref(bmi),
        DIB_RGB_COLORS
    )
    gdi32.DeleteDC(hdc)
    return h_bitmap


class WinImageShow():

    def __init__(self, img, window_title):

        self.img = img
        self.h_bitmap = img_to_hbitmap(img)
        self.img_ratio = img.width / img.height

        # Show image centered and resized to window while keeping its aspect ratio
        def _on_WM_PAINT(hwnd, wparam, lparam):
            rc = RECT()
            user32.GetClientRect(hwnd, byref(rc))
            width, height = rc.right, rc.bottom
            if width / height > self.img_ratio:
                dest_width = round(height * self.img_ratio)
                dest_height = height
                x = (width - dest_width) // 2
                y = 0
            else:
                dest_width = width
                dest_height = round(width / self.img_ratio)
                x = 0
                y = (height - dest_height) // 2
            ps = PAINTSTRUCT()
            hdc = user32.BeginPaint(hwnd, byref(ps))
            gdi32.SetStretchBltMode(hdc, HALFTONE)
            hdc_mem = gdi32.CreateCompatibleDC(hdc)
            gdi32.SelectObject(hdc_mem, self.h_bitmap)
            gdi32.StretchBlt(
                hdc, x, y, dest_width, dest_height,  # dest
                hdc_mem, 0, 0, self.img.width, self.img.height,  # scr
                SRCCOPY
            )
            gdi32.DeleteDC(hdc_mem)
            user32.EndPaint(hwnd, byref(ps))
            return 0

        def _on_WM_DROPFILES(hwnd, wparam, lparam):
            file_buffer = create_unicode_buffer("", MAX_PATH)
            shell32.DragQueryFileW(wparam, 0, file_buffer, MAX_PATH)
            shell32.DragFinish(wparam)
            filename = file_buffer[:].split("\0", 1)[0]
            try:
                img = Image.open(filename)
                self.h_bitmap = img_to_hbitmap(img)
                self.img = img
                self.img_ratio = img.width / img.height
                user32.SetWindowTextW(hwnd, f"{filename} - {img.mode} - {img.width} x {img.height}")
                user32.SetWindowPos(hwnd, 0, *self.get_win_size_for_image(img), 0)
                user32.RedrawWindow(hwnd, 0, 0, RDW_ERASE | RDW_INVALIDATE)
            finally:
                return 0

        def _window_proc_callback(hwnd, msg, wparam, lparam):
            if msg == WM_PAINT:
                return _on_WM_PAINT(hwnd, wparam, lparam)
            elif msg == WM_DROPFILES:
                return _on_WM_DROPFILES(hwnd, wparam, lparam)
            elif msg == WM_CLOSE:
                user32.PostMessageW(self.hwnd, WM_QUIT, 0, 0)
            return user32.DefWindowProcW(hwnd, msg, wparam, lparam)

        wndclass = WNDCLASSEX()
        wndclass.lpfnWndProc = WNDPROC(_window_proc_callback)
        wndclass.style = CS_VREDRAW | CS_HREDRAW
        wndclass.lpszClassName = "PILImageShow"
        wndclass.hBrush = gdi32.GetStockObject(BLACK_BRUSH)
        wndclass.hCursor = user32.LoadCursorW(0, IDC_ARROW)
        wndclass.hIcon = user32.LoadIconW(kernel32.GetModuleHandleW(None), LPCWSTR(1))  # Python icon
        wndclass.hIconSm = wndclass.hIcon
        user32.RegisterClassExW(byref(wndclass))
        self.hwnd = user32.CreateWindowExW(
            0,
            wndclass.lpszClassName,
            window_title,
            WS_OVERLAPPEDWINDOW | WS_VISIBLE,
            *self.get_win_size_for_image(img),
            None, None, None, None
        )
        shell32.DragAcceptFiles(self.hwnd, True)
        msg = MSG()
        while user32.GetMessageW(byref(msg), 0, 0, 0) > 0:
            user32.TranslateMessage(byref(msg))
            user32.DispatchMessageW(byref(msg))
        user32.DestroyWindow(self.hwnd)

    # Show window centered on screen and never bigger than the actual work area (desktop minus taskbar)
    def get_win_size_for_image(self, img):
        rc_desktop = RECT()
        user32.SystemParametersInfoA(SPI_GETWORKAREA, 0, byref(rc_desktop), 0)
        rc_desktop.right -= 32  # Windows 11 DWM fix
        caption_height = user32.GetSystemMetrics(SM_CYCAPTION)
        win_width, win_height = img.width, img.height + caption_height
        if win_width > rc_desktop.right or win_height > rc_desktop.bottom:
            desktop_ratio = rc_desktop.right / (rc_desktop.bottom - caption_height)
            if desktop_ratio > img_ratio:
                win_height = rc_desktop.bottom
                win_width = round(win_height * desktop_ratio)
            else:
                win_width = rc_desktop.right
                win_height = round(win_width / desktop_ratio)
        x = (rc_desktop.right - win_width) // 2 + 16
        y = (rc_desktop.bottom - win_height) // 2
        return x, y, win_width, win_height

# This overwrites the Image.show() method with our custom implementation
import sys
if sys.platform == "win32":
    def _show(img, **options):
        WinImageShow(img, options.get("title", None) or (f"{getattr(img, 'filename', 'Pillow Image')} - {img.mode} - {img.width} x {img.height}"))
    setattr(Image, "_show", _show)

if __name__ == "__main__":
    img = Image.open(r"_test_files/test.png")
    img.show()
