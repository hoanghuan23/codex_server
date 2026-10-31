"""Web local: python3 -m uvicorn ui_server:app --host 127.0.0.1 --port 8001."""
import asyncio
import logging
import shutil
import tempfile
from contextlib import asynccontextmanager, suppress
from pathlib import Path
from uuid import uuid4

from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from starlette.middleware.trustedhost import TrustedHostMiddleware

from map_input import SUPPORTED_EXTENSIONS, read_input
from map_pipeline import BASE, CHART_LABELS, MapClient, PipelineError, Settings, publish_output


load_dotenv(BASE / '.env')
logger = logging.getLogger(__name__)
WEB_FILES = {'index.html': 'text/html', 'style.css': 'text/css', 'app.js': 'text/javascript'}
STATIC = BASE / 'ui'


def create_app(settings=None):
    settings = settings or Settings.from_env()
    jobs = {}
    lock = asyncio.Lock()
    task = None
    active_id = None

    @asynccontextmanager
    async def lifespan(app):
        yield
        if task is not None and not task.done():
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task

    app = FastAPI(title='Tạo bản đồ từ file', lifespan=lifespan)
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=['127.0.0.1', 'localhost', '[::1]'])
    app.state.settings = settings
    app.state.jobs = jobs

    @app.middleware('http')
    async def check_origin(request: Request, call_next):
        origin = request.headers.get('origin')
        if request.method == 'POST' and origin and origin != str(request.base_url).rstrip('/'):
            return JSONResponse({'detail': 'Chỉ nhận yêu cầu từ giao diện local.'}, status_code=403)
        return await call_next(request)

    @app.get('/', include_in_schema=False)
    async def index():
        return FileResponse(STATIC / 'index.html', media_type='text/html')

    @app.get('/ui/{filename}', include_in_schema=False)
    async def static_file(filename: str):
        if filename not in ('app.js', 'style.css'):
            raise HTTPException(404, 'Không tìm thấy tài nguyên.')
        return FileResponse(STATIC / filename, media_type=WEB_FILES[filename])

    async def run_job(job, directory, path):
        nonlocal active_id
        try:
            document = await asyncio.to_thread(read_input, path, job['file_name'])
            job.update(status='analyzing', message='Đang phân tích và chọn loại bản đồ…')
            client = MapClient(settings)
            analysis = await asyncio.to_thread(client.classify, document)
            job['analysis'] = analysis.model_dump()
            if analysis.selectedChart is None:
                job.update(status='needs_data', message='Chưa đủ dữ liệu để dựng bản đồ.',
                           error='\n'.join(analysis.missingData))
                return
            job.update(status='generating', chart_label=CHART_LABELS[analysis.selectedChart],
                       message='Đang dựng bản đồ và tìm dữ liệu địa lý cần thiết…')
            raw = await asyncio.to_thread(client.generate, document, analysis)
            job.update(status='validating', message='Đang kiểm tra HTML, CSS và JavaScript…')
            output, warnings = await asyncio.to_thread(
                publish_output, raw, job['file_name'], job['job_id'], settings)
            job.update(status='completed', message='Bản đồ đã sẵn sàng.',
                       output_dir=str(output), preview_url=f"/outputs/{job['job_id']}/index.html",
                       warnings=warnings)
        except (ValueError, PipelineError) as exc:
            job.update(status='failed', message='Không tạo được bản đồ.', error=str(exc))
        except asyncio.CancelledError:
            job.update(status='failed', message='Tác vụ đã dừng.', error='Ứng dụng local đang tắt.')
            raise
        except Exception:
            logger.exception('Map job %s failed', job['job_id'])
            job.update(status='failed', message='Không tạo được bản đồ.',
                       error='Có lỗi xử lý nội bộ. Xem terminal của ứng dụng local để biết chi tiết.')
        finally:
            shutil.rmtree(directory, ignore_errors=True)
            active_id = None
            lock.release()

    @app.post('/api/jobs', status_code=202)
    async def create_job(file: UploadFile = File(...)):
        nonlocal task, active_id
        if lock.locked():
            await file.close()
            raise HTTPException(409, {'message': 'Đang có một tác vụ chạy. Hãy chờ tác vụ hoàn tất.',
                                      'job_id': active_id})
        if not settings.api_token:
            await file.close()
            raise HTTPException(503, 'Thiếu CODEX_API_TOKEN trong môi trường hoặc file .env.')
        filename = (file.filename or '').replace('\\', '/').rsplit('/', 1)[-1]
        extension = Path(filename).suffix.lower()
        if extension not in SUPPORTED_EXTENSIONS:
            await file.close()
            raise HTTPException(400, 'Chỉ hỗ trợ .geojson, .json (GeoJSON), .xlsx, .docx và .txt.')
        await lock.acquire()
        directory = None
        handed_off = False
        try:
            directory = Path(tempfile.mkdtemp(prefix='map-upload-'))
            path = directory / ('input' + extension)
            size = 0
            with path.open('wb') as target:
                while chunk := await file.read(1024 * 1024):
                    size += len(chunk)
                    if size > settings.max_upload_bytes:
                        limit = settings.max_upload_bytes / (1024 * 1024)
                        raise HTTPException(413, f'File vượt giới hạn {limit:g} MB.')
                    target.write(chunk)
            if size == 0:
                raise HTTPException(400, 'File tải lên rỗng.')
            job_id = uuid4().hex[:12]
            job = {'job_id': job_id, 'file_name': filename, 'status': 'reading',
                   'message': 'Đang đọc dữ liệu trong file…', 'analysis': None,
                   'chart_label': None, 'output_dir': None, 'preview_url': None, 'error': None}
            jobs[job_id] = job
            active_id = job_id
            task = asyncio.create_task(run_job(job, directory, path))
            handed_off = True
            return {'job_id': job_id}
        finally:
            await file.close()
            if not handed_off:
                if directory is not None:
                    shutil.rmtree(directory, ignore_errors=True)
                lock.release()

    @app.get('/api/jobs/{job_id}')
    async def get_job(job_id: str):
        if job_id not in jobs:
            raise HTTPException(404, 'Không tìm thấy tác vụ. Ứng dụng có thể đã được khởi động lại.')
        return dict(jobs[job_id])

    @app.get('/outputs/{job_id}/{filename}', include_in_schema=False)
    async def output_file(job_id: str, filename: str):
        job = jobs.get(job_id)
        if filename not in WEB_FILES or not job or job['status'] != 'completed':
            raise HTTPException(404, 'Không tìm thấy file kết quả.')
        root = Path(job['output_dir']).resolve()
        path = root / filename
        if path.is_symlink() or not path.is_file() or not root.is_relative_to(settings.output_root.resolve()):
            raise HTTPException(404, 'Không tìm thấy file kết quả.')
        return FileResponse(path, media_type=WEB_FILES[filename], headers={'Cache-Control': 'no-store'})

    return app


app = create_app()
