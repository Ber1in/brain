# Copyright (C) 2021 - 2025, Shanghai Yunsilicon Technology Co., Ltd.
# All rights reserved.

# Copyright (C) 2021 - 2025, Shanghai Yunsilicon Technology Co., Ltd.
# All rights reserved.

import logging
from typing import Any, Optional

LOG = logging.getLogger(__name__)


class BrainException(Exception):
    """Base manual Exception

    To correctly use this class, inherit from it and define
    a 'message' property. That message will get printf'd
    with the keyword arguments provided to the constructor.

    """
    message = "An unknown exception occurred."
    code = 500
    headers = {}
    safe = True

    def __init__(self, message: Optional[str] = None, **kwargs: Any):
        self.kwargs = kwargs

        if 'code' not in self.kwargs:
            try:
                self.kwargs['code'] = self.code
            except AttributeError:
                pass

        if not message:
            try:
                message = self.message % kwargs
            except Exception:
                # kwargs doesn't match a variable in the message
                # log the issue and the kwargs
                LOG.exception('Exception in string format operation')
                for name, value in kwargs.items():
                    LOG.error(f"{name}: {value}")
                # at least get the core message out if something happened
                message = self.message
        elif isinstance(message, Exception):
            message = str(message)

        self.msg = message
        super().__init__(message)


class BackstoreImageAPIError(BrainException):
    message = "An image error occurs due to: %(reason)s"


class VblkCreateException(BrainException):
    message = "Failed to create virtblk due to: %(reason)s"


class VblkDeleteException(BrainException):
    message = "Failed to delete virtblk due to: %(reason)s"


class CheckPointSaveException(BrainException):
    message = "Failed to save checkpoint due to: %(reason)s"
