from contextlib import asynccontextmanager

from fastapi import FastAPI, Request

from app.router import router
from common.exception.exception_handler import register_exception
from common.log import log
from common.response.response_schema import CustomResponse, response_base
from core.conf import settings
from utils.serializers import MsgSpecJSONResponse
from utils.string import generate_unique_id


def register_router(app: FastAPI):
    """
    Router.

    :param app: FastAPI
    :return:
    """

    # API
    app.include_router(router)


def register_middleware(app: FastAPI):
    """
    Middleware, execution order from bottom to top.

    :param app:
    :return:
    """
    # Opera log
    # app.add_middleware(OperaLogMiddleware)

    # CORS middleware
    if settings.MIDDLEWARE_CORS:
        log.info("CORS enabled")
        from fastapi.middleware.cors import CORSMiddleware

        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.CORS_ALLOWED_ORIGINS,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )


def register_app(init_db: bool = True) -> FastAPI:
    if init_db:

        @asynccontextmanager
        async def lifespan(app: FastAPI):
            from database.db import check_database_connection, init_db

            await check_database_connection(
                retry_interval=settings.DATABASE_RETRY_INTERVAL,
                max_retries=settings.DATABASE_MAX_RETRIES,
            )
            await init_db()

            # Initialize dev data if in development environment
            if settings.ENVIRONMENT.lower() == "dev":
                try:
                    log.info(
                        "Development environment detected, initializing development data..."
                    )
                    from scripts.init_data import init_dev_data

                    await init_dev_data()
                except Exception as e:
                    log.error(f"Failed to initialize development data: {str(e)}")

            yield

    app = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.VERSION,
        description=settings.DESCRIPTION,
        default_response_class=MsgSpecJSONResponse,
        lifespan=lifespan,
        generate_unique_id_function=generate_unique_id,
        root_path=settings.FASTAPI_ROOT_PATH,
        docs_url=settings.FASTAPI_DOCS_URL,
        redoc_url=settings.FASTAPI_REDOCS_URL,
        openapi_url=settings.FASTAPI_OPENAPI_URL,
    )

    register_middleware(app)
    register_router(app)
    register_exception(app)

    @app.get("/health", tags=["health"])
    async def health(request: Request):
        # First check database connection
        from database.db import check_database_connection

        db_status, error_msg = await check_database_connection(
            max_retries=1, retry_interval=0, for_health_check=True
        )

        if not db_status:
            return await response_base.fail(
                res=CustomResponse(code=503, message="Database connection failed"),
                data={"error": error_msg},
            )

        # If database is fine, check API status
        try:
            # Additional API health checks can be added here
            return await response_base.success(
                data={"database": "connected", "api": "healthy"},
            )
        except Exception as e:
            return await response_base.fail(
                data={"error": str(e)},
            )

    return app
