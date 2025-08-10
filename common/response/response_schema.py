from typing import Any, Generic, TypeVar

from pydantic import BaseModel

from common.response.response_code import CustomResponse, CustomResponseCode

SchemaT = TypeVar("SchemaT")


class ResponseModel(BaseModel):
    code: int = CustomResponseCode.HTTP_200.code
    message: str = CustomResponseCode.HTTP_200.message
    data: Any | None = None


class ResponseSchemaModel(ResponseModel, Generic[SchemaT]):
    """
    包含返回数据 schema 的通用型统一返回模型，仅适用于非分页接口

    示例::

        @router.get('/test', response_model=ResponseSchemaModel[GetApiDetail])
        def test():
            return ResponseSchemaModel[GetApiDetail](data=GetApiDetail(...))


        @router.get('/test')
        def test() -> ResponseSchemaModel[GetApiDetail]:
            return ResponseSchemaModel[GetApiDetail](data=GetApiDetail(...))


        @router.get('/test')
        def test() -> ResponseSchemaModel[GetApiDetail]:
            res = CustomResponseCode.HTTP_200
            return ResponseSchemaModel[GetApiDetail](code=res.code, msg=res.msg, data=GetApiDetail(...))
    """

    data: SchemaT


class ResponseBase:
    @staticmethod
    async def __response(
        *, res: CustomResponseCode | CustomResponse = None, data: Any | None = None
    ):
        return ResponseModel(code=res.code, message=res.message, data=data)

    async def success(
        self,
        *,
        res: CustomResponseCode | CustomResponse = CustomResponseCode.HTTP_200,
        data: Any | None = None,
    ) -> ResponseModel:
        return await self.__response(res=res, data=data)

    async def fail(
        self,
        *,
        res: CustomResponseCode | CustomResponse = CustomResponseCode.HTTP_400,
        data: Any = None,
    ) -> ResponseModel:
        return await self.__response(res=res, data=data)


response_base = ResponseBase()
