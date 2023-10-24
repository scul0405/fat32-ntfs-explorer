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
#fat32.print_table_offset(fat32.RDET_data_raw)
#print(fat32.FAT_data.get_cluster_chain(6))
#fat32.print_bst_info()
