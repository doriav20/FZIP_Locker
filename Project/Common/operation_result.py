from enum import Enum


# from abc import ABC as AbstractBaseClass, ABCMeta as AbstractBaseClassMeta, abstractmethod


class OperationResultType(Enum):
    SUCCEEDED = 0
    DETAILS_ERROR = 1
    CONNECTION_ERROR = 2
    UNKNOWN_ERROR = 3
# class OperationResult(AbstractBaseClass):
#     @abstractmethod
#     def get_error_type(self):
#         raise NotImplementedError("get_error_type is an Abstract Method")
#         # return None
#
#
# class OperationSucceeded(OperationResult):
#     def __init__(self):
#         super().__init__()
#
#     def get_error_type(self):
#         return OperationResultType.SUCCEEDED
#
#
# class OperationFailed(OperationResult, metaclass=AbstractBaseClassMeta):
#     def __init__(self):
#         super().__init__()
#
#     @abstractmethod
#     def get_error_type(self):
#         raise NotImplementedError("get_error_type is an Abstract Method")
#         # return None
#
#
# class OperationFailedDetailsError(OperationFailed):
#     def __init__(self):
#         super().__init__()
#
#     def get_error_type(self):
#         return OperationResultType.DETAILS_ERROR
#
#
# class OperationFailedConnectionError(OperationFailed):
#     def __init__(self):
#         super().__init__()
#
#     def get_error_type(self):
#         return OperationResultType.CONNECTION_ERROR
