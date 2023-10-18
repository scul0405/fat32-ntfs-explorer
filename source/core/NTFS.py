from utils import open_windows_partition

class NTFS:
    def __init__(self, drive_name: str) -> None:
        self.raw_data = None
        try:
            with open_windows_partition(drive_name) as drive:
                self.raw_data = drive.read(512)
        except FileNotFoundError:
            print("Drive not found")
            exit(1)