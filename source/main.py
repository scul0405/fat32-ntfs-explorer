# from [folder].[file.py] import [class]


from core.NTFS import NTFS
from core.FAT32 import FAT32

ntfs = NTFS("E")
# ntfs.print_raw_bpb()
# ntfs.print_bst_info()
# # get standard NTFS file system metadata files (Doc: page 268-269)
# for i in range(0, 14):
#     ntfs.extract_mft()
for i in range(0, 16):
    try:
        ntfs.__extract_mft__()
    except Exception as e:
        print(i, e)
# fat32 = FAT32("F")
# fat32.print_raw_bst()
# fat32.print_bst_info()
