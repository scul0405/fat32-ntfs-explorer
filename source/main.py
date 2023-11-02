import argparse
import os

from core.NTFS import NTFS
from core.FAT32 import FAT32
from utils import print_vailable_volume

parser = argparse.ArgumentParser(description='Process volume information.')
parser.add_argument('-v', '--volume', type=str, required=False, help='volume to process')
parser.add_argument("-l", "--list", action="store_true", help="list available volumes")
parser.add_argument("-f", "--file", type=str, required=False, help="file to process")
args = parser.parse_args()

manager = vars(args)

if (manager["list"] == True):
    print_vailable_volume()


if (manager["volume"] != None):
    ntfs = NTFS(manager["volume"])
    # Trường hợp phân vùng là NTFS
    if ntfs.boot_sector["System ID"] == "NTFS":
        ntfs.print_partrition_data()
    # Trường hợp phân vùng là FAT32
    else:
        fat32 = FAT32(manager["volume"])
        print("FAT32") 
else:
    print("No volume selected")


# ntfs.current_mft_index_entry = 37
# for _ in range(ntfs.boot_sector["Total Sector"]):
#     try:
#         ntfs.__extract_mft__()
#     except Exception as e:
#         pass

# ntfs.__build_dir_tree__()
# print(ntfs.dir_tree_data)

# fat32 = FAT32("F")
# fat32.print_raw_bst()
# fat32.print_bst_info()