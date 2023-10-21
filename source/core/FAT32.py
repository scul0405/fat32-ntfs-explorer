import os
from base64 import decode
import binascii
from utils import open_windows_partition

# disk = input("Choose a disk: ")

# path = "\\\\.\\" + disk + ":"

# if (os.path.exists(path)):
#     print("Chosen Disk: " + disk)
#     file = open(path , "rb")
#     info = file.read(200)
#     getInfo(info)
# else:
#     raise Exception()

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

class FAT32:
    def __init__(self, drive_name: str) -> None:
        self.bootsector_data = None
        try:
            with open_windows_partition(drive_name) as drive:
                self.bootsector_data = drive.read(0x200)
            print('read success')    
        except FileNotFoundError:
            print("Drive not found")
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
        # File System type  offset: 52h size: 8 bytes
        self.file_type = self.bootsector_data[0x52:0x5A].decode('utf-8')
        print("FAT type: " + self.file_type)

        # Bytes per Sector  offset: Bh  size: 2 bytes
        self.BPS = int.from_bytes(self.bootsector_data[0xB:0xD],'little')
        print("Bytes per Sector: " + str(self.BPS))

        # Sectors per Cluster   offset: Dh  size: 1 byte
        self.SC = int.from_bytes(self.bootsector_data[0xD:0xE],'little')
        print("Sectors per Cluster: " + str(self.SC))

        # Reserved Sectors offset: Eh  size: 2 bytes
        self.SB = int.from_bytes(self.bootsector_data[0xE:0x10],'little')
        print("Reserved Sectors: " + str(self.SB))

        # Copies of FAT  offset: 10h size: 1 byte
        self.NF = int.from_bytes(self.bootsector_data[0x10:0x11],'little')
        print("Copies of FAT: " + str(self.NF))

        # Total Sectors  offset: 20h size: 4 bytes
        self.SV = int.from_bytes(self.bootsector_data[0x20:0x24],'little')
        print("Total Sectors: " + str(self.SV))

        # FAT Size  offset: 24h size: 4 bytes
        self.SF = int.from_bytes(self.bootsector_data[0x24:0x28],'little')
        print("FAT Size: " + str(self.SF))

        # First Cluster of RDET offset: 2C  size: 4 bytes
        self.FC = int.from_bytes(self.bootsector_data[0x2C:0x30],'little')
        print("First Cluster of RDET: " + str(self.FC))

        # First Sector of FAT   = SB
        print("First Sector of FAT: " + str(self.SB))

        # First Data Sector = SB + NF * SF
        self.SDATA = self.SB + self.NF * self.SF
        print("First Sector of Data: " + str(self.SDATA))
    
    # From cluster index to sector index
    def __cluster_to_sector(self, index):
        return self.SB + self.SF * self.NF + (index - 2) * self.SC