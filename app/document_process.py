"""Small environment for untrusted document parsers, without application secrets."""
import os,shutil,threading
from pathlib import Path
DOCUMENT_SLOTS=threading.BoundedSemaphore(2)
def worker_environment():
    return {**{k:os.environ[k] for k in ('SystemRoot','TEMP','TMP','TESSDATA_PREFIX') if k in os.environ},
            'PATH':os.environ.get('PATH','') if os.name=='nt' else '/usr/bin:/bin',
            'LANG':'C.UTF-8','PYTHONUTF8':'1','PYTHONPATH':str(Path(__file__).resolve().parent.parent),
            'MLO_TESSERACT':shutil.which('tesseract') or 'tesseract',
            'MLO_PDFTOPPM':shutil.which('pdftoppm') or 'pdftoppm'}
