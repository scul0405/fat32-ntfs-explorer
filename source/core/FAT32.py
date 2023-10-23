import os
from base64 import decode
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

class RDET:
    def __init__(self, data) -> None:
        self.Entries = []
    
    def append_entry(self, data):
        entry = Entry(data)
        self.Entries.append(entry)

class Entry:
   def __init__(self, data) -> None:
      self.sub_entry = True if data[0xB:0xC] == 0x0F else False
      self.data = data
    
class File:
   def _init_(self, data) -> None:
        mainEntry = data.len
        self.is_folder = True if data[mainEntry][0xB:0xC] == 0x10 else False
        self.storage = []

class FAT32:
    def __init__(self, drive_name: str) -> None:
        self.bootsector_data = None
        self.readed = 0
        try:
            with open_windows_partition(drive_name) as drive:
                self.bootsector_data = drive.read(0x200)

            # File System type  offset: 52h size: 8 bytes
            self.file_type = self.bootsector_data[0x52:0x5A].decode('utf-8')

            # Bytes per Sector  offset: Bh  size: 2 bytes
            self.BPS = int.from_bytes(self.bootsector_data[0xB:0xD],'little')

            # Sectors per Cluster   offset: Dh  size: 1 byte
            self.SC = int.from_bytes(self.bootsector_data[0xD:0xE],'little')

            # Reserved Sectors offset: Eh  size: 2 bytes
            self.SB = int.from_bytes(self.bootsector_data[0xE:0x10],'little')

            # Copies of FAT  offset: 10h size: 1 byte
            self.NF = int.from_bytes(self.bootsector_data[0x10:0x11],'little')

            # Total Sectors  offset: 20h size: 4 bytes
            self.SV = int.from_bytes(self.bootsector_data[0x20:0x24],'little')

            # FAT Size  offset: 24h size: 4 bytes
            self.SF = int.from_bytes(self.bootsector_data[0x24:0x28],'little')

            # First Cluster of RDET offset: 2C  size: 4 bytes
            self.FC = int.from_bytes(self.bootsector_data[0x2C:0x30],'little')

            # First Data Sector = SB + NF * SF
            self.SDATA = self.SB + self.NF * self.SF

            # Reserved data
            reserved_data_size = (self.SB - 1) * self.BPS
            self.reserved_data = drive.read(reserved_data_size)

            # FAT data
            FAT_data_size = self.SF * self.NF * self.BPS
            self.FAT_data_raw = drive.read(FAT_data_size)

            self.FAT_data = FAT(self.FAT_data_raw)

            self.RDET_data = drive.read(self.SC * self.BPS)

            print('Read Success')    
        except FileNotFoundError:
            print("Drive Not Found")
            exit(1)

    def print_raw_bst(self) -> None:
        str_data = binascii.hexlify(self.bootsector_data).decode("utf-8")

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
    
    # From cluster index to sector index
    def __cluster_to_sector(self, index):
        return self.SB + self.SF * self.NF + (index - 2) * self.SC