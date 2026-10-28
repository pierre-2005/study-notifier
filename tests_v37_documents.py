"""Local PDF/DOCX/OCR extraction and optional AI contract without a live API key."""
from pathlib import Path
import io
import json
import os
import unittest
from unittest.mock import patch
import zipfile
from PIL import Image,ImageDraw,ImageFont
from pypdf import PdfWriter
from pypdf.generic import DictionaryObject,NameObject,DecodedStreamObject
from app.course_import import parse_upload
from app.outline_parse import candidates,parse_date
from app import outline_ai


class OutlineFormats(unittest.TestCase):
    def test_text_pdf_and_docx(self):
        writer=PdfWriter();page=writer.add_blank_page(width=612,height=792)
        font=DictionaryObject({NameObject('/Type'):NameObject('/Font'),NameObject('/Subtype'):NameObject('/Type1'),NameObject('/BaseFont'):NameObject('/Helvetica')})
        page[NameObject('/Resources')]=DictionaryObject({NameObject('/Font'):DictionaryObject({NameObject('/F1'):writer._add_object(font)})})
        stream=DecodedStreamObject();stream.set_data(b'BT /F1 14 Tf 40 740 Td (Assignment 1 | November 12, 2026 | 20%) Tj ET')
        page[NameObject('/Contents')]=writer._add_object(stream);out=io.BytesIO();writer.write(out)
        rows=candidates(parse_upload(out.getvalue(),'.pdf'),2026)
        self.assertEqual(rows[0]['due_on'],'2026-11-12');self.assertEqual(rows[0]['source_page'],1)
        document=io.BytesIO()
        with zipfile.ZipFile(document,'w') as z:
            z.writestr('word/document.xml','<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>Lab 2 | November 20, 2026 | 10%</w:t></w:r></w:p></w:body></w:document>')
        self.assertEqual(candidates(parse_upload(document.getvalue(),'.docx'),2026)[0]['kind'],'lab')
    def test_image_and_scanned_pdf_ocr(self):
        image=Image.new('RGB',(1500,300),'white');draw=ImageDraw.Draw(image)
        font=ImageFont.truetype(next(str(p) for p in [Path('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'),Path('C:/Windows/Fonts/arial.ttf')] if p.is_file()),38)
        draw.text((35,75),'Assignment 3 | November 25, 2026 | 15%',font=font,fill='black')
        for extension,format in (('.png','PNG'),('.jpg','JPEG'),('.pdf','PDF')):
            out=io.BytesIO();image.save(out,format=format)
            rows=candidates(parse_upload(out.getvalue(),extension),2026)
            self.assertTrue(rows,extension);self.assertEqual(rows[0]['due_on'],'2026-11-25',rows)
    def test_dates_and_format_rejection(self):
        self.assertIsNone(parse_date('11/12/2026',2026)[0])
        self.assertIsNone(parse_date('February 30, 2026',2026)[0])
        self.assertEqual(parse_date('November 12',2026)[0],'2026-11-12')
        for extension in ('.pdf','.png','.jpg','.docx'):
            with self.assertRaises(ValueError):parse_upload(b'invalid bytes',extension)
    def test_ai_schema_consent_evidence_and_failure(self):
        pages=[{'page':1,'text':'Assignment 1 November 12, 2026 20%'}]
        row={'title':'Assignment 1','kind':'assignment','due_on':'2026-11-12','time':None,'weight':20,
             'source_page':1,'evidence':pages[0]['text']}
        def response(value):
            mock=unittest.mock.Mock(status_code=200)
            mock.json.return_value={'status':'completed','output':[{'type':'message','content':[{'type':'output_text','text':json.dumps(value)}]}]}
            return mock
        with patch.dict(os.environ,{'MLO_OUTLINE_AI_ENABLED':'false'},clear=False):
            self.assertFalse(outline_ai.enabled())
            with self.assertRaises(ValueError):outline_ai.extract(pages,2026)
        with patch.dict(os.environ,{'MLO_OUTLINE_AI_ENABLED':'true','OPENAI_API_KEY':'test-only-no-network','MLO_OUTLINE_AI_MODEL':'fixture-model'},clear=False),patch('app.outline_ai.requests.post') as send:
            send.return_value=response({'assessments':[row]})
            result=outline_ai.extract(pages,2026);self.assertFalse(result[0]['selected'])
            request=send.call_args.kwargs['json'];self.assertFalse(request['store']);self.assertTrue(request['text']['format']['strict']);self.assertNotIn('tools',request)
            send.return_value=response({'assessments':[{**row,'evidence':'fabricated quotation'}]})
            self.assertIsNone(outline_ai.extract(pages,2026)[0]['due_on'])
            send.return_value=response({'assessments':['malformed']})
            with self.assertRaises(ValueError):outline_ai.extract(pages,2026)
            send.return_value=unittest.mock.Mock(status_code=429)
            with self.assertRaises(ValueError):outline_ai.extract(pages,2026)


if __name__=='__main__':unittest.main(verbosity=2)
