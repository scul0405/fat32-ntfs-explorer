# from [folder].[file.py] import [class]

import os
from core.NTFS import NTFS
from core.FAT32 import FAT32

volumes = [chr(x) + ":" for x in range(65, 91) if os.path.exists(chr(x) + ":")]
print("Available volumes:")
for i in range(len(volumes)):
    print(f"{i + 1}/", volumes[i])

ntfs = NTFS("F")

ntfs.current_mft_index_entry = 37
for _ in range(ntfs.boot_sector["Total Sector"]):
    try:
        ntfs.__extract_mft__()
    except Exception as e:
        pass

ntfs.__build_dir_tree__()
print(ntfs.dir_tree_data)

# fat32 = FAT32("F")
# fat32.print_raw_bst()
# fat32.print_bst_info()