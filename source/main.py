# from [folder].[file.py] import [class]
from core.NTFS import NTFS

ntfs = NTFS("D")
print(ntfs.boot_sector)
