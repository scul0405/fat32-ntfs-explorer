# from [folder].[file.py] import [class]


from core.NTFS import NTFS
from core.FAT32 import FAT32

# ntfs = NTFS("F")
# ntfs.print_raw_bpb()
# ntfs.print_bst_info()
# # get standard NTFS file system metadata files (Doc: page 268-269)
# for i in range(0, 12):
#     ntfs.extract_mft()

fat32 = FAT32("F")
# print('RDET')
# fat32.print_table_offset(fat32.RDET_data_raw)
fat32.print_bst_info()
for file in fat32.list_File:
    print(file.filename + '.' + file.extension)
    fat32.get_file_content(file)