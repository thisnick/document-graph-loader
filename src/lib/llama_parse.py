import os
import time
from typing import Union, Literal, TypedDict, Optional, List, Dict, Any
from io import BufferedReader, BytesIO
import requests

class TimeoutError(Exception):
    pass

class UploadResponse(TypedDict):
    id: str
    status: Literal['PENDING', 'SUCCESS', 'ERROR', 'CANCELED']

class JobMetadata(TypedDict):
    credits_used: int
    job_credits_usage: int
    job_is_cache_hit: bool
    job_pages: int

class JobStatus(TypedDict):
    status: Literal['PENDING', 'SUCCESS', 'ERROR', 'CANCELED']

class Image(TypedDict):
    name: str
    height: int
    width: int
    x: int
    y: int
    original_width: int
    original_height: int

class BBox(TypedDict):
    x: int
    y: int
    w: int
    h: int

class Item(TypedDict, total=False):
    type: Literal['heading', 'table', 'text']
    lvl: Optional[int]
    value: Optional[str]
    md: Optional[str]
    rows: Optional[List[List[str]]]
    isPerfectTable: Optional[bool]
    csv: Optional[str]
    bBox: Optional[BBox]

class Page(TypedDict):
    page: int
    status: str
    text: str
    md: str
    images: List[Image]
    items: List[Item]

class MarkdownJobResult(TypedDict):
    job_metadata: JobMetadata
    markdown: str

class JsonJobResult(TypedDict):
    pages: List[Page]
    job_metadata: JobMetadata

class LlamaParseClient:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = 'https://api.cloud.llamaindex.ai/api/parsing'

    def upload_file(
        self,
        file_content: Union[BufferedReader, bytes, str],
        file_name: str,
        mime_type: str,
        **options
    ) -> UploadResponse:
        main_mime_type = mime_type.split(';')[0]
        if main_mime_type not in SUPPORTED_MIME_TYPES:
            raise ValueError(f"Unsupported mime type: {main_mime_type}")

        # Convert string content to bytes if necessary
        if isinstance(file_content, str):
            file_content = file_content.encode('utf-8')

        files = {
            'file': (file_name, file_content, main_mime_type)
        }

        # Prepare form data
        data = {k: str(v) for k, v in options.items() if v is not None}
        if 'page_separator' not in data:
            data['page_separator'] = "\n\n---\n\n"

        headers = {
            'Accept': 'application/json',
            'Authorization': f'Bearer {self.api_key}'
        }

        response = requests.post(
            f"{self.base_url}/upload",
            headers=headers,
            files=files,
            data=data
        )
        response.raise_for_status()
        return response.json()

    def get_job(self, job_id: str) -> JobStatus:
        headers = {
            'Accept': 'application/json',
            'Authorization': f'Bearer {self.api_key}'
        }
        response = requests.get(
            f"{self.base_url}/job/{job_id}",
            headers=headers
        )
        response.raise_for_status()
        return response.json()

    def get_result(self, job_id: str, result_type: Literal['markdown', 'json']):
        url = f"{self.base_url}/job/{job_id}/result/{result_type}"
        headers = {
            'Accept': 'application/json',
            'Authorization': f'Bearer {self.api_key}'
        }
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json()

    def get_result_in_json(self, job_id: str) -> JsonJobResult:
        return self.get_result(job_id, 'json')

    def get_result_in_markdown(self, job_id: str) -> MarkdownJobResult:
        return self.get_result(job_id, 'markdown')

    def process_file(
        self,
        file_content: Union[BufferedReader, bytes, str],
        file_name: str,
        mime_type: str,
        result_type: Literal['markdown', 'json'] = 'markdown',
        **options
    ):
        try:
            upload_response = self.upload_file(file_content, file_name, mime_type, **options)
            job_id = upload_response['id']
            print(f"Job created with ID: {job_id}")

            elapsed_time = 0
            timeout = options.get('timeout', 300000)  # Default 5 minutes

            while True:
                time.sleep(5)
                job_status = self.get_job(job_id)
                print(f"Job status: {job_status['status']}")
                elapsed_time += 5000

                if elapsed_time >= timeout:
                    raise TimeoutError('Timeout exceeded while waiting for job to complete')

                if job_status['status'] != 'PENDING':
                    break

            if job_status['status'] == 'SUCCESS':
                return self.get_result(job_id, result_type)
            else:
                raise Exception(f"Job failed with status: {job_status['status']}")

        except Exception as error:
            print(f"Error processing file: {str(error)}")
            raise

# The SUPPORTED_MIME_TYPES list remains the same as in the TypeScript version
SUPPORTED_MIME_TYPES = [
  "application/pdf",
  "application/x-t602",
  "application/x-abiword",
  "image/cgm",
  "application/x-cwk",
  "application/msword",
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
  "application/vnd.ms-word.document.macroenabled.12",
  "application/vnd.ms-word.template.macroenabled.12",
  "application/x-hwp",
  "application/vnd.apple.keynote",
  "application/vnd.lotus-wordpro",
  "application/x-lotus-microsoft-work",
  "application/vnd.apple.pages",
  "application/vnd.powerbuilder6",
  "application/vnd.ms-powerpoint",
  "application/vnd.ms-powerpoint.presentation.macroenabled.12",
  "application/vnd.openxmlformats-officedocument.presentationml.presentation",
  "application/vnd.ms-powerpoint.template.macroenabled.12",
  "application/vnd.openxmlformats-officedocument.presentationml.template",
  "application/rtf",
  "application/vnd.stardivision.draw",
  "application/vnd.stardivision.impress",
  "application/vnd.stardivision.writer",
  "application/vnd.stardivision.writer-global",
  "application/vnd.sun.xml.impress.template",
  "application/vnd.sun.xml.impress",
  "application/vnd.sun.xml.writer",
  "application/vnd.sun.xml.writer.template",
  "application/vnd.sun.xml.writer.global",
  "text/plain",
  "application/x-uof",
  "application/vnd.uoml+xml",
  "application/vnd.wordperfect",
  "application/vnd.ms-works",
  "application/xml",
  "application/epub+zip",
  "image/jpeg",
  "image/png",
  "image/gif",
  "image/bmp",
  "image/svg+xml",
  "image/tiff",
  "image/webp",
  "text/html",
  "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
  "application/vnd.ms-excel",
  "application/vnd.ms-excel.sheet.macroenabled.12",
  "application/vnd.ms-excel.sheet.binary.macroenabled.12",
  "text/csv",
  "video/x-dv",
  "text/spreadsheet",
  "application/x-prn",
  "application/vnd.apple.numbers",
  "application/x-et",
  "application/vnd.oasis.opendocument.spreadsheet",
  "application/x-dbf",
  "application/vnd.lotus-1-2-3",
  "application/x-quattro-pro",
  "application/x-eth",
  "text/tab-separated-values"
]
