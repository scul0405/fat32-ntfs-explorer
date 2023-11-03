import argparse
import os

from core.NTFS import NTFS
from core.FAT32 import FAT32
from utils import print_vailable_volume

parser = argparse.ArgumentParser(description='Process volume information.')
parser.add_argument('-v', '--volume', type=str, required=False, help='volume to process')
parser.add_argument('-t', '--tree', action="store_true", help='print directory tree')
parser.add_argument('-d', '--detail', action="store_true", help='detail of volume')
parser.add_argument("-l", "--list", action="store_true", help="list available volumes")
parser.add_argument("-f", "--filename", type=str, help="file to process")
args = parser.parse_args()

manager = vars(args)

if (manager["list"] == True):
    print_vailable_volume()
    
if (manager["volume"] != None):
    ntfs = NTFS(manager["volume"])
    # Trường hợp phân vùng là NTFS
    if ntfs.boot_sector["System ID"] == "NTFS":
        if (manager["detail"] == True): 
            ntfs.print_partrition_data()

        if (manager["tree"] == True):
            ntfs.__build_dir_tree__()
        
        if (manager["filename"] != None):
            file = ntfs.read_content_of_file(manager["filename"])

            if (file == None):
                print("File không tồn tại")
            
            elif (file["TYPE"] != "FILE"):
                print(file["NAME"], "Không phải là file")

            elif (file["FILE_EXT"] != "txt"):
                print("Chương trình không hỗ trợ đọc file có định dạng khác txt")
            
            else:
                print("----[", file["NAME"] ,"]----")
                print("+ Kích thước:", file["CONTENT_SIZE"], "bytes")
                print("+ Ngày tạo:", file["CREATED TIME"])
                print("+ Chỉ số sector lưu trên ổ cứng:", file["SECTOR OFFSET"])
                print("---- Nội dung ----")
                print(file["CONTENT"].decode("utf-8"))
    # Trường hợp phân vùng là FAT32
    else:
        fat32 = FAT32(manager["volume"])

        if (manager["detail"] == True):
            fat32.print_bst_info()

        if (manager["tree"] == True):
            # gọi hàm in ra cây thư mục
            pass
            
        if (manager["filename"] != None):
            # xử lý đọc content file và in ra màn hình
            # input là manager["filename"] (tên file cần đọc)
            pass
else:
    print("No volume selected")

