from utils import open_windows_partition

import sys
import datetime
import math
import binascii

# Constants
BPS_SIZE = 512
MFT_END = int.from_bytes(b'\xff\xff\xff\xff', byteorder=sys.byteorder)
VOLUME_HEADER_OFFSET = 512

MFT_ENTRY_FLAGS = { 
    "MFT_RECORD_IN_USE": 1,
    "MFT_RECORD_IS_DIRECTORY": 2,
    "MFT_RECORD_IN_EXTENDED": 4,
    "MFT_RECORD_IS_VIEW_INDEX": 8
}

MFT_ATTRIBUTE_TYPE = {
    "$STANDARD_INFORMATION": 0x10,
    "$ATTRIBUTE_LIST": 0x20,
    "$FILE_NAME": 0x30,
    "$OBJECT_ID": 0x40,
    "$SECURITY_DESCRIPTOR": 0x50,
    "$VOLUME_NAME": 0x60,
    "$VOLUME_INFORMATION": 0x70,
    "$DATA": 0x80,
    "$INDEX_ROOT": 0x90,
    "$INDEX_ALLOCATION": 0xA0,
    "$BITMAP": 0xB0,
    "$REPARSE_POINT": 0xC0,
    "$EA_INFORMATION": 0xD0,
    "$EA": 0xE0,
    "$PROPERTY_SET": 0xF0,
    "$LOGGED_UTILITY_STREAM": 0x100
}

ACCEPT_ATTRIBUTE_FLAG = [
    0, # Folder
    32, # File
]

# Constants
BPS_SIZE = 512
MFT_END = 0
ATTR_FILE_NAME = 48

