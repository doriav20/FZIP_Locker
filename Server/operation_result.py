from enum import Enum


class OperationResultType(Enum):
    SUCCEEDED = 0
    DETAILS_ERROR = 1
    CONNECTION_ERROR = 2
    UNKNOWN_ERROR = 3
