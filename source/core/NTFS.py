from utils import open_windows_partition

import sys
import binascii


class NTFS:
    def __init__(self, drive_name: str) -> None:
        self.raw_data = None
        try:
            with open_windows_partition(drive_name) as drive:
                self.raw_data = drive.read(512)
                self.__extract_bpb__()
        except FileNotFoundError:
            print("Drive not found")
            exit(1)

    def __extract_bpb__(self) -> dict:
        self.boot_sector = {
            "Bytes Per Sector": int.from_bytes(self.raw_data[0x0B:0x0D], byteorder=sys.byteorder),
            "Sectors Per Cluster": int.from_bytes(self.raw_data[0x0D:0x0E], byteorder=sys.byteorder),
            "Sectors Per track": int.from_bytes(self.raw_data[0x18:0x1A], byteorder=sys.byteorder),
            "Number Of Heads": int.from_bytes(self.raw_data[0x1A:0x1C], byteorder=sys.byteorder),
            "Total Sector": int.from_bytes(self.raw_data[0x28:0x30], byteorder=sys.byteorder),
            "MFT Cluster": int.from_bytes(self.raw_data[0x30:0x38], byteorder=sys.byteorder),
            "MFT Mirror Cluster": int.from_bytes(self.raw_data[0x38:0x40], byteorder=sys.byteorder),
        }

    def print_raw_bpb(self) -> None:
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
