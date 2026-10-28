"""Consistent browser errors and non-secret API validation responses."""
import logging
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException
from app.ui import templates
log=logging.getLogger(__name__)
TITLES={400:'Check your request',401:'Sign in to continue',403:'Access is restricted',404:'Page not found',409:'This record changed',413:'Upload is too large',422:'Check the form',429:'Try again shortly',500:'Something went wrong',503:'Temporarily unavailable'}

def wants_json(request):
    return request.url.path.startswith('/api/') or 'application/json' in request.headers.get('accept','') or 'application/json' in request.headers.get('content-type','')

def error_response(request,status,detail='',headers=None):
    if not isinstance(detail,str):detail='Check the form and try again.'
    if wants_json(request):return JSONResponse({'detail':detail or TITLES.get(status,'Request failed')},status_code=status,headers=headers)
    return templates.TemplateResponse(request,'error.html',{'request':request,'status':status,'error_title':TITLES.get(status,'Unable to continue'),'detail':detail},status_code=status,headers=headers)

def install_error_handlers(app):
    @app.exception_handler(HTTPException)
    async def http_error(request,exc):return error_response(request,exc.status_code,exc.detail,exc.headers)
    @app.exception_handler(RequestValidationError)
    async def validation_error(request,exc):
        # Do not echo submitted values, passwords, email addresses or validation internals.
        return error_response(request,422,'Check that required fields, dates and numbers are valid. Your saved records have not changed.')
    @app.exception_handler(ValueError)
    async def invalid_value(request,exc):return error_response(request,422,'Check the dates, numbers and required fields, then try again.')
    @app.exception_handler(Exception)
    async def unexpected_error(request,exc):
        log.exception('Request failed: %s %s',request.method,request.url.path,exc_info=exc)
        return error_response(request,500,'Please try again. If this keeps happening, contact the administrator.')
