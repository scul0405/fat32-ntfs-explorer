# from [folder].[file.py] import [class]


from core.NTFS import NTFS
from core.FAT32 import FAT32

# ntfs = NTFS("F")
# ntfs.print_raw_bpb()
# ntfs.print_bst_info()
# # get standard NTFS file system metadata files (Doc: page 268-269)
# for i in range(0, 12):
#     ntfs.extract_mft()

fat32 = FAT32("E")
# print('RDET')
# fat32.print_table_offset(fat32.RDET_data_raw)
fat32.tree.show()
fat32.find_file("E.TXT")
#fat32.print_tree()