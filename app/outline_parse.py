"""Bounded document-to-text worker. No uploaded content is executed or retained."""
import io
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import zipfile
from defusedxml import ElementTree

MAX_TEXT = 500_000


def ocr(path):
    from PIL import Image
    Image.MAX_IMAGE_PIXELS = 20_000_000
    with Image.open(path) as image:
        if image.width * image.height > 20_000_000:
            raise ValueError('Image exceeds 20 megapixels. Resize it and try again.')
        image.verify()
    result = subprocess.run(['tesseract', str(path), 'stdout', '-l', 'eng'],
                            capture_output=True, timeout=25, check=True)
    return result.stdout.decode('utf-8', errors='replace')[:MAX_TEXT]


def extract(path, extension):
    data = Path(path).read_bytes()
    pages = []
    if extension == '.pdf':
        if not data.startswith(b'%PDF-'):
            raise ValueError('The file is not a valid PDF.')
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(data), strict=True)
        if reader.is_encrypted:
            raise ValueError('Upload a PDF without password protection.')
        if len(reader.pages) > 60:
            raise ValueError('Upload at most 60 pages at a time.')
        for number, page in enumerate(reader.pages, 1):
            text = page.extract_text(extraction_mode='layout') or ''
            if len(text.strip()) < 25:
                with tempfile.TemporaryDirectory() as tmp:
                    prefix = str(Path(tmp) / 'page')
                    subprocess.run(['pdftoppm', '-f', str(number), '-l', str(number),
                                    '-singlefile', '-scale-to', '2200', '-png', str(path), prefix],
                                   capture_output=True, timeout=20, check=True)
                    text = ocr(prefix + '.png')
            pages.append({'page': number, 'text': text})
    elif extension == '.docx':
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            if len(archive.infolist()) > 1500 or sum(x.file_size for x in archive.infolist()) > 30_000_000:
                raise ValueError('This document is too large to unpack safely.')
            if any('vbaProject' in x.filename for x in archive.infolist()):
                raise ValueError('Macro-enabled documents are not supported.')
            document = ElementTree.fromstring(archive.read('word/document.xml'))
            ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
            # Word pagination is layout-dependent. These are sections, not invented pages.
            text = '\n'.join(' '.join(p.itertext()) for p in document.findall('.//w:p', ns))
            pages = [{'page': 1, 'text': text}]
    elif extension in ('.png', '.jpg', '.jpeg'):
        expected = b'\x89PNG\r\n\x1a\n' if extension == '.png' else b'\xff\xd8\xff'
        if not data.startswith(expected):
            raise ValueError('The image format does not match its filename.')
        pages = [{'page': 1, 'text': ocr(path)}]
    elif extension == '.txt':
        pages = [{'page': 1, 'text': data.decode('utf-8')}]
    else:
        raise ValueError('Use PDF, DOCX, PNG, JPG or UTF-8 text.')
    if sum(len(p['text']) for p in pages) > MAX_TEXT:
        raise ValueError('The extracted document exceeds the text limit. Split it and try again.')
    if not any(p['text'].strip() for p in pages):
        raise ValueError('No readable text was found. Try a clearer scan.')
    return pages


def parse_date(text, year):
    from datetime import date, datetime
    match = re.search(r'\b(20\d{2}-\d{2}-\d{2})\b', text)
    if match:
        try:
            return date.fromisoformat(match[1]).isoformat(), ''
        except ValueError:
            return None, 'Invalid calendar date'
    months = r'(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:t(?:ember)?)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)'
    match = re.search(r'\b(' + months + r')\.?\s+(\d{1,2})(?:st|nd|rd|th)?(?:,?\s+(20\d{2}))?\b', text, re.I)
    if match:
        month, day, explicit = match.groups()
    else:
        match = re.search(r'\b(\d{1,2})\s+(' + months + r')\.?(?:\s+(20\d{2}))?\b', text, re.I)
        if match:
            day, month, explicit = match.groups()
    if match:
        y = int(explicit) if explicit else year
        if not y:
            return None, 'Confirm the term year'
        try:
            return date(y, datetime.strptime(month[:3].title(), '%b').month, int(day)).isoformat(), '' if explicit else 'Year uses your selected term'
        except ValueError:
            return None, 'Invalid calendar date'
    match = re.search(r'\b(\d{1,2})[/-](\d{1,2})(?:[/-](20\d{2}))?\b', text)
    if match:
        first, second = int(match[1]), int(match[2])
        if first <= 12 and second <= 12:
            return None, 'Ambiguous numeric date; choose the correct date'
        if not (match[3] or year):
            return None, 'Confirm the term year'
        try:
            return date(int(match[3] or year), first if second > 12 else second,
                        second if second > 12 else first).isoformat(), ''
        except ValueError:
            return None, 'Invalid calendar date'
    return None, 'Date not stated; review the source'


def candidates(pages, year):
    rows = []
    seen = set()
    for page in pages:
        lines = [line.strip() for line in page['text'].splitlines() if line.strip()]
        for i, line in enumerate(lines):
            match = re.search(r'\b(assignment|exam(?:ination)?|midterm|final\s+exam|lab(?:oratory)?|quiz|test|project|presentation|report)s?\b', line, re.I)
            if not match or len(line) > 800:
                continue
            # Combine wrapped table cells, but never swallow the next assessment.
            context = line
            if i + 1 < len(lines) and not re.search(r'\b(assignment|exam|midterm|lab|quiz|test|project|report)\b', lines[i+1], re.I):
                context += ' ' + lines[i+1]
            day, warning = parse_date(context, year)
            weights = re.findall(r'\b(\d{1,3}(?:\.\d+)?)\s*%', line)
            weight = float(weights[0]) if len(weights) == 1 and float(weights[0]) <= 100 else None
            clock = re.search(r'\b(\d{1,2}):(\d{2})\s*(a\.?m\.?|p\.?m\.?)?', context, re.I)
            time_value = None
            if clock:
                h, m = int(clock[1]), int(clock[2])
                suffix = (clock[3] or '').lower().replace('.', '')
                if suffix and 1 <= h <= 12:
                    h = h % 12 + (12 if suffix == 'pm' else 0)
                if 0 <= h <= 23 and 0 <= m <= 59:
                    time_value = f'{h:02d}:{m:02d}'
            kind = 'exam' if match[1].lower() in ('exam', 'examination', 'midterm', 'final exam', 'quiz', 'test') else 'lab' if match[1].lower().startswith('lab') else 'assignment'
            title = re.split(r'\s{2,}|\t|\|', line)[0].strip()[:240]
            fingerprint = (title.casefold(), day)
            if fingerprint in seen:
                continue
            seen.add(fingerprint)
            rows.append({'title': title, 'kind': kind, 'due_on': day, 'time': time_value,
                         'weight': weight, 'source_page': page['page'], 'evidence': context[:800],
                         'confidence': 'review' if warning else 'date found', 'warning': warning,
                         'selected': bool(day)})
    return rows[:200]


if __name__ == '__main__':
    try:
        # This worker parses only one temporary file and returns bounded JSON.
        import resource
        resource.setrlimit(resource.RLIMIT_AS, (512 * 1024 * 1024, 512 * 1024 * 1024))
        resource.setrlimit(resource.RLIMIT_CPU, (40, 40))
        print(json.dumps({'pages': extract(sys.argv[1], sys.argv[2])}))
    except Exception as exc:
        print(json.dumps({'error': str(exc)[:250]}))
        sys.exit(1)
