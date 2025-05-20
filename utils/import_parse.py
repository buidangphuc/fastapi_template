#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import importlib

from functools import lru_cache
from typing import Any, Type, TypeVar

from common.exception import errors
from common.log import log

T = TypeVar('T')


@lru_cache(maxsize=512)
def import_module_cached(module_path: str) -> Any:
    """
    Cache imported module

    :param module_path: Module path
    :return:
    """
    return importlib.import_module(module_path)


def dynamic_import_data_model(module_path: str) -> Type[T]:
    """
    Dynamically import data model

    :param module_path: Module path, format is 'module_path.class_name'
    :return:
    """
    try:
        module_path, class_name = module_path.rsplit('.', 1)
        module = import_module_cached(module_path)
        return getattr(module, class_name)
    except (ImportError, AttributeError) as e:
        log.error(f'Failed to dynamically import data model: {e}')
        raise errors.ServerError(msg='Failed to dynamically parse data model, please contact system administrator')
