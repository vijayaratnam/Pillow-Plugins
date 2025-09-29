# Pillow-Plugins - 6 plugins for Pillow (Python)

## 1. FfmpegImagePlugin
Allows [Pillow](https://pillow.readthedocs.io/) to load arbitrary video files as (virtual) multi-frame images.  
Requires [FFmpeg](https://ffmpeg.org/).

Usage:
```python
from PIL import Image
import FfmpegImagePlugin

img = Image.open("test.mp4")
img.seek(123)
img.show()
```

## 2. FreeImagePlugin
Read support for additional image file formats/image modes based on FreeImage.
- MNG (first frame, i.e. not animated)
- Apple PICT
- PSD/TIFF with 16 and 32 bits (floating point) per channel.  

Requires [FreeImage](https://freeimage.sourceforge.io/) (DLL for Windows is included).

Usage:
```python
from PIL import Image
import FreeImagePlugin

img = Image.open("test.pct")
img.show()
```

## 3. GhostImagePlugin
Allows Pillow to load PDF and Adobe Illustrator (AI) files as (virtual) multi-frame images.  
Requires [Ghostscript](https://ghostscript.com/) (binary for Windows is included).

Usage:
```python
from PIL import Image
import GhostImagePlugin

img = Image.open("test.pdf")
img.seek(2)
img.show()
```

## 4. LibreImagePlugin
Allows Pillow to load CorelDraw (CDR), Macromedia FreeHand (FH/FHx) and OpenDocument Graphic (ODG) files as images by using LibreOffice Draw (headless).  
Requires [LibreOffice Draw](https://www.libreoffice.org/) (or OpenOffice Draw, not tested).

Usage:
```python
from PIL import Image
import LibreImagePlugin

img = Image.open("test.cdr")
img.show()
```

## 5. SvgImagePlugin
Allows Pillow to load SVG vector graphic files as images.
Depends on [pycairo](https://pycairo.readthedocs.io/) (`pip install pycairo`, also available for Windows).

Usage:
```python
from PIL import Image
import SvgImagePlugin

img = Image.open("test.svg", output_width = 800)
img.show()
```

## 6. WinImageShowPlugin
A better and way faster Image.show() implementation for Python 3.x x64 on Windows.

Images are shown in a native resizable viewer window, without creating
any temporary files. While the window is displayed, other image files
can be dropped into it from Explorer to view them.
In addition to Pillow the script only uses ctypes and the Windows API,
no 3rd-party modules involved.

Usage:
```python
from PIL import Image
import WinImageShowPlugin  # import overwrites Image.show() method

img = Image.open("test.tif")
img.show()  # Blocks code execution until viewer window is closed
```
