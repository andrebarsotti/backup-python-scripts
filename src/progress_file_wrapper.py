#!/usr/bin/env python3
"""
Progress tracking wrapper for file uploads.

Provides a file-like object wrapper that updates a progress bar during reads.
"""

__all__ = ['ProgressFileWrapper']


class ProgressFileWrapper:
    """
    A file wrapper to integrate reading with a progress bar.
    """
    def __init__(self, file, progress_bar):
        self.file = file
        self.progress_bar = progress_bar

    def read(self, size=-1):
        """
        Read from the file and update the progress bar.

        :param size: Number of bytes to read. Defaults to -1 (read all).
        :return: Data read from the file.
        """
        data = self.file.read(size)
        self.progress_bar.update(len(data))
        return data

    def tell(self):
        """
        Returns the current stream position.

        :return: The current position in the file.
        """
        return self.file.tell()
