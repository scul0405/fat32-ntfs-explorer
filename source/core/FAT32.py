import os
from base64 import decode
import binascii
from utils import open_windows_partition

# def getInfo(info):

#     # File System type  offset: 52h size: 8 bytes
#     file_type = info[0x52:0x5A].decode('utf-8')
#     print("FAT type: " + file_type)

#     # Bytes per Sector  offset: Bh  size: 2 bytes
#     BPS = int.from_bytes(info[0xB:0xD],'little')
#     print("Bytes per Sector: " + str(BPS))

#     # Sectors per Cluster   offset: Dh  size: 1 byte
#     SC = int.from_bytes(info[0xD:0xE],'little')
#     print("Sectors per Cluster: " + str(SC))

#     # Reserved Sectors offset: Eh  size: 2 bytes
#     SB = int.from_bytes(info[0xE:0x10],'little')
#     print("Reserved Sectors: " + str(SB))

#     # Copies of FAT  offset: 10h size: 1 byte
#     NF = int.from_bytes(info[0x10:0x11],'little')
#     print("Copies of FAT: " + str(NF))

#     # Total Sectors  offset: 20h size: 4 bytes
#     SV = int.from_bytes(info[0x20:0x24],'little')
#     print("Total Sectors: " + str(SV))

#     # FAT Size  offset: 24h size: 4 bytes
#     SF = int.from_bytes(info[0x24:0x28],'little')
#     print("FAT Size: " + str(SF))

#     # First Cluster of RDET offset: 2C  size: 4 bytes
#     FC = int.from_bytes(info[0x2C:0x30],'little')
#     print("First Cluster of RDET: " + str(FC))

#     # First Sector of FAT   = SB
#     print("First Sector of FAT: " + str(SB))

#     # First Data Sector = SB + NF * SF
#     SDATA = SB + NF * SF
#     print("First Sector of Data: " + str(SDATA))




# disk = input("Choose a disk: ")

# path = "\\\\.\\" + disk + ":"

# if (os.path.exists(path)):
#     print("Chosen Disk: " + disk)
#     file = open(path , "rb")
#     info = file.read(200)
#     getInfo(info)
# else:
#     raise Exception()

class FAT32:
    def __init__(self, drive_name: str) -> None:
        self.raw_data = None
        try:
            with open_windows_partition(drive_name) as drive:
                self.raw_data = drive.read(0x200)
            print('read success')    
        except FileNotFoundError:
            print("Drive not found")
            exit(1)
    def print_raw_bst(self) -> None:
        str_data = binascii.hexlify(self.raw_data).decode("utf-8")

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
        file_type = self.raw_data[0x52:0x5A].decode('utf-8')
        print("FAT type: " + file_type)

        # Bytes per Sector  offset: Bh  size: 2 bytes
        BPS = int.from_bytes(self.raw_data[0xB:0xD],'little')
        print("Bytes per Sector: " + str(BPS))

        # Sectors per Cluster   offset: Dh  size: 1 byte
        SC = int.from_bytes(self.raw_data[0xD:0xE],'little')
        print("Sectors per Cluster: " + str(SC))

        # Reserved Sectors offset: Eh  size: 2 bytes
        SB = int.from_bytes(self.raw_data[0xE:0x10],'little')
        print("Reserved Sectors: " + str(SB))

        # Copies of FAT  offset: 10h size: 1 byte
        NF = int.from_bytes(self.raw_data[0x10:0x11],'little')
        print("Copies of FAT: " + str(NF))

        # Total Sectors  offset: 20h size: 4 bytes
        SV = int.from_bytes(self.raw_data[0x20:0x24],'little')
        print("Total Sectors: " + str(SV))

        # FAT Size  offset: 24h size: 4 bytes
        SF = int.from_bytes(self.raw_data[0x24:0x28],'little')
        print("FAT Size: " + str(SF))

        # First Cluster of RDET offset: 2C  size: 4 bytes
        FC = int.from_bytes(self.raw_data[0x2C:0x30],'little')
        print("First Cluster of RDET: " + str(FC))

        # First Sector of FAT   = SB
        print("First Sector of FAT: " + str(SB))

        # First Data Sector = SB + NF * SF
        SDATA = SB + NF * SF
        print("First Sector of Data: " + str(SDATA))