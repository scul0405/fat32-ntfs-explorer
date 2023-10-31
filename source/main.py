# from [folder].[file.py] import [class]


from core.NTFS import NTFS
from core.FAT32 import FAT32

ntfs = NTFS("F")
# ntfs.print_bst_info()
# # get standard NTFS file system metadata files (Doc: page 268-269)
# for i in range(0, 14):
#     ntfs.extract_mft()

# skip tới folder ditmemay để debug cho nhanh
ntfs.current_mft_index_entry = 37
for _ in range(ntfs.boot_sector["Total Sector"]):
    try:
        ntfs.__extract_mft__()
    except Exception as e:
        print(e)
        pass

ntfs.__build_dir_tree__()

# fat32 = FAT32("F")
# fat32.print_raw_bst()
# fat32.print_bst_info()
