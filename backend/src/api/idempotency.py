import hashlib
import json
from typing import Optional

from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from src.database.models import RemoteOperation
from src.database.session import SessionLocal


MUTATING_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
IDEMPOTENCY_HEADER = "Idempotency-Key"


def _resolve_user_id(request: Request) -> int:
    raw_value = request.headers.get("X-User-ID")
    if raw_value:
        try:
            return int(raw_value)
        except ValueError:
            pass
    query_value = request.query_params.get("user_id")
    if query_value:
        try:
            return int(query_value)
        except ValueError:
            pass
    return 1


def _request_hash(request: Request, body: bytes, user_id: int) -> str:
    normalized_body: object
    if body:
        try:
            normalized_body = json.loads(body)
        except (json.JSONDecodeError, UnicodeDecodeError):
            normalized_body = body.decode("utf-8", errors="replace")
    else:
        normalized_body = None
    canonical = json.dumps(
        {
            "method": request.method,
            "path": request.url.path,
            "query": sorted(request.query_params.multi_items()),
            "user_id": user_id,
            "body": normalized_body,
        },
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _conflict(detail: str, key: str) -> JSONResponse:
    return JSONResponse(
        status_code=409,
        content={
            "status": "conflict",
            "detail": detail,
            "idempotency_key": key,
        },
    )


class IdempotencyMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        key = request.headers.get(IDEMPOTENCY_HEADER)
        if request.method not in MUTATING_METHODS or not key:
            return await call_next(request)
        if request.url.path.startswith("/api/v1/auth/"):
            return await call_next(request)
        if (
            not request.headers.get("Authorization")
            and not request.headers.get("X-User-ID")
            and not request.cookies.get("habit_session")
        ):
            return await call_next(request)
        if len(key) > 100:
            return JSONResponse(
                status_code=400,
                content={"detail": "Idempotency-Key must be at most 100 characters."},
            )

        body = await request.body()
        user_id = _resolve_user_id(request)
        request_hash = _request_hash(request, body, user_id)

        existing = self._get_operation(user_id, key)
        if existing:
            return self._existing_response(existing, request_hash)

        db = SessionLocal()
        try:
            operation = RemoteOperation(
                user_id=user_id,
                idempotency_key=key,
                request_hash=request_hash,
                method=request.method,
                path=request.url.path,
                status="in_progress",
            )
            db.add(operation)
            db.commit()
        except IntegrityError:
            db.rollback()
            existing = (
                db.query(RemoteOperation)
                .filter_by(user_id=user_id, idempotency_key=key)
                .first()
            )
            if existing:
                return self._existing_response(existing, request_hash)
            raise
        finally:
            db.close()

        try:
            response = await call_next(request)
            chunks = [chunk async for chunk in response.body_iterator]
            response_body = b"".join(chunks)
            self._complete_operation(
                user_id=user_id,
                key=key,
                http_status=response.status_code,
                response_body=response_body.decode("utf-8", errors="replace"),
            )
            headers = dict(response.headers)
            headers.pop("content-length", None)
            return Response(
                content=response_body,
                status_code=response.status_code,
                headers=headers,
                media_type=response.media_type,
                background=response.background,
            )
        except Exception:
            self._mark_failed(user_id, key)
            raise

    @staticmethod
    def _get_operation(user_id: int, key: str) -> Optional[RemoteOperation]:
        db = SessionLocal()
        try:
            return (
                db.query(RemoteOperation)
                .filter_by(user_id=user_id, idempotency_key=key)
                .first()
            )
        finally:
            db.close()

    @staticmethod
    def _existing_response(operation: RemoteOperation, request_hash: str) -> Response:
        if operation.request_hash != request_hash:
            return _conflict(
                "This idempotency key was already used with a different request.",
                operation.idempotency_key,
            )
        if operation.status != "completed" or operation.http_status is None:
            return _conflict(
                "The operation outcome is uncertain. Inspect it before retrying.",
                operation.idempotency_key,
            )
        return Response(
            content=operation.response_body or "",
            status_code=operation.http_status,
            media_type="application/json",
            headers={"Idempotency-Replayed": "true"},
        )

    @staticmethod
    def _complete_operation(
        user_id: int, key: str, http_status: int, response_body: str
    ) -> None:
        db = SessionLocal()
        try:
            operation = (
                db.query(RemoteOperation)
                .filter_by(user_id=user_id, idempotency_key=key)
                .first()
            )
            if operation:
                operation.status = "completed"
                operation.http_status = http_status
                operation.response_body = response_body
                db.commit()
        finally:
            db.close()

    @staticmethod
    def _mark_failed(user_id: int, key: str) -> None:
        db = SessionLocal()
        try:
            operation = (
                db.query(RemoteOperation)
                .filter_by(user_id=user_id, idempotency_key=key)
                .first()
            )
            if operation:
                operation.status = "uncertain"
                db.commit()
        finally:
            db.close()
