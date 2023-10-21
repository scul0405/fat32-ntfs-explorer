# from [folder].[file.py] import [class]


from core.NTFS import NTFS
from core.FAT32 import FAT32
ntfs = NTFS("E")
ntfs.print_raw_bpb()

fat32 = FAT32("F")
fat32.print_raw_bst()
fat32.print_bst_info()
