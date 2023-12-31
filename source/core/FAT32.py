from enum import Flag, auto
from base64 import decode
from itertools import chain
import binascii
import os
from utils import open_windows_partition

# file attribute got from offset 0B
class Attribute(Flag):
    Read_Only = auto()
    Hidden = auto()
    System = auto()
    Volume_Lable = auto()
    Directory = auto()
    Archive = auto()

# Store FATs to get cluster chain from given first cluster of file
class FAT:
  # Store FATs
  def __init__(self, data) -> None:
    self.FAT_TABLE = []

    for i in range(0, len(data), 4):

      # Lấy 4 bytes tiếp theo từ data chuyển thành int đưa vào FAT_TABLE
      self.FAT_TABLE.append(int.from_bytes(data[i:i + 4], 'little'))

  # Get cluster chain from given first cluster of file
  def get_cluster_chain(self, index: int) -> 'list[int]':
    cluster_chain = []
    # print('///')
    while True:
      cluster_chain.append(index)
      index = self.FAT_TABLE[index]

      if index == 0x0FFFFFFF or index == 0x0FFFFFF7:
        break
      
    return cluster_chain

# Entry aka File information
class Entry:
    # Store File information
    def __init__(self, data) -> None:
        self.raw_data = data
        self.flag = data[0xB:0xC]
        self.is_subentry = False
        self.is_deleted = False
        self.is_empty = False
        self.is_label = False
        self.attr = Attribute(0)
        self.size = 0
        self.total_name = ""
        self.file_content = ""
        self.display = ""
        self.storage = []
        self.parse_entry(data)

    # Parse the entry data
    def parse_entry(self, data):
        if self.flag == b'\x0f':
            self.is_subentry = True
        if not self.is_subentry:
            self.parse_main_entry(data)
        else:
            self.parse_subentry(data)

    # Parse main entry
    def parse_main_entry(self, data):
        self.name = data[:0x8]
        self.ext = data[0x8:0xB]
        if self.name[:1] == b'\xe5':
            self.is_deleted = True
        if self.name[:1] == b'\x00':
            self.is_empty = True
            self.name = ""
            return

        self.attr = Attribute(int.from_bytes(self.flag, 'little'))
        if Attribute.Volume_Lable in self.attr:
            self.is_label = True
            return

        self.start_cluster = int.from_bytes(data[0x1A:0x1C], 'little')
        self.size = int.from_bytes(data[0x1C:0x20], 'little')

    # Parse sub entry
    def parse_subentry(self, data):
        self.name = b""
        for i in chain(range(0x1, 0xB), range(0xE, 0x1A), range(0x1C, 0x20)):
            self.name += int.to_bytes(data[i], 1, 'little')
            if self.name.endswith(b"\xff\xff"):
                self.name = self.name[:-2]
                break
        self.name = self.name.decode('utf-16le').strip('\x00')

    # Check if it is main entry
    def is_main_entry(self) -> bool:
        return not (self.is_empty or self.is_subentry or self.is_deleted or self.is_label or Attribute.System in self.attr)

    # Check if it is directory
    def is_directory(self) -> bool:
        return Attribute.Directory in self.attr

    # The second line of file when display, show attribute and sectors
    def set_display_in_tree(self, chain, SC):
        self.display = self.display + self.display_attr()

        if (chain):
            self.display = self.display + "\t Sectors: " + str(chain[0] * SC) + " -> " + str((chain[0] + len(chain)) * SC - 1)

    # Convert attribute of the entry to string
    def display_attr(self) -> str:
        attr = []

        if self.attr.value & 0b1:
            attr.append('Read-Only')

        if self.attr.value & 0b10:
            attr.append('Hidden')

        if self.attr.value & 0b100:
            attr.append('System')

        if self.attr.value & 0b1000:
            attr.append('VolLable')

        if self.attr.value & 0b10000:
            attr.append('Directory')
            
        if self.attr.value & 0b100000:
            attr.append('Archive')

        display = "Thuộc tính: "

        for i in attr:
            display = display + i

            if(i != attr[len(attr) - 1]):
                display = display + " - "

        return display

