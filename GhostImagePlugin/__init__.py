#from __future__ import annotations

import io
import os
import shutil
import subprocess
from PIL import Image

IS_WIN = os.name == 'nt'

"""
  Can be overwritten with custom path:

  import GhostImagePlugin
  GhostImagePlugin.GS_BIN = '/foo/gs'
  ...

"""
GS_BIN = os.path.join(os.path.dirname(__file__), 'bin', 'gs.cmd') if IS_WIN else shutil.which('gs')

"""
  Can be overwritten:

  import GhostImagePlugin
  GhostImagePlugin.PDF_DISPLAY_DPI = 300
  ...

"""
PDF_DISPLAY_DPI = 150

# pbm pbmraw pgm pgmraw pgnm pgnmraw pnm pnmraw ppm ppmraw pkm pkmraw pksm pksmraw
# "pnmraw" automatically chooses between PBM ("1"), PGM ("L"), and PPM ("RGB").
PDF_DEVICE = 'ppmraw'

if IS_WIN:
    startupinfo = subprocess.STARTUPINFO()
    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

########################################
#
########################################
def get_page_count(filename):
    if IS_WIN:
        filename = filename.replace('\\', '\\\\')
    proc = subprocess.run(
        [
            GS_BIN,
            "-dQUIET",
            "-dNOSAFER",
            "-dNODISPLAY",
            "-c",
            f"({filename}) (r) file runpdfbegin pdfpagecount = quit",
        ],
        capture_output = True,
        shell = False,
        startupinfo = startupinfo if IS_WIN else None
    )
    return int(proc.stdout.strip())

########################################
#
########################################
def load_page(filename, page):

    proc = subprocess.run(
        [
            GS_BIN,
            "-dQUIET",
            "-dBATCH",      # exit after processing
            "-dNOPAUSE",    # don't pause between pages
            "-dSAFER",
            f"-r{PDF_DISPLAY_DPI:f}x{PDF_DISPLAY_DPI:f}",
            f"-sPageList={page + 1}",
            f"-sDEVICE={PDF_DEVICE}",
            # The options below are for smoother text rendering. The default text render mode is unbearable.
            "-dInterpolateControl=-1",
            "-dTextAlphaBits=4",
            "-dGraphicsAlphaBits=4",
            "-sOutputFile=-",
            "-f",
            filename,
        ],
        capture_output = True,
        shell = False,
        startupinfo = startupinfo if IS_WIN else None
    )
    img = Image.open(io.BytesIO(proc.stdout), formats=('PPM',))
    img.load()
    return img

def _open(fp, filename, ** kwargs):

    get_page_count(filename)

    img = load_page(filename, 0)  #.copy()
    img.filename = filename
    img.format = "PDF"
    img.__frame = 0
    img.n_frames = get_page_count(filename)
    img.is_animated = img.n_frames > 1

    def _seek(self, frame):
        if frame < 0 or frame >= self.n_frames:
            raise EOFError()
        self.__frame = frame
        _img = load_page(self.filename, frame)
        self.im = _img.im
        _img.close()

    img.seek = _seek.__get__(img)

    img.tell = lambda: img.__frame

    img._dump = (lambda file=None, format=None, d=img._dump, **options:
            options.update({'save_all': False}) or d(file, format, **options))

    return img

# --------------------------------------------------------------------

Image.register_open("PDF", _open, lambda prefix: prefix[:4] == b'%PDF')
Image.register_extensions("PDF", [".pdf", ".ai"])

if __name__ == "__main__":
    img = Image.open("../_test_files/test.pdf")
    img.show()
