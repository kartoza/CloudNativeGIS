# coding=utf-8
"""Cloud Native GIS."""
import mmap


class RangeRequestReader:
    """Read file using mmap."""

    def __init__(self, filepath):
        """Initialize RangeRequestReader."""
        self.filepath = filepath
        self.file = open(filepath, 'rb')
        try:
            self.mmap = mmap.mmap(
                self.file.fileno(), 0, access=mmap.ACCESS_READ
            )
        except Exception as e:
            self.file.close()
            raise OSError(f"Failed to create memory map: {e}")

    def read_range(self, offset, length):
        """Read range bytes."""
        if offset < 0:
            raise ValueError("Offset cannot be negative")
        file_size = len(self.mmap)
        if offset >= file_size:
            raise ValueError("Offset exceeds file size")

        # Adjust length if it would exceed file size
        length = min(length, file_size - offset)

        self.mmap.seek(offset)
        return self.mmap.read(length)

    def read_all(self):
        """Read all bytes."""
        self.mmap.seek(0)
        return self.mmap.read()

    def close(self):
        """Close resources."""
        if hasattr(self, 'mmap') and self.mmap:
            self.mmap.close()
        if hasattr(self, 'file') and self.file:
            self.file.close()