# Store list of Entries, including main and sub entries
class DET:
  # Get all raw data and convert it into list Entries
  def __init__(self, data: bytes) -> None:
    self.entries: list[Entry] = []
    total_name = ""

    for i in range(0, len(data), 32):
        entry = Entry(data[i: i + 32])
        self.entries.append(entry)

        # Check if the current entry is empty or deleted
        if entry.is_empty or entry.is_deleted:
            total_name = ""
            continue

        # If the current entry is a sub entry, add its name to the total name
        if entry.is_subentry:
            total_name = entry.name + total_name
            continue

        # This stage is the main entry
        if total_name != "":
            # Sum up all sub entry names to the main entry
            entry.total_name = total_name
        else:
            extend = entry.ext.strip().decode()
            if extend == "":
                # It's a folder
                entry.total_name = entry.name.strip().decode()
            else:
                # It's a file
                entry.total_name = entry.name.strip().decode() + "." + extend

        # Reset the total name
        total_name = ""

    # Save all main entries of a det
    self.list_main_entries: 'list[Entry]' = [entry for entry in self.entries if entry.is_main_entry()]

class FAT32:
    # Read and store reserved data (including bootsector), FATs, RDET
    def __init__(self, drive_name: str) -> None:
        self.bootsector_data_raw = None
        # Open disk
        try:
            self.drive = open(r'\\.\%s:' % drive_name, 'rb')
            print(f"Đọc ổ {drive_name}...")
        except FileNotFoundError:
            print(f"[ERROR] No volume named {drive_name}")
            exit()
        except PermissionError:
            print("[ERROR] Permission denied, try again as admin/root")
            exit()
        except Exception as e:
            print(e)
            print("[ERROR] Unknown error occurred")
            exit()

        try:
            with open_windows_partition(drive_name) as drive:
                self.bootsector_data_raw = drive.read(0x200)
                self.get_bootsector_discription()
  
        except Exception as e:
            print(e)
            print("[ERROR] Unknown error occurred")
            exit(1)

        # Reserved data
        reserved_data_size = self.SB * self.BPS
        self.reserved_data = self.drive.read(reserved_data_size)

        # FAT data
        FAT_data_size = self.SF * self.NF * self.BPS
        self.FAT_data_raw = self.drive.read(FAT_data_size)
        self.FAT_data = FAT(self.FAT_data_raw)

        # RDET data
        self.RDET_data_raw = self.drive.read(self.SC * self.BPS)

        # Create root
        self.disk = Entry(b'')
        self.disk.total_name = drive_name + ":"
        self.disk.storage = self.get_all_files(self.RDET_data_raw)

        # found file/folder flag
        self.found_file = False

        print('Đọc thành công')  
    
    # Read all disk information in bootsector
    def get_bootsector_discription(self):
        # File System type  offset: 52h size: 8 bytes
        self.file_type = self.bootsector_data_raw[0x52:0x5A].decode('utf-8')

        # Bytes per Sector  offset: Bh  size: 2 bytes
        self.BPS = int.from_bytes(self.bootsector_data_raw[0xB:0xD],'little')

        # Sectors per Cluster   offset: Dh  size: 1 byte
        self.SC = int.from_bytes(self.bootsector_data_raw[0xD:0xE],'little')

        # Reserved Sectors offset: Eh  size: 2 bytes
        self.SB = int.from_bytes(self.bootsector_data_raw[0xE:0x10],'little')

        # Copies of FAT  offset: 10h size: 1 byte
        self.NF = int.from_bytes(self.bootsector_data_raw[0x10:0x11],'little')

        # Total Sectors  offset: 20h size: 4 bytes
        self.SV = int.from_bytes(self.bootsector_data_raw[0x20:0x24],'little')

        # FAT Size  offset: 24h size: 4 bytes
        self.SF = int.from_bytes(self.bootsector_data_raw[0x24:0x28],'little')

        # First Cluster of RDET offset: 2C  size: 4 bytes
        self.FC = int.from_bytes(self.bootsector_data_raw[0x2C:0x30],'little')

        # First Data Sector = SB + NF * SF
        self.SDATA = self.SB + self.NF * self.SF
    
    # Print offset of given raw data (Ex: bootsector, FATs, RDET, ...)
    def print_table_offset(self, data) -> None:
        str_data = binascii.hexlify(data).decode("utf-8")

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

    # Print all disk information got from bootsector
    def print_bst_info(self):
        print("Thông tin chi tiết ổ đĩa " + self.disk.total_name)

        print("Loại FAT: " + self.file_type)

        print("Bytes mỗi Sector: " + str(self.BPS))

        print("Sectors mỗi Cluster: " + str(self.SC))

        print("Reserved Sectors: " + str(self.SB))

        print("Số bảng FAT: " + str(self.NF))

        print("Tổng số: " + str(self.SV))

        print("Kích thước của FAT: " + str(self.SF))

        print("Cluster đầu tiên của RDET: " + str(self.FC))

        # First Sector of FAT = SB
        print("Sector đầu tiên của FAT: " + str(self.SB))

        print("Sector đầu tiên của Data: " + str(self.SDATA))

    # Get all files/folders from data (RDET, SDET) given (Mutually recursive with get_folder_content)
    def get_all_files(self, data):
        list_File = []

        for i in DET(data).list_main_entries:
            list_File.append(i)

            if(i.is_directory()):
                self.get_folder_content(i)
            else:
                self.get_file_content(i)

        return list_File
    
    # Get content of file from given list entries
    def get_file_content(self, file: Entry):
        if(file.size == 0):
            file.set_display_in_tree([], self.SC)
            return

        chain = self.FAT_data.get_cluster_chain(file.start_cluster)
        file.set_display_in_tree(chain , self.SC)
        size_remaining = file.size

        if(file.ext.decode('utf-8') == 'TXT'):
            for i in chain:

                if(size_remaining <= 0):
                    break

                pos = self.cluster_to_sector(i) * self.BPS
                self.drive.seek(pos)
                byte_per_cluster = self.SC * self.BPS
                read_data = self.drive.read(min(size_remaining , byte_per_cluster))
                file.file_content = file.file_content + read_data.decode('utf-8')
                size_remaining = size_remaining - byte_per_cluster
        else:
            file.file_content = "Chương trình không hỗ trợ đọc file có định dạng khác txt"
    
    # Get content of folder from given list entries (all files/folders contain in it) (Mutually recursive with get_all_files)
    def get_folder_content(self, folder: Entry):
        # print(folder.total_name)
        chain = self.FAT_data.get_cluster_chain(folder.start_cluster)
        raw_data = b''
        folder.set_display_in_tree(chain, self.SC)

        for i in chain:

            pos = self.cluster_to_sector(i) * self.BPS
            self.drive.seek(pos)
            byte_per_cluster = self.SC * self.BPS
            read_data = self.drive.read(byte_per_cluster)
            raw_data = raw_data + read_data
        
        folder.storage = self.get_all_files(raw_data[64:])

    # From cluster index to sector index
    def cluster_to_sector(self, index):
        return self.SB + self.SF * self.NF + (index - 2) * self.SC

    # Find file matches the given name
    def find_file(self, name):
        self.found_file = False
        self.find_file_in_folder(name, self.disk.storage)
        
        if self.found_file == False:
            print("Không tìm thấy file.")

    # Find file in folder matches given name (Recursion)
    def find_file_in_folder(self, name, folder):
        if self.found_file:
            return

        for i in folder:
            if i.total_name.upper() == name.upper():
                self.found_file = True
                print("----[ " + name + " ]----")
                if i.is_directory():
                    self.print_tree(i)
                else:
                    print("+ Kích thước: " + str(i.size if i.size != 0 else 0))
                    print('---- Nội dung: ----\n',i.file_content)
                    print('-------------------')
                return
            elif i.is_directory():
                self.find_file_in_folder(name, i.storage)

    # Print all children nodes in the same depth and go to the next depth(Recursion)
    def print_children_tree(self, list, indent='', elbow='└──', pipe='│  ', tee='├──', blank='   '):
        for i in list:
            is_last_child = (i == list[len(list) - 1])

            if i.is_directory():
                print(indent + (elbow if is_last_child else tee) + i.total_name)
                next_indent = indent + (blank if is_last_child else pipe)
                print(next_indent + i.display)
                self.print_children_tree(i.storage, next_indent, elbow, pipe, tee, blank)
            else:
                print(indent + (elbow if is_last_child else tee) + i.total_name + '\tKích thước: ' + str(i.size if i.size != 0 else 0))
                print(indent + (blank if is_last_child else pipe) + i.display)

    # Print tree with given root
    def print_tree(self, folder):
        print(folder.total_name)

        if folder.display:
            print(folder.display) 

        self.print_children_tree(folder.storage)