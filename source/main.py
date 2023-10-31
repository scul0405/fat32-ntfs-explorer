# from [folder].[file.py] import [class]


from core.NTFS import NTFS
from core.FAT32 import FAT32_display

# ntfs = NTFS("F")
# ntfs.print_raw_bpb()
# ntfs.print_bst_info()
# # get standard NTFS file system metadata files (Doc: page 268-269)
# for i in range(0, 12):
#     ntfs.extract_mft()


FAT32_display()