class NTFS:
    def __init__(self, drive_name: str) -> None:
        self.raw_data = None
        self.drive_name = drive_name
        self.drive = None
        self.boot_sector = None
        self.current_offset = 0
        self.current_mft_index_entry = 0
        self.mft_attribute_header = None
        self.mft_entry_raw_data = None
        self.mft_entry_data = None
        self.mft_entry_size = None
        self.mft_standard_flag = 0
        self.file_created_time = None
        self.valid_parent_id = [5] # 5 là root
        self.dir_tree_data = []
        try:
            self.drive = open_windows_partition(drive_name)
            self.raw_data = self.drive.read(BPS_SIZE)
            self.__extract_bpb__()

            if self.boot_sector["System ID"] != "NTFS":
                return

        except FileNotFoundError:
            print("Drive not found, please try another drive or use -l to list available volumes")
            exit(1)

    def __extract_bpb__(self) -> dict:
        self.boot_sector = {
            "System ID": self.raw_data[0x03:0x0B].decode("utf-8").strip(),
            "Bytes Per Sector": int.from_bytes(self.raw_data[0x0B:0x0D], byteorder=sys.byteorder),
            "Sectors Per Cluster": int.from_bytes(self.raw_data[0x0D:0x0E], byteorder=sys.byteorder),
            "Sectors Per track": int.from_bytes(self.raw_data[0x18:0x1A], byteorder=sys.byteorder),
            "Number Of Heads": int.from_bytes(self.raw_data[0x1A:0x1C], byteorder=sys.byteorder),
            "Total Sector": int.from_bytes(self.raw_data[0x28:0x30], byteorder=sys.byteorder),
            "MFT Cluster": int.from_bytes(self.raw_data[0x30:0x38], byteorder=sys.byteorder),
            "MFT Mirror Cluster": int.from_bytes(self.raw_data[0x38:0x40], byteorder=sys.byteorder),
            "Size of MTF Entry": int(math.pow(2, math.fabs(int.from_bytes(self.raw_data[0x40:0x41], byteorder=sys.byteorder, signed=True)))),
            "Cluster no Index Buffer": int.from_bytes(self.raw_data[0x44:0x45], byteorder=sys.byteorder),
            "Volume Serial Number": int.from_bytes(self.raw_data[0x48:0x50], byteorder=sys.byteorder),
        }
        self.mft_entry_size = self.boot_sector["Size of MTF Entry"]
        return self.boot_sector

    def __extract_mft__(self) -> dict:
        # Tính offset của MFT entry hiện tại
        self.current_offset = self.boot_sector["MFT Cluster"] * self.boot_sector["Sectors Per Cluster"] * \
            self.boot_sector["Bytes Per Sector"] + \
            self.current_mft_index_entry * self.mft_entry_size
        self.drive.seek(self.current_offset)

        # lưu lại sector bắt đầu của MFT entry hiện tại
        begin_sector = int(self.current_offset / self.boot_sector["Bytes Per Sector"])

        # Đọc MFT entry đầu tiên
        self.mft_entry_raw_data = self.drive.read(self.mft_entry_size)

        # Kiểm tra xem đã là MFT end chưa, nếu rồi thì throw exception
        # Dunno why mft entry index must greater than 37 but it works lmfao help
        if  int.from_bytes(self.mft_entry_raw_data[0x0:0x4], byteorder=sys.byteorder) == MFT_END and self.current_mft_index_entry > 37:
            raise Exception("Reach MFT end")

        try:
            self.mft_entry_header = {
                "Signature": self.mft_entry_raw_data[0x0:0x4].decode("utf-8"),
                "Sequence Number": int.from_bytes(self.mft_entry_raw_data[0x4:0x6], byteorder=sys.byteorder),
                "Reference Count": int.from_bytes(self.mft_entry_raw_data[0x6:0x8], byteorder=sys.byteorder),
                "Offset to the first attribute": int.from_bytes(self.mft_entry_raw_data[0x14:0x16], byteorder=sys.byteorder),
                "Entry Flags": self.__get_entry_flags__(int.from_bytes(self.mft_entry_raw_data[0x16:0x18], byteorder=sys.byteorder)),
                "Real size of the file": int.from_bytes(self.mft_entry_raw_data[0x18:0x1C], byteorder=sys.byteorder),
                "Total entry size": int.from_bytes(self.mft_entry_raw_data[0x1C:0x20], byteorder=sys.byteorder),
                "Base reference": int.from_bytes(self.mft_entry_raw_data[0x20:0x28], byteorder=sys.byteorder),
            }  
        except Exception as e:
            self.current_mft_index_entry += 1
            return 
        
        # Nếu không phải là file thì skip
        if self.mft_entry_header["Signature"] != "FILE":
            self.current_mft_index_entry += 1
            return
        
        # Đọc header của attribute $STANDARD INFORMATION
        self.current_offset += self.mft_entry_header["Offset to the first attribute"]
        self.drive.seek(self.current_offset)
        self.mft_entry_raw_data = self.drive.read(16)
        self.mft_attribute_header = self.__extract_mft_header__()

        # Đọc flag
        # Giữ lại current_offset làm offset bắt đầu từ header cho dễ tính toán
        current_standard_offset = self.current_offset + 16 + 4 # skip header và 4 byte kích thước nội dung
        
        if self.mft_attribute_header["Flag"] == "Resident":
            # Lấy thông tin byte 20-21 để biết vị trí offset của data
            self.drive.seek(current_standard_offset)
            self.mft_entry_raw_data = self.drive.read(2)

            # Tính offset để nhảy để data của standard info attribute
            current_standard_offset = self.current_offset + int.from_bytes(self.mft_entry_raw_data, byteorder=sys.byteorder)

            # Bắt đầu đọc data
            # Lấy byte thứ 0 - 7 để biết thời gian tạo file
            self.drive.seek(current_standard_offset)
            self.mft_entry_raw_data = self.drive.read(8)
            timestamp = int.from_bytes(self.mft_entry_raw_data, byteorder=sys.byteorder)
            self.file_created_time = datetime.datetime(1601, 1, 1) + datetime.timedelta(microseconds=timestamp / 10)

            # Lấy byte thứ 32 - 35 để biết giá trị cờ báo
            self.drive.seek(current_standard_offset + 32) # Seek 32 byte đầu
            self.mft_standard_flag = int.from_bytes(self.drive.read(4), byteorder=sys.byteorder)
            # 0 - FOLDER
            # 32 - các file hợp lệ
            # Skip nếu như đó là file ẩn hoặc hệ thống
            if self.mft_standard_flag not in ACCEPT_ATTRIBUTE_FLAG:
                self.current_mft_index_entry += 1
                return
        else:
            print("Non-resident")
            self.current_mft_index_entry += 1
            return 

        # ATTRIBUTE $FILE_NAME
        self.current_offset += self.mft_attribute_header["Attribute length"]
        self.drive.seek(self.current_offset)
        self.mft_entry_raw_data = self.drive.read(16)
        self.mft_attribute_header = self.__extract_mft_header__()
        # Seek tới info attribute của $FILE_NAME
        if self.mft_attribute_header["Flag"] == "Resident":
            self.current_offset += 16
            self.drive.seek(self.current_offset)

            self.mft_entry_raw_data = self.drive.read(6)
            self.mft_entry_data = {
                "SIZE OF CONTENT": int.from_bytes(self.mft_entry_raw_data[0:4], byteorder=sys.byteorder),
                "OFFSET TO CONTENT": int.from_bytes(self.mft_entry_raw_data[4:6], byteorder=sys.byteorder),
            }

            self.current_offset += self.mft_entry_data["OFFSET TO CONTENT"] - 16
            self.drive.seek(self.current_offset)
            body = self.drive.read(self.mft_entry_data["SIZE OF CONTENT"])

            # seek ngay tới offset phía sau của $FILE_NAME
            self.current_offset += self.mft_entry_data["SIZE OF CONTENT"] + 2

            self.mft_entry_data = {
                # id này là mft_index của id cha, nếu là 5 thì nó là id thư mục gốc
                "PARENT ID": int.from_bytes(body[0:6], byteorder=sys.byteorder),
                "NAME LENGTH": body[64],
                # byte thứ 66 bắt đầu là tên file (docs có ghi)
                "FILE NAME": body[66:66 + body[64] * 2].decode("utf-16"),
            }   

            # Save to directory tree data
            # Ý tưởng ở đây là nếu các file không phải của hệ thống thì nó luôn có 1 parent folder,
            # và ta lưu các folder index vào valid_parent_id nếu nó là folder
            if self.mft_entry_data["PARENT ID"] in self.valid_parent_id:
                node = {
                    "PARENT ID": self.mft_entry_data["PARENT ID"],
                    "NAME": self.mft_entry_data["FILE NAME"],
                    "INDEX": self.current_mft_index_entry,
                    "TYPE": self.mft_standard_flag == 32 and "FILE" or "FOLDER",
                    "SECTOR OFFSET": begin_sector,
                    "CREATED TIME": self.file_created_time.strftime("%d/%m/%Y %H:%M:%S"),
                }
                self.dir_tree_data.append(node)

                if self.mft_standard_flag == 0:
                    self.valid_parent_id.append(self.current_mft_index_entry)
                
                if "FILE" == (self.mft_standard_flag == 32 and "FILE" or "FOLDER"):
                    # Giữ lại file name để cuối hàm in ra màn hình
                    current_file_name = self.mft_entry_data["FILE NAME"]

                    # Seek tới attribute $DATA, bỏ qua các attribute khác
                    self.drive.seek(self.current_offset)
                    while self.drive.read(2)[0] != 0x80:
                        self.current_offset += 2

                    self.drive.seek(self.current_offset)

                    # Attribute $DATA
                    # $DATA HEADER
                    self.current_offset += self.mft_attribute_header["Attribute length"]
                    self.drive.seek(self.current_offset)
                    self.mft_entry_raw_data = self.drive.read(16)
                    self.mft_attribute_header = self.__extract_mft_header__()

                    # Giữ lại offset bắt đầu phần DATA của attribute $DATA                    
                    current_data_offset = self.current_offset
                    self.current_offset += 16
                    self.drive.seek(self.current_offset)
                    self.mft_entry_raw_data = self.drive.read(6)

                    # Đọc offset và size của content
                    self.mft_entry_data = {
                        "SIZE OF CONTENT": int.from_bytes(self.mft_entry_raw_data[0:4], byteorder=sys.byteorder),
                        "OFFSET TO CONTENT": int.from_bytes(self.mft_entry_raw_data[4:6], byteorder=sys.byteorder),
                    }

                    # Trở ngược về đầu phần DATA và đọc content
                    self.current_offset = current_data_offset + self.mft_entry_data["OFFSET TO CONTENT"]
                    self.dir_tree_data[-1]["FILE_EXT"] = current_file_name.split(".")[-1]
                    self.drive.seek(self.current_offset)

                    if current_file_name.split(".")[-1] == "txt":
                        content = self.drive.read(self.mft_entry_data["SIZE OF CONTENT"])
        
                        self.dir_tree_data[-1]["CONTENT"] = content
                        self.dir_tree_data[-1]["CONTENT_SIZE"] = len(content)
                    else:
                        self.dir_tree_data[-1]["CONTENT"] = ""
                    # Lưu content và extension file
        else:
            print("Non-resident")
        self.current_mft_index_entry += 1
    
    def __extract_mft_header__(self) -> dict:
        header = {
            "Attribute type": int.from_bytes(self.mft_entry_raw_data[0:4], byteorder=sys.byteorder),
            "Attribute length": int.from_bytes(self.mft_entry_raw_data[4:8], byteorder=sys.byteorder),
            "Flag": "Resident" if int.from_bytes(self.mft_entry_raw_data[8:9], byteorder=sys.byteorder) == 0 else "Non-resident",
            "Name size": int.from_bytes(self.mft_entry_raw_data[9:10], byteorder=sys.byteorder),
            "Offset to name": int.from_bytes(self.mft_entry_raw_data[10:12], byteorder=sys.byteorder),
            "Attribute name": self.__get_attribute_type__(int.from_bytes(self.mft_entry_raw_data[0:4], byteorder=sys.byteorder)),
        }
        return header

    def __get_attribute_type__(self, attribute_type: int) -> str:
        for key, value in MFT_ATTRIBUTE_TYPE.items():
            if attribute_type == value:
                return key
        return "Unknown"

    def __get_entry_flags__(self, entry_flags: int) -> str:
        for key, value in MFT_ENTRY_FLAGS.items():
            if entry_flags == value:
                return key
        return "Unknown flags"

    def __build_dir_tree__(self, inp_dir: dict = None) -> None:
        for _ in range(self.boot_sector["Total Sector"]):
            try:
                self.__extract_mft__()
            except Exception as e:
                if str(e) == "Reach MFT end":
                    break
                else:
                    pass
        # Xuất thông tin ổ đĩa
        if inp_dir == None:
            print("Directory tree:")
            print(self.drive_name + ":")
            self.print_folder_tree(self.dir_tree_data, 5)
        else: 
            print(inp_dir["NAME"] + ":")
            self.print_folder_tree(self.dir_tree_data, inp_dir["INDEX"])
        # Xuất thông tin thư mục

    def read_content_of_file(self, file_name: str):
        for item in self.dir_tree_data:
            if item["NAME"] == file_name:
                # return item["CONTENT"]
                return item
        return None

    def print_folder_tree(self, data, parent_id, indent='', elbow='└──', pipe='│  ', tee='├──', blank='   '):
        children = [item for item in data if item['PARENT ID'] == parent_id]
        for i, child in enumerate(children):
            name = child['NAME']
            is_last_child = (i == len(children) - 1)
            if child['TYPE'] == 'FOLDER':
                print(indent + (elbow if is_last_child else tee) + name)
                next_indent = indent + (blank if is_last_child else pipe)
                self.print_folder_tree(data, child['INDEX'], next_indent, elbow, pipe, tee, blank)
            else:
                print(indent + (elbow if is_last_child else tee) + name)

    def print_raw_mft(self, data = None) -> None:
        str_data = binascii.hexlify(data if data != None else self.raw_data).decode("utf-8")
        
        # Print header
        print("offset ", end=" ")
        for i in range(0, 16):
            print("{:2x}".format(i), end=' ')
        print()
        # print 16 byte each line
        for i in range(0, len(str_data), 32):
            line = str_data[i:i+32]
            # print offset
            offset = int(i / 32)
            print("{:07x}0".format(offset), end=" ")
            # print hex
            for j in range(0, len(line), 2):
                print(line[j:j+2], end=' ')
            # print ascii
            for j in range(0, len(line), 2):
                char = line[j:j+2]
                # ignore \r \n
                if int(char, 16) >= 32 and int(char, 16) <= 126:
                    print(chr(int(char, 16)), end='')
                else:
                    print(".", end='')
            print()
    
    def print_partrition_data(self):
        print("Thông tin chi tiết ổ đĩa", self.drive_name, ":")
        print("System ID:", self.boot_sector["System ID"])
        print("Bytes mỗi Sector:", self.boot_sector["Bytes Per Sector"])
        print("Sectors mỗi Cluster:", self.boot_sector["Sectors Per Cluster"])
        print("Sectors mỗi track:", self.boot_sector["Sectors Per track"])
        print("Số lượng Heads:", self.boot_sector["Number Of Heads"])
        print("Tổng số Sector:", self.boot_sector["Total Sector"])
        print("Địa chỉ MFT Cluster:", self.boot_sector["MFT Cluster"])
        print("Địa chỉ MFT Mirror Cluster:", self.boot_sector["MFT Mirror Cluster"])
        print("Kích thước MTF Entry:", self.boot_sector["Size of MTF Entry"])
        print("Số cluster Index Buffer:", self.boot_sector["Cluster no Index Buffer"])
        print("Volume Serial:", self.boot_sector["Volume Serial Number"])
