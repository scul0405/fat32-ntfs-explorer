from enum import Flag, auto
from base64 import decode
from itertools import chain
import binascii
from utils import open_windows_partition

class FAT:
  def __init__(self, data) -> None:
    self.FAT_TABLE = []
    for i in range(0, len(data), 4):
      self.FAT_TABLE.append(int.from_bytes(data[i:i + 4], byteorder='little'))
  
  def get_cluster_chain(self, index: int) -> 'list[int]':
    cluster_chain = []
    while True:
      cluster_chain.append(index)
      index = self.FAT_TABLE[index]
      if index == 0x0FFFFFFF or index == 0x0FFFFFF7:
        break
    return cluster_chain
    
class File:
    def __init__(self, data) -> None:
        mainEntry = len(data) - 1
        self.is_folder = (int.from_bytes(data[mainEntry][0xB:0xC]) == 0x10)
        self.storage = []
        self.file_content = ""
        self.get_file_info(data)

    def get_file_info(self, data):
        self.filename = ""
        for i in range(len(data)):
           # is main entry (last loop)
           if(i == len(data) - 1):
               
                if(len(data) == 1):
                    self.main_filename = data[i][0x0:0x8].decode('utf-8')

                self.extension =data[i][0x8:0xB].decode('utf-8')
                self.start_cluster = int.from_bytes(data[i][0x1A:0x1C], 'little')
           # is sub entry
           else:
                temp = data[i][0x1:0xB].decode('utf-16') + data[i][0xE:0x1A].decode('utf-16') + data[i][0x1C:0x20].decode('utf-16')
                self.filename = self.filename + temp

        end_filename = self.filename.find('\x00')
        self.filename = self.filename[:end_filename]
        print(self.filename + "." + self.extension + "\t" + str(self.start_cluster))
    



class FAT32:
    def __init__(self, drive_name: str) -> None:
        self.bootsector_data_raw = None
        
        try:
            self.drive = open(r'\\.\%s:' % drive_name, 'rb')
            print(f"Reading {drive_name}...")
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
            
            # Reserved data
            reserved_data_size = self.SB * self.BPS
            self.reserved_data = self.drive.read(reserved_data_size)

            # FAT data
            FAT_data_size = self.SF * self.NF * self.BPS
            self.FAT_data_raw = self.drive.read(FAT_data_size)
            self.FAT_data = FAT(self.FAT_data_raw)

            # RDET data
            self.RDET_data_raw = self.drive.read(self.SC * self.BPS)

            # get list file
            self.get_all_files_in_RDET()


            print('Read Success')    
        except FileNotFoundError:
            print("Drive Not Found")
            exit(1)

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

    def print_bst_info(self):
        print("FAT type: " + self.file_type)

        print("Bytes per Sector: " + str(self.BPS))

        print("Sectors per Cluster: " + str(self.SC))

        print("Reserved Sectors: " + str(self.SB))

        print("Copies of FAT: " + str(self.NF))

        print("Total Sectors: " + str(self.SV))

        print("FAT Size: " + str(self.SF))

        print("First Cluster of RDET: " + str(self.FC))

        # First Sector of FAT   = SB
        print("First Sector of FAT: " + str(self.SB))

        print("First Sector of Data: " + str(self.SDATA))
    
    def get_all_files_in_RDET(self):
        list_Entry = []
        self.list_File = []
        for i in range(0, len(self.RDET_data_raw), 32):
            new_entry = self.RDET_data_raw[i : i + 32]

            if(int.from_bytes(new_entry[0xB:0xC]) == 0x0):
                break

            list_Entry.append(new_entry)

            if(int.from_bytes(new_entry[0xB:0xC]) != 0x0f):
                self.list_File.append(File(list_Entry))
                list_Entry = []

    # def get_file_content(self, file: File):
    #     chain = self.FAT_data.get_cluster_chain(file.start_cluster)
    #     for i in chain:

    
    # From cluster index to sector index
    def cluster_to_sector(self, index):
        return self.SB + self.SF * self.NF + (index - 2) * self.SC